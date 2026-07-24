"""LangGraph orchestration of the six-agent Gemba Walk workflow:

RAG retrieve -> PE Agent -> [Automation Agent || AI Agentic Agent || Kaizen
Agent || Process Flow Agent] (run concurrently - all four only depend on PE
Agent's diagnostics, not on each other's output) -> Postprocess (single
fan-in from all four: roadmap horizon assignment + duplicate flagging over
the merged recommendation list; Process Flow Agent's diagrams pass through
untouched) -> Reviewer Agent -> RAGAS + deep evaluation -> (loop back to
Kaizen Agent for revision if below threshold, up to ragas_max_review_rounds
- re-triggers only Kaizen, then flows back through Postprocess; Process Flow
Agent does not re-run) -> Finalize (savings roll-up + executive summary +
persistence).

IMPORTANT: Reviewer Agent must have exactly ONE incoming edge (from
Postprocess), not two. An earlier version fed Postprocess and Process Flow
Agent into Reviewer Agent as separate parallel edges; empirically (see a
standalone LangGraph script reproducing this exact topology) that caused
Reviewer Agent to fire multiple times per revision round with stale round
numbers - chaining two fan-in joins back-to-back before a loop's re-entry
point is unsafe, even though a single fan-in join handles the same loop
correctly. Route every parallel branch through ONE join before a loop-back
target.

Compiled with a LangGraph MemorySaver checkpointer, so each run's full
state is checkpointed step-by-step under a unique thread_id - this is the
"working memory" layer: state survives across the graph's supersteps and
could be resumed/inspected after a partial failure, without needing an
external Redis deployment for this single-process backend.
"""
from __future__ import annotations

import uuid
from difflib import SequenceMatcher

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.ai_agent import run_ai_agent
from app.agents.automation_agent import run_automation_agent
from app.agents.flow_agent import run_flow_agent
from app.agents.kaizen_agent import assign_roadmap_horizons, run_kaizen_agent
from app.agents.pe_agent import run_pe_agent
from app.agents.review_agent import run_review_agent
from app.agents.savings_calculator import aggregate_savings, compute_current_state_baseline
from app.config.llm_factory import get_chat_model
from app.config.settings import get_settings
from app.evaluation.deep_eval import deep_evaluate_recommendations
from app.evaluation.kpi_engine import compute_kpis
from app.evaluation.ragas import evaluate_response
from app.schemas.agent_state import GembaWalkState
from app.utils.logging import get_logger

logger = get_logger(__name__)

_checkpointer = MemorySaver()


def _flag_duplicates(recommendations: list) -> list:
    for i, r1 in enumerate(recommendations):
        if r1.is_duplicate:
            continue
        for r2 in recommendations[i + 1:]:
            if r2.is_duplicate or r1.step_number != r2.step_number:
                continue
            similarity = SequenceMatcher(None, r1.title.lower(), r2.title.lower()).ratio()
            if similarity > 0.72:
                r2.is_duplicate = True
                r2.reviewer_notes = f"Flagged as duplicate of '{r1.title}' (similarity {similarity:.2f})"
    return recommendations


def node_pe_agent(state: GembaWalkState) -> dict:
    diagnostics, raw = run_pe_agent(state["metadata"], state["raw_steps"])
    return {"diagnostics": diagnostics, "trace": [f"PE Agent: diagnosed {len(diagnostics)} steps"]}


def node_automation_agent(state: GembaWalkState) -> dict:
    """Runs concurrently with node_ai_agent (both fan out from PE Agent).
    Returns only its OWN new recommendations - the additive `recommendations`
    reducer concatenates this with whatever the AI Agentic Agent's parallel
    branch contributes in the same superstep, so neither branch clobbers
    the other's writes.
    """
    recs, raw = run_automation_agent(state["metadata"], state["diagnostics"])
    return {"recommendations": recs, "trace": [f"Automation Agent: {len(recs)} recommendations"]}


def node_ai_agent(state: GembaWalkState) -> dict:
    """Runs concurrently with node_automation_agent and node_kaizen_agent -
    see their docstrings."""
    recs, raw = run_ai_agent(state["metadata"], state["diagnostics"])
    return {"recommendations": recs, "trace": [f"AI Agentic Agent: {len(recs)} recommendations"]}


def node_kaizen_agent(state: GembaWalkState) -> dict:
    """Runs concurrently with node_automation_agent, node_ai_agent and
    node_flow_agent (all four fan out from PE Agent and only depend on its
    diagnostics, not on each other's output) - this is also the sole target
    of the review loop's "revise" edge, so on a revision round only this
    node re-runs before flowing back into node_postprocess.
    """
    recs, raw = run_kaizen_agent(state["metadata"], state["diagnostics"])
    round_number = state.get("review_round", 1)
    return {"recommendations": recs, "trace": [f"Kaizen Agent (round {round_number}): {len(recs)} recommendations"]}


def node_postprocess(state: GembaWalkState) -> dict:
    """Sole fan-in point before Reviewer Agent: runs once every branch
    active in this superstep has completed - Automation, AI Agentic, Kaizen
    and Process Flow on the initial pass, or just Kaizen alone on a revision
    round (verified empirically that LangGraph's join still fires correctly
    when only one of several predecessors re-triggers it - see the module
    docstring for why this must be the ONLY node feeding Reviewer Agent).
    By the time this executes, state["recommendations"] holds the full
    merged list. Roadmap-horizon assignment and duplicate flagging mutate
    those Recommendation objects IN PLACE; this node adds no new items
    itself, so it returns an empty recommendations list rather than
    re-appending the same objects onto the additive reducer (which would
    double-count them). Process Flow Agent's diagrams/future-state steps use
    the `_last_write` reducer and simply pass through untouched.
    """
    round_number = state.get("review_round", 1)
    full_list = state.get("recommendations", [])
    assign_roadmap_horizons(full_list)
    _flag_duplicates(full_list)
    return {"recommendations": [], "trace": [f"Postprocess (round {round_number}): horizons assigned, duplicates flagged"]}


def node_flow_agent(state: GembaWalkState) -> dict:
    """Runs concurrently with node_automation_agent, node_ai_agent and
    node_kaizen_agent - see their docstrings. Reasons directly from PE
    Agent's diagnostic automation/AI-readiness scores rather than waiting
    for the other three agents' specific recommendation titles (see
    flow_agent.py's module docstring for the precision/speed trade-off).
    """
    future_steps, notes, current_mermaid, future_mermaid = run_flow_agent(
        state["metadata"], state["diagnostics"]
    )
    return {
        "flow_mermaid_current": current_mermaid, "flow_mermaid_future": future_mermaid,
        "future_diagnostics": future_steps,
        "trace": [f"Process Flow Agent: future state has {len(future_steps)} steps. {notes[:200]}"],
    }


def node_review_agent(state: GembaWalkState) -> dict:
    round_number = state.get("review_round", 1)
    recommendations = state.get("recommendations", [])

    review_note, raw_answer, question, contexts = run_review_agent(
        state["metadata"], state["diagnostics"], recommendations, round_number=round_number
    )

    # `contexts` from the ReAct loop is only the knowledge-base chunks the
    # Reviewer Agent retrieved - but its critique is mostly about THIS
    # process's own facts (FTE, savings figures, step names), which live in
    # `question` (the full prompt), not the KB. Scoring faithfulness/context
    # metrics against KB chunks alone was measuring the wrong ground truth
    # and drove every run's scores toward zero regardless of answer quality.
    # `question` itself is legitimate grounding: the reviewer is supposed to
    # draw its claims from exactly that process data.
    ragas_score = evaluate_response(question=question, answer=raw_answer, contexts=contexts + [question])
    settings = get_settings()
    ragas_passed = ragas_score.passes(settings.ragas_min_score)

    # Deep evaluation: deterministic grounding + numeric sanity checks that
    # RAGAS (which only judges the reviewer's narrative answer) can't catch -
    # e.g. a recommendation claiming more FTE savings than the process has,
    # or naming a system never mentioned anywhere in the process intake.
    deep_result = deep_evaluate_recommendations(
        state["metadata"], state["diagnostics"], recommendations, round_number=round_number
    )

    needs_revision = (
        review_note.verdict == "needs_revision" or not ragas_passed or not deep_result.passed
    ) and round_number < settings.ragas_max_review_rounds

    if not ragas_passed:
        for r in recommendations:
            if not r.reviewer_notes:
                r.reviewer_notes = "RAGAS score below threshold this round - under revision."

    trace = [
        f"Reviewer Agent (round {round_number}): verdict={review_note.verdict}, "
        f"RAGAS overall={ragas_score.overall:.2f} (threshold {settings.ragas_min_score}), "
        f"deep_eval={'pass' if deep_result.passed else 'FAIL'} "
        f"({len(deep_result.findings)} finding(s), {deep_result.corrections_applied} auto-corrected), "
        f"needs_revision={needs_revision}"
    ]

    return {
        "review_notes": state.get("review_notes", []) + [review_note],
        "ragas_scores": state.get("ragas_scores", []) + [ragas_score],
        "deep_eval_findings": deep_result.findings,
        "needs_revision": needs_revision,
        "review_round": round_number + 1,
        "trace": trace,
    }


def route_after_review(state: GembaWalkState) -> str:
    return "revise" if state.get("needs_revision") else "finalize"


def node_finalize(state: GembaWalkState) -> dict:
    """Computes savings/exec-summary from a locally-filtered (non-duplicate)
    view of the recommendations. Deliberately does NOT return
    "recommendations" in the update dict: that key uses the additive
    reducer (for the parallel Automation/AI fan-out earlier in the graph),
    so returning even the *same, filtered* list here would concatenate it
    onto what's already accumulated and double-count everything. The state's
    "recommendations" key stays the full accumulated list (including
    flagged duplicates, for auditability) - callers filter `is_duplicate`
    themselves, same as this function does locally.
    """
    metadata = state["metadata"]
    diagnostics = state["diagnostics"]
    recommendations = [r for r in state.get("recommendations", []) if not r.is_duplicate]

    baseline = compute_current_state_baseline(metadata, diagnostics)
    savings = aggregate_savings(metadata, recommendations)
    savings["baseline"] = baseline

    exec_summary = _generate_executive_summary(metadata, diagnostics, recommendations, savings)
    kpi_summary = compute_kpis(metadata, diagnostics, recommendations, savings)

    return {
        "executive_summary": exec_summary, "savings_summary": savings, "kpi_summary": kpi_summary,
        "trace": ["Finalize: savings aggregated, KPIs benchmarked, and executive summary generated"],
    }


def _generate_executive_summary(metadata, diagnostics, recommendations, savings: dict) -> str:
    llm = get_chat_model(temperature=0.3)
    quick_wins = [r for r in recommendations if r.prioritization.quadrant == "Quick Win"][:8]
    top_wastes = {}
    for d in diagnostics:
        for w in d.lean_wastes:
            top_wastes[w.value] = top_wastes.get(w.value, 0) + 1

    prompt = f"""You are a Senior Director of Process Excellence delivering the final
executive summary of a Gemba walk diagnostic for "{metadata.process_name}"
(Team: {metadata.team_name}).

Baseline: {metadata.current_fte} FTE, {metadata.current_volume} volume/period,
{metadata.aht_minutes} min AHT. Process Cycle Efficiency: {savings['baseline']['process_cycle_efficiency_pct']}%.
Top Lean wastes observed: {top_wastes}.

{len(recommendations)} recommendations identified ({savings['quick_win_count']} quick wins,
{savings['strategic_count']} strategic). Estimated blended efficiency improvement:
{savings['blended_efficiency_improvement_pct']}% (target range {savings['target_efficiency_range_pct']}).
Estimated FTE savings (FTEs released): {savings['total_fte_savings']}.
In-Year savings: ${savings['in_year_savings']:,.0f} (based on {savings['months_remaining_in_year']} months
remaining in the calendar year). 12-Month (full run-rate) savings: ${savings['twelve_month_savings']:,.0f}
(annual FTE cost provided by the user: ${savings['annual_fte_cost']:,.0f}/FTE/year).

Top quick wins: {[q.title for q in quick_wins]}

Write a client-ready executive summary (350-500 words) with these sections:
1. Process Overview & Current State
2. Key Findings (root causes, not just symptoms)
3. Improvement Opportunity Summary (Lean, Automation, AI - by category)
4. HOW THESE OPPORTUNITIES WILL BE DELIVERED - a concrete implementation
   approach paragraph explaining the delivery mechanism for each major
   category (e.g. how a Kaizen quick win gets implemented in practice, how
   an RPA bot gets built/deployed/governed, how a GenAI pilot gets scoped
   and rolled out with human-in-the-loop controls), not just what the
   opportunity is.
5. Expected Business Impact & Efficiency Improvement, with assumptions stated.
Use clear business language suitable for a Process Excellence steering committee."""

    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def build_gemba_walk_graph():
    graph = StateGraph(GembaWalkState)

    graph.add_node("pe_agent", node_pe_agent)
    graph.add_node("automation_agent", node_automation_agent)
    graph.add_node("ai_agent", node_ai_agent)
    graph.add_node("kaizen_agent", node_kaizen_agent)
    graph.add_node("postprocess", node_postprocess)
    graph.add_node("flow_agent", node_flow_agent)
    graph.add_node("review_agent", node_review_agent)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("pe_agent")
    # Fan-out: all four branches depend only on PE Agent's diagnostics, not
    # on each other, so LangGraph runs them in the same superstep (parallel).
    graph.add_edge("pe_agent", "automation_agent")
    graph.add_edge("pe_agent", "ai_agent")
    graph.add_edge("pe_agent", "kaizen_agent")
    graph.add_edge("pe_agent", "flow_agent")
    # Single fan-in: postprocess joins all four parallel branches (not just
    # the three recommendation-generating ones) - see the module docstring
    # for why review_agent must have exactly this one incoming edge rather
    # than a second parallel edge from flow_agent.
    graph.add_edge("automation_agent", "postprocess")
    graph.add_edge("ai_agent", "postprocess")
    graph.add_edge("kaizen_agent", "postprocess")
    graph.add_edge("flow_agent", "postprocess")
    graph.add_edge("postprocess", "review_agent")
    graph.add_conditional_edges("review_agent", route_after_review, {"revise": "kaizen_agent", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=_checkpointer)


def run_full_diagnostic(metadata, raw_steps) -> GembaWalkState:
    """Entry point used by the FastAPI backend to run the complete
    multi-agent diagnostic end to end.
    """
    app = build_gemba_walk_graph()
    initial_state: GembaWalkState = {
        "metadata": metadata,
        "raw_steps": raw_steps,
        "recommendations": [],
        "review_notes": [],
        "ragas_scores": [],
        "deep_eval_findings": [],
        "kpi_summary": {},
        "review_round": 1,
        "trace": [],
    }
    thread_id = str(uuid.uuid4())
    logger.info(f"Starting Gemba Walk multi-agent diagnostic for '{metadata.process_name}' (thread_id={thread_id})")
    final_state = app.invoke(
        initial_state, config={"recursion_limit": 50, "configurable": {"thread_id": thread_id}}
    )
    logger.info("Gemba Walk diagnostic complete.")
    return final_state

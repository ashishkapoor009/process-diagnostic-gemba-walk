"""LangGraph orchestration of the six-agent Gemba Walk workflow:

RAG retrieve -> PE Agent -> Automation Agent -> AI Agentic Agent ->
Kaizen Agent -> Process Flow Agent -> Reviewer Agent -> RAGAS evaluation
-> (loop back to Kaizen Agent for revision if below threshold, up to
ragas_max_review_rounds) -> Finalize (savings roll-up + executive summary
+ persistence).
"""
from __future__ import annotations

from difflib import SequenceMatcher

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
from app.evaluation.ragas import evaluate_response
from app.schemas.agent_state import GembaWalkState
from app.utils.logging import get_logger

logger = get_logger(__name__)


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
    trace = state.get("trace", [])
    trace.append(f"PE Agent: diagnosed {len(diagnostics)} steps")
    return {"diagnostics": diagnostics, "trace": trace}


def node_automation_agent(state: GembaWalkState) -> dict:
    recs, raw = run_automation_agent(state["metadata"], state["diagnostics"])
    trace = state.get("trace", [])
    trace.append(f"Automation Agent: {len(recs)} recommendations")
    existing = state.get("recommendations", [])
    return {"recommendations": existing + recs, "trace": trace}


def node_ai_agent(state: GembaWalkState) -> dict:
    recs, raw = run_ai_agent(state["metadata"], state["diagnostics"])
    trace = state.get("trace", [])
    trace.append(f"AI Agentic Agent: {len(recs)} recommendations")
    existing = state.get("recommendations", [])
    return {"recommendations": existing + recs, "trace": trace}


def node_kaizen_agent(state: GembaWalkState) -> dict:
    recs, raw = run_kaizen_agent(state["metadata"], state["diagnostics"])
    trace = state.get("trace", [])
    round_number = state.get("review_round", 1)
    trace.append(f"Kaizen Agent (round {round_number}): {len(recs)} recommendations")
    all_recs = state.get("recommendations", []) + recs
    all_recs = assign_roadmap_horizons(all_recs)
    all_recs = _flag_duplicates(all_recs)
    return {"recommendations": all_recs, "trace": trace}


def node_flow_agent(state: GembaWalkState) -> dict:
    rec_summaries = [f"{r.category.value}: {r.title} (step {r.step_number})" for r in state.get("recommendations", [])]
    future_steps, notes, current_mermaid, future_mermaid = run_flow_agent(
        state["metadata"], state["diagnostics"], rec_summaries
    )
    trace = state.get("trace", [])
    trace.append(f"Process Flow Agent: future state has {len(future_steps)} steps. {notes[:200]}")
    return {"flow_mermaid_current": current_mermaid, "flow_mermaid_future": future_mermaid, "trace": trace}


def node_review_agent(state: GembaWalkState) -> dict:
    round_number = state.get("review_round", 1)
    review_note, raw_answer, question, contexts = run_review_agent(
        state["metadata"], state["diagnostics"], state.get("recommendations", []), round_number=round_number
    )

    ragas_score = evaluate_response(question=question, answer=raw_answer, contexts=contexts)
    settings = get_settings()
    passed = ragas_score.passes(settings.ragas_min_score)
    needs_revision = (review_note.verdict == "needs_revision" or not passed) and round_number < settings.ragas_max_review_rounds

    if not passed:
        for r in state.get("recommendations", []):
            if not r.reviewer_notes:
                r.reviewer_notes = "RAGAS score below threshold this round - under revision."

    trace = state.get("trace", [])
    trace.append(
        f"Reviewer Agent (round {round_number}): verdict={review_note.verdict}, "
        f"RAGAS overall={ragas_score.overall:.2f} (threshold {settings.ragas_min_score}), "
        f"needs_revision={needs_revision}"
    )

    review_notes = state.get("review_notes", []) + [review_note]
    ragas_scores = state.get("ragas_scores", []) + [ragas_score]

    return {
        "review_notes": review_notes,
        "ragas_scores": ragas_scores,
        "needs_revision": needs_revision,
        "review_round": round_number + 1,
        "trace": trace,
    }


def route_after_review(state: GembaWalkState) -> str:
    return "revise" if state.get("needs_revision") else "finalize"


def node_finalize(state: GembaWalkState) -> dict:
    metadata = state["metadata"]
    diagnostics = state["diagnostics"]
    recommendations = [r for r in state.get("recommendations", []) if not r.is_duplicate]

    baseline = compute_current_state_baseline(metadata, diagnostics)
    savings = aggregate_savings(metadata, recommendations)
    savings["baseline"] = baseline

    exec_summary = _generate_executive_summary(metadata, diagnostics, recommendations, savings)

    trace = state.get("trace", [])
    trace.append("Finalize: savings aggregated and executive summary generated")

    return {"executive_summary": exec_summary, "savings_summary": savings, "recommendations": recommendations, "trace": trace}


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
Estimated FTE savings: {savings['total_fte_savings']}. Estimated annual cost savings:
${savings['total_annual_cost_savings']:,.0f} (assumption: ${savings['annual_cost_per_fte_assumption']:,.0f}/FTE/year).

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
    graph.add_node("flow_agent", node_flow_agent)
    graph.add_node("review_agent", node_review_agent)
    graph.add_node("finalize", node_finalize)

    graph.set_entry_point("pe_agent")
    graph.add_edge("pe_agent", "automation_agent")
    graph.add_edge("automation_agent", "ai_agent")
    graph.add_edge("ai_agent", "kaizen_agent")
    graph.add_edge("kaizen_agent", "flow_agent")
    graph.add_edge("flow_agent", "review_agent")
    graph.add_conditional_edges("review_agent", route_after_review, {"revise": "kaizen_agent", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    return graph.compile()


def run_full_diagnostic(metadata, raw_steps) -> GembaWalkState:
    """Entry point used by the Streamlit UI / FastAPI backend to run the
    complete multi-agent diagnostic end to end.
    """
    app = build_gemba_walk_graph()
    initial_state: GembaWalkState = {
        "metadata": metadata,
        "raw_steps": raw_steps,
        "recommendations": [],
        "review_notes": [],
        "ragas_scores": [],
        "review_round": 1,
        "trace": [],
    }
    logger.info(f"Starting Gemba Walk multi-agent diagnostic for '{metadata.process_name}'")
    final_state = app.invoke(initial_state, config={"recursion_limit": 50})
    logger.info("Gemba Walk diagnostic complete.")
    return final_state

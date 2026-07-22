# Agent Interaction Model

## The Six Agents

| # | Agent | Persona | Primary Output |
|---|-------|---------|-----------------|
| 1 | **PE Agent** | Lean Six Sigma Master Black Belt | Per-step diagnostics: VA/NVA/BNVA, Lean waste, root cause, risk, automation/AI readiness scores |
| 2 | **Process Flow Agent** | Business Process Architect | Current-state (swimlane) and future-state (flowchart) Mermaid diagrams |
| 3 | **Kaizen Agent** | Continuous Improvement Lead | Lean/standardization/governance recommendations + roadmap horizon assignment for ALL recommendations |
| 4 | **Automation Agent** | RPA/Intelligent Automation Architect | Automation recommendations (Excel/Power Automate/RPA/API/OCR/etc.) |
| 5 | **AI Agentic Agent** | Applied AI/GenAI Solutions Architect | GenAI/Agentic AI/predictive recommendations |
| 6 | **Reviewer Agent** | Senior Director, Process Excellence | Critical review: hallucinations, gaps, duplicates, prioritization/ROI sanity check, confidence score, verdict |

## Why This Order

`PE -> Automation -> AI -> Kaizen -> Flow -> Reviewer` (see `app/agents/orchestrator.py`):

1. **PE Agent runs first** because every other agent depends on its
   diagnostics (waste, VA/NVA, root cause, readiness scores) as input.
2. **Automation and AI Agents run in parallel logic** (sequential in the
   graph for simplicity, but independent in reasoning) - each scans the
   same diagnostics for a different lens (rule-based vs. judgment-based
   opportunities) and is explicitly instructed not to duplicate the other's
   recommendation type.
3. **Kaizen Agent runs after** Automation/AI so it can see the full
   recommendation set and assign a coherent roadmap horizon (Quick Win /
   30 / 60 / 90-Day / Strategic) across ALL recommendations, not just its own.
4. **Process Flow Agent runs after Kaizen** so the future-state flow
   reflects the complete, roadmap-assigned recommendation set.
5. **Reviewer Agent runs last**, seeing everything, and is the only agent
   whose output is gated by RAGAS - if quality is insufficient, the graph
   loops back to the Kaizen Agent (which re-synthesizes using the reviewer's
   feedback implicitly available in the next round's context) rather than
   restarting the entire pipeline.

## Shared Infrastructure Every Agent Uses

- **`app/agents/tools.py`** - `search_knowledge_base` (RAG retrieval) and
  `get_process_details` (process data lookup) LangChain tools, given to
  every agent so it can genuinely act, not just generate text.
- **`app/agents/react_utils.py`** - wraps LangGraph's `create_react_agent`
  for the Reason-Act-Observe loop, then a second structured-output call
  coerces the free-text answer into a strict Pydantic schema.
- **`app/agents/context_capture.py`** - records which knowledge-base chunks
  an agent actually retrieved during its ReAct loop (via a `ContextVar`),
  so the Reviewer Agent's RAGAS evaluation scores against real, traceable context.

## Confidence Scoring

Every recommendation carries a `source_type` (Retrieved Knowledge / LLM
Reasoning / Both) and a `confidence_score` (0-1), so a Process Excellence
lead can immediately see which recommendations are grounded in established
best practice, which are the agent's own inference about this specific
process, and which are both - directly informing how much SME validation
each recommendation needs before it enters a business case.

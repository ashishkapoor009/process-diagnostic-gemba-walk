# GenAI & Agentic AI Opportunity Patterns

## When GenAI/LLM Beats Traditional Automation
Traditional RPA/workflow automation is deterministic - it excels at
structured, rule-based steps. GenAI/LLMs excel where the step requires
*judgment on unstructured input*: reading free-text emails/documents,
summarizing, classifying intent, drafting responses, answering "how do I..."
questions, or reconciling ambiguous/inconsistent data. If a step's
bottleneck is a human reading and interpreting unstructured text before
deciding what to do next, it's a GenAI candidate, not just an RPA one.

## Core GenAI Use Case Patterns
- **Document AI / Extraction** - LLM-based extraction from contracts,
  invoices, claims, resumes into structured fields, handling format
  variation that breaks rule-based OCR templates.
- **Knowledge Assistant / Semantic Search (RAG)** - ground an LLM in a
  company's SOPs/policies/knowledge base so staff (or customers) get
  accurate, cited answers instantly instead of searching manuals or
  escalating to SMEs. This is exactly the RAG pattern this tool itself uses.
- **Intelligent Routing / Classification** - classify inbound tickets,
  emails, or cases by intent/urgency/team using an LLM, replacing manual
  triage.
- **Summarization** - condense long case histories, call transcripts, or
  documents for faster handling and QA review.
- **Drafting / Co-pilot** - LLM drafts a first-pass response, report, or
  document for human review/approval, cutting authoring time significantly
  while keeping a human in the loop for judgment/accountability.
- **Predictive Models** - traditional ML (not generative) for forecasting
  volume, churn, fraud risk, or SLA breach risk to enable proactive action.
- **Recommendation Engines** - suggest next-best-action to agents/customers
  based on historical patterns.

## Agentic AI Patterns
Agentic AI goes beyond single-turn generation: an agent can plan a sequence
of actions, call tools/APIs, observe results, and adapt - the ReAct
(Reason + Act) pattern this application itself is built on.
- **Planning Agent** - decomposes a complex multi-step goal into an ordered
  task plan (e.g. "process this claim end-to-end": extract documents,
  validate against policy, check fraud rules, compute payout, draft
  decision letter).
- **Decision Agent** - applies business rules/policy plus retrieved context
  to make or recommend a bounded decision, with a confidence score and an
  escalation path when confidence is low.
- **Multi-Agent Systems** - specialist agents (e.g. one per domain: intake,
  validation, decisioning, communication) coordinate via a shared state/
  orchestrator, each auditable independently - mirrors this tool's own
  six-agent architecture and is a strong template to recommend for complex,
  multi-stage back-office processes.
- **Autonomous AI with Human-in-the-Loop Guardrails** - full end-to-end
  automation for low-risk/high-confidence cases, with automatic hand-off to
  a human for high-risk, low-confidence, or policy-exception cases.

## AI Readiness Signals (score higher when present)
High-quality historical data/labels available; clear, describable decision
criteria (even if currently tacit/expert judgment); tolerance for
occasional error with human review; high volume (amortizes model
development cost); and a defined escalation/fallback path. Low readiness:
no digital data trail, decisions carry legal/safety liability with zero
error tolerance, or volume too low to justify model development.

## Governance for AI/GenAI in Regulated Processes
Any AI recommendation touching compliance-flagged or high customer-impact
steps must include: human-in-the-loop review threshold, explainability/
audit trail, bias/fairness check where decisions affect individuals, and
a defined model monitoring and drift-review cadence.

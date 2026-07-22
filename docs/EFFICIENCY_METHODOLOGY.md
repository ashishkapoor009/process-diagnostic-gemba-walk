# How Improvement Opportunities Are Delivered & How the 25-30% Target Is Reached

This document explains, category by category, both *how* each type of
recommendation actually gets implemented in a real organization, and *how*
its savings are calculated and rolled up into the headline efficiency number.

## 1. Delivery Mechanism by Category

### Lean / Process Simplification / Standardization (Kaizen Agent)
**How it's delivered:** Typically a 1-2 week Kaizen event: a facilitated
workshop with the process owner and frontline staff, using the PE Agent's
root-cause findings as the starting A3. Deliverables are a revised SOP,
an updated RACI, and - where relevant - visual management boards or a
5S/Kanban/Poka-Yoke/SMED change to the physical or digital workspace. No
new system is required, so time-to-value is typically 1-4 weeks.
**Governance:** Process owner signs off the revised SOP; Change Management
communicates the change and runs a short training session before cutover.

### Automation - Excel/Power Query/Power Automate (Automation Agent)
**How it's delivered:** Built by a citizen developer or the automation
CoE using low-code tools already licensed under most Microsoft 365
tenants. Typically 1-4 weeks: build, UAT with the process owner, deploy to
production, and hand over a one-page runbook. Requires no IT security
review beyond standard M365 governance.

### Automation - Full RPA (UiPath/Automation Anywhere/Blue Prism/Power
Automate Desktop) or API Integration (Automation Agent)
**How it's delivered:** Goes through the organization's RPA CoE / IT
delivery process: bot design document, dev, UAT, security/credential
vaulting review, hypercare, then handover to a bot support team with a
monitoring dashboard and defined exception-handling queue. Typically
6-12 weeks depending on system complexity. API integration is preferred
over UI-level RPA whenever both systems expose one, since it's materially
cheaper to maintain long-term.

### AI / GenAI / Document AI (AI Agentic Agent)
**How it's delivered:** Scoped as a pilot on a contained sub-process first
(e.g. one document type, one queue), with a defined human-in-the-loop
review threshold and a measured accuracy baseline before wider rollout.
Delivery involves: prompt/pipeline design, evaluation against a labeled
sample (mirroring this tool's own RAGAS gate), a pilot with live human
oversight, then phased confidence-based automation expansion. Typically
6-12 weeks to pilot, longer to full autonomous scale - governance
(explainability, bias check, monitoring cadence) is mandatory for any
step touching compliance or customer-impact risk.

### Agentic AI / Multi-Agent Systems (AI Agentic Agent)
**How it's delivered:** Reserved for complex, multi-stage steps. Delivered
incrementally: start with a single Planning or Decision Agent on the
highest-value sub-task, prove reliability and cost, then expand into a
coordinated multi-agent system (mirroring this application's own
architecture) with a human escalation path for low-confidence cases.
Strategic-horizon initiative, typically 3-6+ months.

### Dashboard / Analytics / Governance & Control (Kaizen Agent)
**How it's delivered:** Usually a fast-follow to any automation/AI
initiative - a Power BI/dashboard build against the same data captured by
the new automated step, plus a defined control (e.g. exception threshold
alert) so the process stays managed (BPM CBOK Maturity Level 4) rather
than just measured once and forgotten.

## 2. How the Numbers Are Calculated

Every recommendation's savings are estimated by its authoring agent with
explicitly stated assumptions (visible in the UI and every report under
"Savings assumptions"), then rolled up deterministically in
`app/agents/savings_calculator.py` - never by asking the LLM to do arithmetic:

```
Time Savings/Txn   = Current Touch Time − Future Touch Time (post automation/simplification)
FTE Savings        = (Time Savings/Txn × Volume) / Productive Minutes per FTE per Period
Annual Cost Savings = FTE Savings × Assumed Fully-Loaded Annual Cost per FTE
Blended Efficiency % = confidence-weighted average of each approved
                        recommendation's AHT-reduction %, capped by the
                        FTE-savings-implied ceiling (current_fte-relative)
```

Duplicate recommendations (flagged by the Reviewer Agent / orchestrator's
similarity check) are excluded from the roll-up so savings are never
double-counted across agents recommending overlapping fixes on the same step.

## 3. Why 25-30% Is a Realistic Target, Not a Guess

Per the Lean Six Sigma and RPA best-practice sources in this tool's own
knowledge base (`app/rag/knowledge_base/`):
- Eliminating pure NVA waste (waiting, rework, hand-offs) typically
  recovers **10-15%** of cycle time on a typical unoptimized back-office process.
- Automating the rules-based subset of remaining manual steps typically
  removes **70-95%** of *their* touch time, contributing another **10-15%**
  blended across the whole process.
- AI-assisted acceleration of judgment-heavy steps (faster
  read/classify/draft) contributes the remainder, particularly on
  processes with heavy unstructured-document handling.

Summed and confidence-weighted (not naively added, to avoid
double-counting overlapping steps), these three levers land most
processes with meaningful manual/hand-off content in the **25-30%**
blended efficiency range shown as this tool's calibration target
(`TARGET_EFFICIENCY_LOW`/`TARGET_EFFICIENCY_HIGH` in `.env`) - individual
processes may land above or below depending on their actual current-state
maturity, which is exactly what the diagnostic measures.

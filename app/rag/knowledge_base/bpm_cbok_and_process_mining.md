# BPM CBOK & Process Mining

## BPM CBOK (Business Process Management Common Body of Knowledge)
BPM CBOK defines process management maturity across dimensions: process
modeling, process analysis, process design, process performance
measurement, process transformation, process organization, and enterprise
process management. Key artifacts:
- **Process Architecture** - hierarchy of processes (Level 1 value chain
  down to Level 4-5 detailed task/procedure).
- **RACI Matrix** - Responsible, Accountable, Consulted, Informed - clarifies
  ownership at each step, a common gap when hand-offs are unclear.
- **SIPOC** - Supplier, Input, Process, Output, Customer - a high-level
  process framing used before detailed mapping.

## BPMN (Business Process Model and Notation)
Standard notation for process flowcharts: Events (circles), Activities
(rounded rectangles), Gateways (diamonds - decision/parallel/merge points),
and Swimlanes (who/what system owns each activity). This tool's Process
Flow Agent generates BPMN-style swimlane flows in Mermaid syntax so outputs
are portable into Visio, Lucidchart, or draw.io.

## Process Maturity Levels (1-5)
1. **Initial/Ad-hoc** - undocumented, tribal knowledge, inconsistent execution.
2. **Repeatable** - documented but not standardized across teams/shifts.
3. **Defined** - standardized SOPs, trained staff, consistent execution.
4. **Managed** - measured with KPIs/SLAs, data-driven control, dashboards.
5. **Optimized** - continuously improved, automated where sensible, AI-augmented decisioning, predictive controls.

Governance, documentation, automation, and analytics maturity should each be
scored independently - a process can have excellent documentation (Level 4)
but zero automation (Level 1), which points directly at the improvement
category to prioritize.

## Process Mining
Uses system event logs (timestamps, user IDs, transaction IDs) to
reconstruct the *actual* as-executed process variants, rather than relying
on interviews or documentation. Reveals: rework loops, non-standard paths,
approval bypass, and true cycle time distributions (not averages).
Recommended whenever applications_used/systems_used indicates a system of
record with timestamped audit trails (ERP, ticketing, workflow tools) -
flag as an "Analytics" improvement opportunity to validate manually-reported
cycle times against system truth.

## Value Stream Mapping (VSM)
Maps end-to-end material AND information flow for a process, distinguishing
Value-Added time from wait/queue time at each step, and computing:
- **Process Cycle Efficiency (PCE)** = Total VA Time / Total Lead Time.
  Best-in-class back-office processes achieve 25%+ PCE; most unoptimized
  processes run below 10%, meaning >90% of lead time is waiting/queueing,
  not work being done - the single biggest lever for cycle-time reduction
  is usually eliminating queue/wait time, not speeding up the work itself.

## A3 Problem Solving
A one-page (A3 paper size) structured problem-solving document: background,
current condition, goal, root cause analysis, countermeasures, plan, and
follow-up. Used to communicate a Kaizen recommendation concisely to
leadership - the Kaizen Agent's quick-win recommendations should be
A3-ready: problem, root cause, countermeasure, owner, timeline.

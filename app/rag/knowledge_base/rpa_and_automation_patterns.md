# RPA & Automation Best Practices

## Automation Suitability Criteria
A step is a good RPA/automation candidate when it is: rule-based (no
subjective judgment), high-volume/repetitive, structured/digital input,
stable (process doesn't change often), and has low exception rates. Steps
with high volume + high manual effort + low judgment score highest on
automation potential.

## Automation Tool Selection Ladder (lowest cost/effort to highest)
1. **Excel Macros / VBA** - one user, one spreadsheet, simple repetitive
   calculation or formatting task. Near-zero cost, days of effort.
2. **Power Query / Power Pivot** - repeatable data transformation/blending
   from multiple sources into a refreshable report. No-code, low effort.
3. **Power Automate (Cloud)** - trigger-based workflow across
   Microsoft 365/Dataverse/API-connected systems (approvals, notifications,
   simple data movement). Low-code, days to weeks.
4. **Power Automate Desktop / UiPath / Automation Anywhere / Blue Prism** -
   full RPA for UI-level automation across legacy/desktop apps without APIs,
   including screen scraping, multi-step swivel-chair processes. Weeks of
   effort, needs governance (bot ownership, exception handling, credential
   vaulting).
5. **API Integration** - the most robust and maintainable option when both
   systems expose APIs; eliminates UI-automation fragility entirely. Prefer
   API integration over RPA whenever both endpoints support it.
6. **Custom Python Scripts** - scheduled/triggered scripts for data
   processing, file manipulation, report generation, or gluing APIs
   together when no off-the-shelf connector exists.

## Automation Anti-Patterns
- Automating a broken process ("paving the cow path") - simplify/standardize
  first, automate second, or the bot just executes waste faster.
- No exception handling path - bots need a defined fallback when data is
  malformed or a system is down (route to human queue, alert, retry with backoff).
- No bot governance/ownership - orphaned bots break silently when source
  systems change; assign a named process owner and monitoring dashboard.

## Workflow Automation & Low-Code
Workflow automation platforms orchestrate multi-step, multi-system,
multi-approver processes with built-in audit trail, SLA timers, and
escalation - well suited to replacing email-and-spreadsheet-based approval
chains. Low-code platforms (Power Apps, Retool, OutSystems) suit
department-owned tools that don't justify full custom development.

## Document & Communication Automation
- **OCR / Document AI** - structured extraction from invoices, forms,
  contracts, ID documents; pairs with a human-in-the-loop review queue for
  low-confidence extractions.
- **Email Automation** - auto-classification, routing, and templated
  response generation for high-volume inbound email queues.
- **Chatbot / Conversational automation** - deflects Tier-1 FAQ-style
  requests, freeing FTE capacity for exception handling.
- **Computer Vision** - for physical inspection, quality control, or
  document layout understanding beyond plain OCR text extraction.

## Estimating Automation Savings
Typical rule of thumb: fully automating a rules-based manual step removes
70-95% of its touch time (residual time is exception handling/oversight).
Partial automation (e.g. auto-populate + human verify) typically removes
30-50% of touch time. Always state the assumed automation rate explicitly
when calculating FTE/cost savings.

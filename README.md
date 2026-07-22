# Process Diagnostic / Gemba Walk Multi-Agent Solution

An enterprise-grade, multi-agent AI application that behaves like a **20+
year Lean Six Sigma Master Black Belt consulting team**, conducting a
Gemba-walk diagnostic on any business process and producing Lean,
Process Simplification/Standardization, Automation (RPA/low-code), and
AI/GenAI/Agentic improvement opportunities for **every single step** -
targeting a **25-30% blended efficiency improvement**, evaluated
automatically for quality with **RAGAS**, and delivered as client-ready
PDF/Word/Excel/PowerPoint reports.

## What It Does

1. **Intake** - collects Process Name, Department, Business Function,
   Current FTE, Current Volume, AHT, Country, LOB (mandatory) plus Pain
   Areas, Dependencies, Compliance Requirements, etc. (optional).
2. **Extraction** - accepts typed process steps OR an uploaded document
   (PDF, DOCX, PPT, PNG/JPG, BPMN, Visio XML export, CSV, Excel), using
   OCR (Tesseract + OpenCV) and an LLM structured-extraction pass to
   reconstruct the ordered step list automatically.
3. **Six-Agent Diagnostic** (LangGraph, ReAct architecture, RAG-grounded):
   - **PE Agent** - Gemba-walk diagnostic: VA/NVA/BNVA, Lean waste
     (TIMWOODS + hand-offs/bottlenecks/rework/queue/delay/approvals), root
     cause, risk, automation/AI readiness scoring.
   - **Process Flow Agent** - current-state and future-state Mermaid
     flow/swimlane diagrams.
   - **Kaizen Agent** - Lean/standardization/governance recommendations +
     roadmap horizon assignment (Quick Win / 30 / 60 / 90-Day / Strategic).
   - **Automation Agent** - Excel macros through full RPA/API integration,
     choosing the right tool for each step.
   - **AI Agentic Agent** - GenAI, agentic AI, document AI, predictive
     models, multi-agent systems.
   - **Reviewer Agent** - Senior-Director-level critical review: catches
     hallucinations, gaps, duplicates, weak prioritization - gated by
     **RAGAS** (faithfulness, answer relevancy, context precision/recall/
     relevancy), automatically triggering a revision round when below threshold.
4. **Visualization** - Mermaid current/future flow, Value Stream Map,
   Process Bottleneck Map (NetworkX), Lean Waste Heatmap, Automation/AI
   Opportunity Heatmap, Priority Matrix, Business-Value-vs-Effort Bubble
   Chart, Roadmap Timeline (all Plotly).
5. **Reports** - downloadable PDF (ReportLab), Word (python-docx), Excel
   (pandas/XlsxWriter), and PowerPoint (python-pptx) deliverables.
6. **Persistence & Audit** - every diagnostic, recommendation, RAGAS score,
   RAG query, upload, and user action is stored in SQLite for full
   traceability, and can be reopened later from the Dashboard.

## Tech Stack

Python 3.11/3.12 · Streamlit · LangGraph · LangChain · ReAct agent
architecture · SQLite (SQLAlchemy) · ChromaDB (vector store) · RAGAS ·
Pydantic · FastAPI (optional backend) · NetworkX · Mermaid · Graphviz ·
Pandas · Plotly · python-docx · ReportLab · Pillow/OpenCV · Tesseract OCR ·
Unstructured.io · PyMuPDF · pdfplumber · OpenAI / Azure OpenAI compatible models.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then set OPENAI_API_KEY
streamlit run streamlit_app.py
```
Full setup (including Tesseract/Graphviz system packages) is in
[`docs/INSTALLATION.md`](docs/INSTALLATION.md). Try it instantly with the
sample process in [`sample_data/`](sample_data/).

## Project Structure

```
process-excellence-agent/
├── app/
│   ├── agents/          # PE, Flow, Kaizen, Automation, AI, Reviewer agents + LangGraph orchestrator
│   ├── rag/              # Knowledge base, ChromaDB vector store, retriever
│   ├── database/         # SQLAlchemy models, CRUD, DB->Pydantic rehydration
│   ├── extraction/       # Document parsing, OCR, LLM step extraction
│   ├── evaluation/       # RAGAS integration
│   ├── graphs/           # Mermaid, NetworkX, Plotly visualizations
│   ├── reports/          # PDF/Word/Excel/PPT generators
│   ├── schemas/          # Pydantic models (process, recommendation, evaluation, LangGraph state)
│   ├── ui/               # Streamlit styling, Mermaid rendering, pipeline runner
│   ├── config/           # Settings (pydantic-settings), LLM factory
│   ├── utils/             # Logging, retry, caching
│   └── main.py            # Optional FastAPI backend
├── pages/                 # Streamlit multipage UI (Upload, Analysis, Recommendations, Flow, Reports, KB, Settings)
├── streamlit_app.py        # Dashboard / entry point
├── tests/                  # pytest suite (offline-safe: no LLM calls required)
├── sample_data/             # Sample process for a quick first run
├── docs/                     # Architecture, sequence, agent interaction, API, install, deployment docs
├── Dockerfile / docker-compose.yml
└── requirements.txt
```

## How the 25-30% Efficiency Target Is Delivered

See [`docs/EFFICIENCY_METHODOLOGY.md`](docs/EFFICIENCY_METHODOLOGY.md) for
the full breakdown of how Lean waste elimination, automation touch-time
reduction, and AI-assisted judgment-step acceleration combine into the
blended efficiency number shown on every report, and exactly how each
recommendation category gets implemented in practice.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - system diagram, layers, design decisions
- [Sequence Diagram](docs/SEQUENCE.md) - end-to-end run, message by message
- [Agent Interactions](docs/AGENT_INTERACTIONS.md) - why this agent order, shared tooling
- [API Reference](docs/API.md) - optional FastAPI backend endpoints
- [Installation Guide](docs/INSTALLATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md) - Streamlit Community Cloud, Render/Railway, Cloud Run, Vercel-hybrid

## Important Note on Deployment

**Streamlit cannot run on Vercel** - Vercel's serverless functions have no
persistent process and no WebSocket support, both of which Streamlit
requires. Deploy the Streamlit UI on Streamlit Community Cloud (free,
recommended), Render, Railway, or Cloud Run; see `docs/DEPLOYMENT.md` for
a fully-documented hybrid path if a single `*.vercel.app` URL is required
(a Next.js frontend on Vercel calling this app's FastAPI backend hosted elsewhere).

## License

Internal enterprise tooling scaffold - adapt freely for your organization.

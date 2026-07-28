# Architecture

## System Overview

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        EXT["Next.js Frontend\n(Vercel)"]
    end

    subgraph API["Service Layer"]
        FASTAPI["FastAPI Backend\n(app/main.py)"]
    end

    subgraph Orchestration["LangGraph Orchestration"]
        PIPE["orchestrator.py\nStateGraph"]
        PE["PE Agent"]
        AUTO["Automation Agent"]
        AI["AI Agentic Agent"]
        KAI["Kaizen Agent"]
        FLOW["Process Flow Agent"]
        REV["Reviewer Agent"]
        RAGAS["RAGAS Evaluation"]
    end

    subgraph Knowledge["RAG Layer"]
        KB["Knowledge Base\n(Markdown corpus)"]
        CHROMA["ChromaDB\nVector Store"]
    end

    subgraph Extraction["Extraction Pipeline"]
        PARSE["Document Parsers\n(PyMuPDF/pdfplumber/docx/pptx)"]
        OCR["Tesseract OCR + OpenCV"]
        LLMX["LLM Step Extractor"]
    end

    subgraph Storage["Persistence"]
        SQLITE[("SQLite\nusers/projects/processes/steps/\nrecommendations/evaluations/audit")]
    end

    subgraph Reports["Report Generation"]
        PDF["ReportLab PDF"]
        WORD["python-docx"]
        XLS["Excel (pandas/XlsxWriter)"]
        PPT["python-pptx"]
    end

    EXT --> FASTAPI --> PIPE
    FASTAPI --> PARSE --> OCR
    PARSE --> LLMX --> PIPE

    PIPE --> PE --> AUTO --> AI --> KAI --> FLOW --> REV --> RAGAS
    RAGAS -- "below threshold" --> KAI
    RAGAS -- "approved" --> PIPE

    PE -.retrieve.-> CHROMA
    AUTO -.retrieve.-> CHROMA
    AI -.retrieve.-> CHROMA
    KAI -.retrieve.-> CHROMA
    FLOW -.retrieve.-> CHROMA
    REV -.retrieve.-> CHROMA
    KB --> CHROMA

    PIPE --> SQLITE
    FASTAPI --> Reports
    Reports --> SQLITE
```

## Layers

1. **Client Layer** - the Next.js frontend (`process-diagnostic-frontend`,
   deployed to Vercel) that talks to the FastAPI backend.
2. **Service Layer** - the FastAPI REST API (`app/main.py`) exposing the
   pipeline to the frontend.
3. **Orchestration Layer** - a LangGraph `StateGraph` (`app/agents/orchestrator.py`)
   sequencing six ReAct agents, with a conditional edge that loops back to
   the Kaizen Agent when RAGAS scores fall below threshold.
4. **RAG Layer** - a Markdown knowledge base (`app/rag/knowledge_base/`)
   chunked and embedded into ChromaDB (`app/rag/vector_store.py`), queried
   via a shared `search_knowledge_base` LangChain tool every agent can call.
5. **Extraction Pipeline** - multi-format document parsing (PDF/DOCX/PPTX/
   image/BPMN/CSV/Excel) with OpenCV-assisted Tesseract OCR for scanned
   content, then an LLM structured-output pass that reconstructs the
   ordered process step list.
6. **Persistence** - SQLite via SQLAlchemy ORM (`app/database/models.py`):
   users, projects, processes, process_steps, recommendations,
   agent_responses, evaluation_scores, rag_history, uploads, feedback,
   audit_logs.
7. **Report Generation** - PDF (ReportLab), Word (python-docx), Excel
   (pandas/XlsxWriter), PowerPoint (python-pptx), all built from one shared
   `ReportContext` so every format stays consistent.

## Why LangGraph + ReAct (not a linear pipeline)

Each agent is built with LangGraph's `create_react_agent`, meaning it can
genuinely **reason, call a tool (RAG search or process-data lookup), observe
the result, and reason again** before producing its final answer - rather
than having all context force-fed into a single prompt. The orchestrator
graph then adds a second layer of agentic control: a **conditional edge**
that routes back to the Kaizen Agent for revision when the Reviewer Agent's
own verdict or deep evaluation's deterministic numeric/grounding checks flag
a problem, up to `MAX_REVIEW_ROUNDS` rounds (default 1).

RAGAS is **not** part of this decision loop - see "RAGAS runs independently
of the agent pipeline" below.

## Key Design Decisions

- **RAGAS runs independently of the agent pipeline**, not as a graph node.
  It only ever judged the Reviewer Agent's own narrative critique, not the
  recommendations themselves, so it was never a meaningful signal for
  whether to revise - and its four sequential LLM-judge calls (~90s) used
  to dominate pipeline latency. `app/agents/orchestrator.py`'s Reviewer
  Agent node captures its raw (question, answer, contexts) into
  `review_artifacts`; `app/services/pipeline_runner.py` persists those and
  scores them with RAGAS in a background thread *after* the pipeline has
  already returned to the caller, and exposes
  `POST /api/processes/{id}/evaluate-ragas` to re-score on demand - a
  process the agents never see or react to. `RAGAS_MIN_SCORE` (default
  0.70) still marks a score passed/failed for display.
- **RAGAS scores the exact context each agent retrieved**, not a re-run
  retrieval - `app/agents/context_capture.py` records every chunk pulled by
  the `search_knowledge_base` tool during a ReAct loop via a `ContextVar`,
  so faithfulness/context metrics reflect what the agent actually reasoned over.
- **Deterministic savings math** - LLM agents estimate a recommendation's
  own savings with stated assumptions; `app/agents/savings_calculator.py`
  performs the actual roll-up arithmetic so the headline efficiency number
  is reproducible and auditable, not LLM-generated.
- **One shared `ReportContext`** feeds all four report formats so the PDF,
  Word, Excel, and PPT deliverables never drift out of sync with each other.

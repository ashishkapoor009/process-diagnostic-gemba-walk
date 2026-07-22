# Installation Guide

## Prerequisites

- Python 3.11 or 3.12
- Tesseract OCR engine (system package, not just the `pytesseract` Python wrapper)
- Graphviz (system package) for diagram rendering
- An OpenAI API key, or an Azure OpenAI resource with a chat + embedding deployment

### Installing Tesseract & Graphviz

| OS | Tesseract | Graphviz |
|----|-----------|----------|
| Windows | [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki), then set `TESSERACT_CMD` in `.env` to the install path | `choco install graphviz` or [graphviz.org download](https://graphviz.org/download/) |
| macOS | `brew install tesseract` | `brew install graphviz` |
| Ubuntu/Debian | `sudo apt install tesseract-ocr` | `sudo apt install graphviz` |

## Local Setup

```bash
cd process-excellence-agent

# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY (or the AZURE_OPENAI_* variables)

# 4. Run the Streamlit app
streamlit run streamlit_app.py
```
The app opens at `http://localhost:8501`.

## Running the Optional FastAPI Backend

```bash
uvicorn app.main:api --host 0.0.0.0 --port 8000 --reload
```
API docs at `http://localhost:8000/docs`.

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```
Tests that require a live LLM call (the agents themselves, end-to-end
orchestration) are not part of the default offline suite - the suite covers
schemas, savings math, Mermaid rendering, database persistence/rehydration,
report generation, and the non-LLM step extractor path, all of which run
without any API key.

## Docker Setup

```bash
docker compose up --build
```
This starts both the Streamlit UI (port 8501) and the FastAPI backend (port
8000), sharing the same `data/` volume (SQLite DB + ChromaDB persistence).

## First Run: Knowledge Base Ingestion

On first use of any RAG-dependent feature (running a diagnostic, or the
Knowledge Base search page), the app automatically chunks and embeds the
Markdown knowledge base in `app/rag/knowledge_base/` into a local ChromaDB
collection under `data/chroma/`. This requires a working embeddings API call,
so `OPENAI_API_KEY` (or Azure equivalent) must be set before first use.
Subsequent runs reuse the persisted collection instantly.

## Troubleshooting

- **"No LLM credentials configured"** - set `OPENAI_API_KEY` in `.env` and restart the app (Streamlit doesn't hot-reload `.env` changes).
- **OCR returns empty text** - confirm Tesseract is installed and on PATH, or set `TESSERACT_CMD` explicitly in `.env`.
- **Mermaid diagrams don't render** - they load `mermaid.js` from a CDN inside an embedded HTML component; ensure the machine running the browser has internet access.
- **`unstructured` fallback errors on an unusual file** - this only triggers for formats not natively handled (e.g. legacy `.doc`, `.vsdx`); prefer PDF/DOCX/PPTX/PNG/JPG/CSV/XLSX/BPMN-XML exports where possible.

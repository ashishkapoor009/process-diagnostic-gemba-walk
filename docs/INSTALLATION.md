# Installation Guide

## Prerequisites

- Python 3.11 or 3.12
- Tesseract OCR engine (system package, not just the `pytesseract` Python wrapper)
- An OpenAI API key, or an Azure OpenAI resource with a chat + embedding deployment
- Node.js 18+ (only if you're also running the `process-diagnostic-frontend` Next.js app locally)

### Installing Tesseract

| OS | Command |
|----|---------|
| Windows | [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki), then set `TESSERACT_CMD` in `.env` to the install path |
| macOS | `brew install tesseract` |
| Ubuntu/Debian | `sudo apt install tesseract-ocr` |

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

# 4. Run the FastAPI backend
uvicorn app.main:api --host 0.0.0.0 --port 8000 --reload
```
API docs at `http://localhost:8000/docs`.

## Running the Frontend

The UI lives in the sibling `process-diagnostic-frontend` repo (Next.js):

```bash
cd ../process-diagnostic-frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```
The app opens at `http://localhost:3000` (or the port you choose) and talks
to the backend started above.

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
This starts the FastAPI backend on port 8000, persisting the SQLite DB and
ChromaDB collection under the `data/` volume. Run the frontend separately
(locally via `npm run dev`, or deployed to Vercel) pointed at this backend.

## First Run: Knowledge Base Ingestion

On first use of any RAG-dependent feature (running a diagnostic, or the
`/api/knowledge-base` search endpoint), the app automatically chunks and
embeds the Markdown knowledge base in `app/rag/knowledge_base/` into a
local ChromaDB collection under `data/chroma/`. This requires a working
embeddings API call, so `OPENAI_API_KEY` (or Azure equivalent) must be set
before first use. Subsequent runs reuse the persisted collection instantly.

## Troubleshooting

- **"No LLM credentials configured"** - set `OPENAI_API_KEY` in `.env` and restart the backend process.
- **OCR returns empty text** - confirm Tesseract is installed and on PATH, or set `TESSERACT_CMD` explicitly in `.env`.
- **Mermaid diagrams don't render on the frontend** - the frontend renders them client-side via the `mermaid` npm package; check the browser console for errors and confirm the backend's `flow_mermaid_current`/`flow_mermaid_future` fields are non-empty.
- **`unstructured` fallback errors on an unusual file** - this only triggers for formats not natively handled (e.g. legacy `.doc`, `.vsdx`); prefer PDF/DOCX/PPTX/PNG/JPG/CSV/XLSX/BPMN-XML exports where possible.

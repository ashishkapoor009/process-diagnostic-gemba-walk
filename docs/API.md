# API Documentation (Optional FastAPI Backend)

Run the backend standalone:
```bash
uvicorn app.main:api --host 0.0.0.0 --port 8000 --reload
```
Interactive docs are auto-generated at `http://localhost:8000/docs` (Swagger UI)
and `http://localhost:8000/redoc`.

## Endpoints

### `GET /health`
Returns service health and whether LLM credentials are configured.
```json
{ "status": "ok", "llm_configured": true, "llm_provider": "openai" }
```

### `POST /api/extract/text`
Extract structured process steps from raw text using the LLM.
**Body:**
```json
{ "raw_text": "Step 1 ...\nStep 2 ...", "process_name": "Invoice Processing" }
```
**Response:** `ProcessStepInput[]`

### `POST /api/extract/upload`
Multipart file upload (`file`). Parses PDF/DOCX/PPTX/image/BPMN/CSV/Excel
(with OCR fallback for scanned content) and extracts steps via LLM.
**Response:**
```json
{ "filename": "process.pdf", "used_ocr": false, "steps": [ ... ] }
```

### `POST /api/processes`
Runs the full six-agent diagnostic pipeline and persists the result.
**Body:**
```json
{
  "metadata": { "process_name": "...", "department": "...", "business_function": "...",
                 "current_fte": 6, "current_volume": 3200, "aht_minutes": 22,
                 "country": "India", "lob": "Finance" },
  "steps": [ { "step_number": 1, "step_name": "Receive invoice" }, ... ],
  "project_id": null
}
```
**Response:**
```json
{
  "process_id": 1, "diagnostics_count": 12, "recommendations_count": 24,
  "executive_summary": "...", "savings_summary": { "blended_efficiency_improvement_pct": 27.4, ... }
}
```

### `GET /api/processes`
Lists all saved processes (id, name, department, FTE, volume, AHT, created_at).

### `GET /api/processes/{process_id}`
Returns the full rehydrated diagnostic: metadata, diagnostics, recommendations,
savings_summary, executive_summary, and both Mermaid flow diagrams.

### `GET /api/processes/{process_id}/report/{fmt}`
`fmt` is one of `pdf`, `word`, `excel`, `ppt`. Streams the generated report
file with the correct `Content-Type` and `Content-Disposition` for download.

## Using a Vercel-Hosted Frontend Against This API

Because Vercel cannot run this Python backend directly (see `DEPLOYMENT.md`),
host this FastAPI service on Render/Railway/Cloud Run, then point a Next.js
app deployed on Vercel at it, e.g.:

```ts
const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/processes`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ metadata, steps }),
});
```

Set `NEXT_PUBLIC_API_URL` as a Vercel environment variable pointing to your
deployed backend's public URL, and tighten `allow_origins` in
`app/main.py`'s CORS middleware to that Vercel domain before going to production.

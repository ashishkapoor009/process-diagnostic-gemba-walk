# Deployment Guide

## Why Not Vercel Directly

Vercel runs your code as short-lived serverless functions - there is no
persistent process, no WebSocket support, and no long-lived Python server.
Streamlit requires exactly that: a continuously running server process
holding a WebSocket connection open to the browser for the app's entire
session. There is no configuration that makes real Streamlit run on Vercel.
Any claim otherwise produces either a broken deployment or something that
isn't actually Streamlit. Below are the three supported deployment paths.

---

## Option A (Recommended): Streamlit Community Cloud

Free, purpose-built for exactly this app, deploys straight from GitHub.

1. Push this repository to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, select the repo, branch, and set the main file path to
   `process-excellence-agent/streamlit_app.py` (or `streamlit_app.py` if the
   repo root *is* this folder).
4. Under **Advanced settings -> Secrets**, paste the contents of your `.env`
   in TOML format:
   ```toml
   OPENAI_API_KEY = "sk-..."
   LLM_PROVIDER = "openai"
   OPENAI_CHAT_MODEL = "gpt-4o"
   OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
   RAGAS_MIN_SCORE = 0.70
   ```
   (Streamlit Cloud injects secrets as environment variables automatically -
   `pydantic-settings` picks them up the same way it reads `.env` locally.)
5. Add a `packages.txt` file (already included) listing `tesseract-ocr` and
   `graphviz` so Streamlit Cloud installs the system packages OCR/diagram
   rendering need.
6. Click **Deploy**. You get a public URL like
   `https://your-app-name.streamlit.app`.

---

## Option B: Render or Railway (Full Docker Deployment)

Use this when you also want the optional FastAPI backend running as a
separate persistent service (e.g. to support an external frontend).

### Render
1. Push the repo to GitHub.
2. In Render, **New -> Web Service**, connect the repo, set:
   - **Runtime:** Docker (uses the included `Dockerfile`)
   - **Start Command:** leave default (`CMD` in the Dockerfile runs Streamlit)
     or override to `uvicorn app.main:api --host 0.0.0.0 --port $PORT` for
     the API service.
3. Add the same environment variables as in `.env.example` under
   **Environment**.
4. Add a **Persistent Disk** mounted at `/app/data` so the SQLite DB and
   ChromaDB collection survive restarts.
5. Deploy. Render assigns a public HTTPS URL.
6. Repeat as a second service (API) if you need both UI and backend
   running independently.

### Railway
1. `railway init` in the project directory, or connect the GitHub repo via
   the Railway dashboard.
2. Railway auto-detects the `Dockerfile`. Set the same environment
   variables as above in **Variables**.
3. Attach a **Volume** mounted at `/app/data` for persistence.
4. Deploy - Railway assigns a public URL, or attach a custom domain.

---

## Option C: Google Cloud Run

For teams already on GCP, or wanting autoscaling-to-zero cost control.

```bash
# 1. Build and push the image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pe-gemba-agent

# 2. Deploy the Streamlit UI
gcloud run deploy pe-gemba-ui \
  --image gcr.io/YOUR_PROJECT_ID/pe-gemba-agent \
  --command streamlit \
  --args "run,streamlit_app.py,--server.port=8080,--server.address=0.0.0.0" \
  --port 8080 \
  --set-env-vars OPENAI_API_KEY=sk-...,LLM_PROVIDER=openai \
  --allow-unauthenticated

# 3. (Optional) Deploy the FastAPI backend as a second service
gcloud run deploy pe-gemba-api \
  --image gcr.io/YOUR_PROJECT_ID/pe-gemba-agent \
  --command uvicorn \
  --args "app.main:api,--host,0.0.0.0,--port,8080" \
  --port 8080 \
  --set-env-vars OPENAI_API_KEY=sk-...,LLM_PROVIDER=openai \
  --allow-unauthenticated
```
For persistence beyond a single container's lifetime, mount a Cloud Run
volume backed by Cloud Storage FUSE, or migrate `SQLITE_DB_PATH` /
`CHROMA_PERSIST_DIR` to a managed Postgres + a hosted vector DB (e.g.
Cloud SQL + a managed Chroma/Pinecone) for production-grade durability.

---

## Option D: One Public URL Under Vercel (Hybrid)

If a single `*.vercel.app` URL is a hard requirement, deploy the Python
backend on any of A/B/C above, then deploy a thin Next.js frontend on
Vercel that calls it over REST (`app/main.py`'s FastAPI endpoints - see
`docs/API.md`). This gives you a Vercel URL for the *frontend*, while the
actual multi-agent processing still runs on a real persistent server
elsewhere. Steps:

1. Deploy the FastAPI backend per Option B or C; note its public URL.
2. Scaffold a Next.js app, set `NEXT_PUBLIC_API_URL` to that backend URL as
   a Vercel environment variable.
3. Build pages that call `POST {API_URL}/api/processes`,
   `GET {API_URL}/api/processes/{id}`, and the report-download endpoints.
4. `vercel deploy` the Next.js app for your single public Vercel URL.
5. In `app/main.py`, tighten `CORSMiddleware(allow_origins=[...])` to your
   Vercel domain before going to production.

This hybrid keeps the Streamlit UI as the primary/reference experience
(Options A-C) while giving you the Vercel URL as an additional thin client.

---

## Production Checklist

- [ ] Set `APP_ENV=production` and a real `RAGAS_MIN_SCORE` for your risk tolerance
- [ ] Move SQLite to a managed Postgres if you need concurrent multi-user writes at scale
- [ ] Restrict FastAPI CORS `allow_origins` to your actual frontend domain(s)
- [ ] Put the OpenAI/Azure API key in the platform's secret manager, never in source control
- [ ] Mount a persistent volume for `data/` (SQLite DB + ChromaDB) on any container platform
- [ ] Set up log shipping from `logs/app.log` (or stdout, which the Dockerfile also emits to) to your observability stack

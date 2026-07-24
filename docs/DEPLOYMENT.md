# Deployment Guide

## Why Not Vercel for the Backend

Vercel runs your code as short-lived serverless functions - there is no
persistent process and function timeouts are far shorter than the 3-8
minutes the six-agent diagnostic pipeline needs. The FastAPI backend must
run on a platform with a long-running server process. The Next.js
frontend, by contrast, is exactly what Vercel is built for.

This is a two-repo deployment:
- **Backend** (this repo, `process-excellence-agent`) - deploy to Render,
  Railway, Fly.io, or Cloud Run (Options A-C below).
- **Frontend** (`process-diagnostic-frontend`) - deploy to Vercel, pointed
  at the backend's public URL via `NEXT_PUBLIC_API_URL`.

---

## Option A (Recommended): Render or Railway (Docker)

### Render
1. Push the repo to GitHub.
2. In Render, **New -> Web Service**, connect the repo, set:
   - **Runtime:** Docker (uses the included `Dockerfile`)
   - **Start Command:** leave default (`CMD` in the Dockerfile runs
     `uvicorn app.main:api --host 0.0.0.0 --port 8000`), or override to
     `uvicorn app.main:api --host 0.0.0.0 --port $PORT` if Render assigns
     `$PORT` dynamically.
3. Add the same environment variables as in `.env.example` under
   **Environment**.
4. Add a **Persistent Disk** mounted at `/app/data` so the SQLite DB and
   ChromaDB collection survive restarts.
5. Deploy. Render assigns a public HTTPS URL - this is your
   `NEXT_PUBLIC_API_URL` for the frontend.

### Railway
1. `railway init` in the project directory, or connect the GitHub repo via
   the Railway dashboard.
2. Railway auto-detects the `Dockerfile`. Set the same environment
   variables as above in **Variables**.
3. Attach a **Volume** mounted at `/app/data` for persistence.
4. Deploy - Railway assigns a public URL, or attach a custom domain.

---

## Option B: Google Cloud Run

For teams already on GCP, or wanting autoscaling-to-zero cost control.

```bash
# 1. Build and push the image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pe-gemba-agent

# 2. Deploy the FastAPI backend
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

## Frontend: Vercel

1. In `process-diagnostic-frontend`, run `vercel link` then `vercel --prod`
   (or connect the GitHub repo in the Vercel dashboard for automatic
   deploys on push).
2. Set `NEXT_PUBLIC_API_URL` as a Vercel environment variable to the public
   backend URL from Option A or B above.
3. In `app/main.py` on the backend, tighten
   `CORSMiddleware(allow_origins=[...])` to your Vercel domain before going
   to production.

---

## Production Checklist

- [ ] Set `APP_ENV=production` and a real `RAGAS_MIN_SCORE` for your risk tolerance
- [ ] Move SQLite to a managed Postgres if you need concurrent multi-user writes at scale
- [ ] Restrict FastAPI CORS `allow_origins` to your actual frontend domain(s)
- [ ] Put the OpenAI/Azure API key in the platform's secret manager, never in source control
- [ ] Mount a persistent volume for `data/` (SQLite DB + ChromaDB) on any container platform
- [ ] Set up log shipping from `logs/app.log` (or stdout, which the Dockerfile also emits to) to your observability stack

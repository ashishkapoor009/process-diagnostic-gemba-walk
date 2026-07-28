FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps: tesseract for OCR, poppler for pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    poppler-utils \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/chroma data/uploads logs

EXPOSE 8000

# Cloud Run (and some other PaaS hosts) inject $PORT and require the
# container to listen on it rather than a fixed port - shell form so the
# env var expands. Defaults to 8000 (unchanged local/Render behavior) when
# PORT isn't set.
CMD ["sh", "-c", "uvicorn app.main:api --host 0.0.0.0 --port ${PORT:-8000}"]

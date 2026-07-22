FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps: tesseract for OCR, graphviz for diagram rendering, poppler for pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    graphviz \
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

EXPOSE 8501 8000

# Default: run the Streamlit UI. Override CMD to run the FastAPI backend instead:
#   docker run ... uvicorn app.main:api --host 0.0.0.0 --port 8000
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

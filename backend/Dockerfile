# Conformance gateway and dashboard API.
# Build context is the repository root:  docker build -f backend/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY backend/requirements.txt backend/requirements-ner.txt ./
RUN pip install -r requirements.txt

# Named entity detection (Presidio with a small spaCy model). Adds about 400 MB.
# Build with --build-arg INSTALL_NER=false for a smaller image without it.
ARG INSTALL_NER=true
ARG NER_MODEL_URL=https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
RUN if [ "$INSTALL_NER" = "true" ]; then pip install -r requirements-ner.txt "$NER_MODEL_URL"; fi

COPY backend/app ./app
COPY demo ./demo

RUN useradd --system --uid 10001 --create-home conformance \
    && mkdir -p /data \
    && chown conformance:conformance /data
USER conformance

ENV DATA_DIR=/data
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).status == 200 else 1)"

# One worker: the recorder, the ledger writer and the connector scheduler run in this process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

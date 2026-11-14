# Simulator: mock model provider and mock Microsoft and GitHub APIs for local testing.
# Build context is the repository root.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
COPY simulator/requirements.txt ./
RUN pip install -r requirements.txt
COPY simulator ./simulator
COPY demo ./demo
COPY sdk ./sdk
RUN useradd --system --uid 10001 simulator
USER simulator
EXPOSE 9000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9000/healthz', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "simulator.app:app", "--host", "0.0.0.0", "--port", "9000"]

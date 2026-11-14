# Sample internal tool. Build context is the repository root.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONPATH=/srv
WORKDIR /srv
COPY demo-app/requirements.txt ./
RUN pip install -r requirements.txt
COPY demo ./demo
COPY demo-app ./demo-app
RUN useradd --system --uid 10001 tool
USER tool
WORKDIR /srv/demo-app
EXPOSE 8090
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8090/healthz', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]

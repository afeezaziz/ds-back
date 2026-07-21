FROM python:3.12-slim

# Non-root runtime user (Coolify/production best practice)
RUN useradd -m -u 10001 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Container-level healthcheck (Coolify also polls /v1/health).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/v1/health').status==200 else 1)"

# Production server. Bump --workers for more concurrency (needs Postgres, not SQLite).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

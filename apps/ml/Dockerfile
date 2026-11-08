FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY packages/assessment-contract /tmp/assessment-contract
COPY apps/ml/pyproject.toml ./
COPY apps/ml/ml_service ./ml_service
RUN pip install /tmp/assessment-contract . \
    && rm -rf /tmp/assessment-contract \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app
USER app
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)"]
CMD ["uvicorn", "ml_service.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--no-access-log"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY packages/assessment-contract /tmp/assessment-contract
COPY apps/backend/pyproject.toml ./
COPY apps/backend/app ./app
COPY apps/backend/alembic.ini ./
COPY apps/backend/alembic ./alembic
COPY apps/backend/healthcheck.py ./healthcheck.py

RUN pip install /tmp/assessment-contract . \
    && rm -rf /tmp/assessment-contract

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

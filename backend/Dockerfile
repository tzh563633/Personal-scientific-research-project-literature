FROM postgres:16 AS postgres-client

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice \
        curl \
        git \
        gcc \
        libpq-dev \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY --from=postgres-client /usr/lib/postgresql/16/bin/pg_dump /usr/local/bin/pg_dump16
COPY --from=postgres-client /usr/lib/postgresql/16/bin/pg_restore /usr/local/bin/pg_restore16
COPY app /app/app
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

RUN mkdir -p /app/storage

EXPOSE 8000

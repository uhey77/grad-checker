# syntax=docker/dockerfile:1
FROM golang:1.25-bookworm AS go-build
WORKDIR /src
COPY backend/go.mod ./
COPY backend/apps/api ./apps/api
COPY backend/modules ./modules
COPY backend/shared ./shared
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /api ./apps/api

FROM ghcr.io/astral-sh/uv:0.13.1 AS uv
FROM python:3.15.2-slim-bookworm AS python-build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/apps ./apps
COPY backend/modules ./modules
COPY backend/shared ./shared
COPY backend/migrations ./migrations
COPY backend/scripts ./scripts
# ローカルの管理環境でのみCAをmountする。通常のCIでは標準CAを使用する。
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    uv sync --locked --no-dev --no-editable --no-cache --python /usr/local/bin/python

FROM python:3.15.2-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY --from=python-build --chown=app:app /app/.venv /app/.venv
COPY --from=go-build --chown=app:app /api /app/bin/api
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=4s --start-period=30s CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/api/ready',timeout=3)"]
CMD ["python", "-m", "apps.runtime"]

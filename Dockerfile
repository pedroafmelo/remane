# Imagem única do Escalista (plano da C0, B2): build do React num estágio Node e execução em Python.

# ---- Estágio 1: build da SPA ----
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci
COPY web/ ./
RUN npm run build

# ---- Estágio 2: backend e SPA ----
FROM python:3.12-slim-bookworm AS app
COPY --from=ghcr.io/astral-sh/uv:0.9.17 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
WORKDIR /app

# Dependências primeiro (cache de camada); o projeto em seguida.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ src/
COPY data/ data/
RUN uv sync --frozen --no-dev

COPY --from=web /web/dist web/dist

ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA} \
    PATH="/app/.venv/bin:$PATH" \
    WEB_DIST_DIR=/app/web/dist \
    DATABASE_URL=sqlite:////data/escalista.db

# Usuário sem root; o entrypoint acerta o dono do volume montado em /data e então abandona o root.
RUN useradd --system --uid 10001 --home-dir /app app && mkdir -p /data && chown -R app:app /data
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "escalista.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]

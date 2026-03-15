# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline 2>/dev/null || npm install
COPY frontend/ ./
# vite.config.js sets outDir: '../dashboard' → output lands at /dashboard
RUN npm run build

# ── Stage 2: Python dependency layer ───────────────────────────────────────
FROM python:3.12-slim AS base
RUN pip install uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY pyproject.toml ./
RUN uv sync --no-cache

# ── Stage 3: Final runtime image ───────────────────────────────────────────
FROM python:3.12-slim AS runner
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
COPY --from=base /app/.venv /app/.venv
COPY --from=frontend-builder /dashboard ./dashboard
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

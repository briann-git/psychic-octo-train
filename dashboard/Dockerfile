# ── Stage 1: build React frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python backend + bundled frontend ────────────────────────────────
FROM python:3.11-slim
WORKDIR /app
COPY backend/ .
COPY --from=frontend /app/dist ./static
RUN pip install --no-cache-dir fastapi uvicorn docker aiofiles
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

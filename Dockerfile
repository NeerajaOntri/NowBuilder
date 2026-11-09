# nowBuilder as one service (used by Render, see render.yaml): the React app is built first, then
# served by the FastAPI backend from /app/static, so the app and /api share one address.

# ---- 1. build the frontend ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. backend + built frontend ----
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NOWBUILDER_ENVIRONMENT=production
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
EXPOSE 10000
# Render sets PORT; --proxy-headers so the app sees https behind Render's proxy
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]

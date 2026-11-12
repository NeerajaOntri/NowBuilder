
# nowBuilder: Build frontend, then run FastAPI with BOTH Python and Node.js.

# ---- 1. Build frontend ----
FROM node:22-bookworm-slim AS web

WORKDIR /web

COPY frontend/package.json frontend/package-lock.json ./

RUN npm ci --no-audit --no-fund

COPY frontend/ ./

RUN npm run build


# ---- 2. Backend runtime: Python + Node.js ----
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NOWBUILDER_ENVIRONMENT=production

# Install Node.js 22 in the FINAL runtime image.
# Required for executing the ServiceNow SDK from the backend.

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -d -m 0755 /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && chmod a+r /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && node --version \
    && npm --version \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*


# ---- 3. Install Python dependencies ----

COPY backend/requirements.txt .

RUN pip install -r requirements.txt


# ---- 4. Copy backend application ----

COPY backend/ ./


# ---- 5. Copy built frontend ----

COPY --from=web /web/dist ./static


# ---- 6. Start FastAPI ----

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]

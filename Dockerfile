# ===============================================================
# DataEngineX — Multi-stage Docker Build
# Stage 1 (builder): Installs dependencies via uv into a venv.
# Stage 2 (runtime): Copies only the venv + source code and runs
#                    the FastAPI application as a non-root user.
# ===============================================================

# --- Stage 1: Build dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install curl for uv installer
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy dependency manifest and source tree
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/
COPY packages/dataenginex/ packages/dataenginex/

# Build a frozen venv with production dependencies only (no dev)
ENV UV_PROJECT_ENVIRONMENT=/build/.venv \
    UV_PYTHON=/usr/local/bin/python \
    UV_PYTHON_PREFERENCE=system
RUN /root/.local/bin/uv sync --frozen --no-dev

# --- Stage 2: Minimal runtime image ---
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 dex \
    && useradd --uid 1000 --gid dex --shell /bin/bash dex

# Copy virtual environment from builder stage
COPY --from=builder /build/.venv /app/.venv

# Copy dataenginex core package
COPY --from=builder /build/packages /app/packages

# Copy application source code
COPY src/ /app/src/

# Configure runtime paths
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app/packages/dataenginex/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as non-root
USER dex

# Expose FastAPI default port
EXPOSE 8000

# Start the FastAPI application via Uvicorn
CMD ["python", "-m", "uvicorn", "careerdex.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ===============================================================
# DEX — Multi-stage Docker Build
# Stage 1 (builder): Installs dependencies via uv into a venv.
# Stage 2 (runtime): Copies only the venv + source code and runs
#                    the FastAPI application as a non-root user.
# ===============================================================

# --- Stage 1: Build dependencies ---
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Copy dependency manifest and source tree
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

# Build a frozen venv with production dependencies only (no dev)
ENV UV_PROJECT_ENVIRONMENT=/build/.venv \
    UV_PYTHON=/usr/local/bin/python \
    UV_PYTHON_PREFERENCE=system
RUN uv sync --frozen --no-dev

# --- Stage 2: Minimal runtime image ---
FROM python:3.13-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 dex \
    && useradd --uid 1000 --gid dex --shell /bin/bash dex

# Copy virtual environment from builder stage
COPY --from=builder /build/.venv /app/.venv

# Copy application source code and examples
COPY src/ /app/src/
COPY examples/ /app/examples/

# Configure runtime paths
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as non-root
USER dex

# Expose FastAPI default port
EXPOSE 17000

# Start the DEX API server (override CMD for custom entry point)
CMD ["dex", "serve", "--host", "0.0.0.0", "--port", "17000"]

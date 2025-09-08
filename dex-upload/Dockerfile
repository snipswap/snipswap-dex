# 🚀 SnipSwap DEX - Sovereignty Stack Backend
# Multi-stage build for optimized production image

# ===== BUILD STAGE =====
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=3.0.0-sovereignty
ARG VCS_REF

# Labels for metadata
LABEL maintainer="SnipSwap Team <team@snipswap.com>" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="SnipSwap DEX" \
      org.label-schema.description="Privacy-first decentralized exchange with AI integration" \
      org.label-schema.url="https://snipswap.com" \
      org.label-schema.vcs-url="https://github.com/snipswap/snipswap-dex" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vendor="SnipSwap" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ===== PRODUCTION STAGE =====
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r snipswap && useradd -r -g snipswap snipswap

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=snipswap:snipswap . .

# Create necessary directories
RUN mkdir -p /app/src/database /app/static /app/logs && \
    chown -R snipswap:snipswap /app

# Switch to non-root user
USER snipswap

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=src/main.py \
    PORT=5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/api/health || exit 1

# Expose ports
EXPOSE 5001 9090

# Default command
CMD ["python", "src/main.py"]

# ===== DEVELOPMENT STAGE =====
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy \
    ipython \
    jupyter

# Switch back to snipswap user
USER snipswap

# Override for development
ENV FLASK_ENV=development
CMD ["python", "src/main.py"]


# =============================================================================
# Narrative AI SDK Developer Portal - Lightweight Dockerfile
# =============================================================================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application artifacts
COPY narrative_ai/ ./narrative_ai/
COPY config/ ./config/
COPY docker/entrypoint.sh /app/entrypoint.sh

# Environment Setup
RUN chmod +x /app/entrypoint.sh && \
    # Create non-root user for security
    groupadd -r narrative && \
    useradd -r -g narrative -d /app -s /sbin/nologin narrative && \
    chown -R narrative:narrative /app

USER narrative

# Expose ports
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default start command
CMD ["python", "-m", "narrative_ai.api.app", "--host", "0.0.0.0", "--port", "8000"]

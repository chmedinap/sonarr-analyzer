# Sonarr Analyzer v0.3
# Multi-stage build for optimized image size

FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY app.py .
COPY auth.py .
COPY security.py .
COPY storage.py .

# Copy Streamlit configuration
# Security note: CORS and XSRF protections are disabled because this app runs
# in a controlled Docker environment where users access it directly (not via external APIs).
# This configuration prevents compatibility warnings while maintaining security.
COPY .streamlit /home/appuser/.streamlit
RUN chown -R appuser:appuser /home/appuser/.streamlit

# Create data directory for persistent storage
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_FILE_WATCHER_TYPE=none

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Volume for persistent data
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]



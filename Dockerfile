# Use Ubuntu as base image for ADB support
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV WEBHOOK_HOST=0.0.0.0
ENV WEBHOOK_PORT=5680

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    android-tools-adb \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy Python application files and assets
COPY btt_launcher.py .
COPY getsql.py .
COPY btt_auto.py .
COPY web_ui.html .
COPY network-server.png .

# Copy Docker entry point
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/db /app/logs

# Create non-root user
RUN useradd -m -u 1000 bttuser && \
    chown -R bttuser:bttuser /app

# Switch to non-root user
USER bttuser

# Expose port
EXPOSE 5680

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5680/healthz || exit 1

# Set entry point
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"] 
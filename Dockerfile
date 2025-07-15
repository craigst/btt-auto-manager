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
    python3-venv \
    wget \
    unzip \
    curl \
    adb \
    android-tools-adb \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY btt_launcher.py .
COPY getsql.py .
COPY btt_auto.py .
COPY AUTOREADME.md .

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/db /app/logs

# Create a non-root user for security
RUN useradd -m -u 1000 bttuser && \
    chown -R bttuser:bttuser /app

# Switch to non-root user
USER bttuser

# Expose webhook port
EXPOSE 5680

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5680/healthz || exit 1

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"] 
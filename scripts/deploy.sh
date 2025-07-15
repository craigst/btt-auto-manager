#!/bin/bash

# BTT Auto Manager Production Deployment Script

set -e

echo "🚀 BTT Auto Manager Production Deployment"
echo "=========================================="

# Configuration
CONTAINER_NAME="btt-auto-manager"
IMAGE_NAME="btt-auto-manager"
WEBHOOK_PORT=${WEBHOOK_PORT:-5680}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (required for ADB access)
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root for ADB access"
    print_warning "Run with: sudo $0"
    exit 1
fi

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

print_status "Prerequisites check passed"

# Create production directories
print_status "Creating production directories..."
mkdir -p /opt/btt-auto-manager/{db,logs,config}
cd /opt/btt-auto-manager

# Create production configuration
if [ ! -f config/btt_config.json ]; then
    print_status "Creating production configuration..."
    cat > config/btt_config.json << EOF
{
  "auto_enabled": false,
  "interval_minutes": 20,
  "last_sql_atime": null,
  "last_locations": 0,
  "last_cars": 0,
  "last_loads": 0,
  "webhook_enabled": true,
  "webhook_port": ${WEBHOOK_PORT},
  "adb_ips": []
}
EOF
fi

# Set proper permissions
chmod 644 config/btt_config.json
chmod 755 db logs

# Create production docker-compose file
print_status "Creating production docker-compose configuration..."
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  btt-auto-manager:
    build: .
    container_name: ${CONTAINER_NAME}
    ports:
      - "${WEBHOOK_PORT}:5680"
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
      - ./config/btt_config.json:/app/btt_config.json
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - WEBHOOK_HOST=0.0.0.0
      - WEBHOOK_PORT=5680
      - PYTHONUNBUFFERED=1
      - PRODUCTION=true
    devices:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true
    restart: unless-stopped
    user: root
    networks:
      - btt-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  btt-network:
    driver: bridge
EOF

# Build and deploy
print_status "Building Docker image..."
docker-compose -f docker-compose.prod.yml build

print_status "Starting BTT Auto Manager..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for service to start
print_status "Waiting for service to start..."
sleep 10

# Check if service is running
if docker ps | grep -q ${CONTAINER_NAME}; then
    print_status "Service is running successfully"
else
    print_error "Service failed to start"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

# Test webhook endpoint
print_status "Testing webhook endpoint..."
if curl -f http://localhost:${WEBHOOK_PORT}/healthz > /dev/null 2>&1; then
    print_status "Webhook endpoint is responding"
else
    print_warning "Webhook endpoint not responding yet, may need more time to start"
fi

# Create systemd service (optional)
if command -v systemctl &> /dev/null; then
    print_status "Creating systemd service..."
    cat > /etc/systemd/system/btt-auto-manager.service << EOF
[Unit]
Description=BTT Auto Manager
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/btt-auto-manager
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable btt-auto-manager.service
    print_status "Systemd service created and enabled"
fi

# Display status
print_status "Deployment completed successfully!"
echo ""
echo "Service Information:"
echo "  Container: ${CONTAINER_NAME}"
echo "  Webhook URL: http://localhost:${WEBHOOK_PORT}"
echo "  Health Check: http://localhost:${WEBHOOK_PORT}/healthz"
echo "  Logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop: docker-compose -f docker-compose.prod.yml down"
echo ""
echo "Next steps:"
echo "1. Connect your Android device via USB"
echo "2. Enable USB debugging on your device"
echo "3. Test the webhook API"
echo "4. Configure auto-update settings via webhook" 
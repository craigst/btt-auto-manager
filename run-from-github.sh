#!/bin/bash

# BTT Auto Manager - Run from GitHub Container Registry
# This script sets up and runs BTT Auto Manager using the GitHub-hosted Docker image

set -e

echo "🚀 BTT Auto Manager - GitHub Container Registry Deployment"
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

print_status "Docker and Docker Compose are installed"

# Create necessary directories
print_status "Creating directories..."
mkdir -p db logs

# Set up environment variables
if [ -f setup-env.sh ]; then
    print_status "Setting up environment variables..."
    chmod +x setup-env.sh
    ./setup-env.sh
else
    print_warning "setup-env.sh not found, using default configuration"
    # Create basic .env file if env.example exists
    if [ -f env.example ] && [ ! -f .env ]; then
        print_status "Creating .env file from env.example..."
        cp env.example .env
        chmod 600 .env
    fi
fi

# Create default configuration if it doesn't exist
if [ ! -f btt_config.json ]; then
    print_status "Creating default configuration..."
    cat > btt_config.json << EOF
{
  "auto_enabled": false,
  "interval_minutes": 20,
  "last_sql_atime": null,
  "last_locations": 0,
  "last_cars": 0,
  "last_loads": 0,
  "webhook_enabled": true,
  "webhook_port": 5680,
  "adb_ips": []
}
EOF
    print_status "Configuration file created"
else
    print_status "Configuration file already exists"
fi

# Set proper permissions
chmod 644 btt_config.json
chmod 755 db logs

# Pull the latest image from GitHub Container Registry
print_status "Pulling latest image from GitHub Container Registry..."
docker pull ghcr.io/craigst/btt-auto-manager:main

# Start the service
print_status "Starting BTT Auto Manager..."
docker-compose up -d

# Wait for service to start
print_status "Waiting for service to start..."
sleep 10

# Check if service is running
if docker ps | grep -q btt-auto-manager; then
    print_status "Service is running successfully"
else
    print_error "Service failed to start"
    docker-compose logs
    exit 1
fi

# Test webhook endpoint
print_status "Testing webhook endpoint..."
if curl -f http://localhost:5680/healthz > /dev/null 2>&1; then
    print_status "Webhook endpoint is responding"
else
    print_warning "Webhook endpoint not responding yet, may need more time to start"
fi

echo ""
print_status "Deployment completed successfully!"
echo ""
echo "Service Information:"
echo "  Container: btt-auto-manager"
echo "  Webhook URL: http://localhost:5680"
echo "  Health Check: http://localhost:5680/healthz"
echo "  Status: http://localhost:5680/status"
echo ""
echo "Environment Configuration:"
if [ -f .env ]; then
    echo "  Environment file: .env (configured)"
    echo "  To modify settings: nano .env && docker-compose restart"
else
    echo "  Environment file: .env (not found, using defaults)"
fi
echo ""
echo "Management Commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop service: docker-compose down"
echo "  Restart service: docker-compose restart"
echo "  Update image: docker-compose pull && docker-compose up -d"
echo ""
echo "Next steps:"
echo "1. Connect your Android device via USB"
echo "2. Enable USB debugging on your device"
echo "3. Test the webhook API"
echo "4. Configure auto-update settings via webhook" 
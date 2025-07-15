#!/bin/bash

# BTT Auto Manager - Local Docker Build Script
# This script builds the Docker image locally as a temporary solution

set -e

echo "🔨 BTT Auto Manager - Local Docker Build"
echo "========================================"

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

print_status "Docker is installed"

# Build the Docker image locally
print_status "Building Docker image locally..."
docker build -t btt-auto-manager:local .

# Test the image
print_status "Testing the built image..."
docker run -d --name test-btt-local -p 5680:5680 btt-auto-manager:local

# Wait for startup
print_status "Waiting for service to start..."
sleep 30

# Test health endpoint
if curl -f http://localhost:5680/healthz > /dev/null 2>&1; then
    print_status "Image test successful!"
else
    print_warning "Health check failed, but image was built"
fi

# Cleanup test container
docker stop test-btt-local 2>/dev/null || true
docker rm test-btt-local 2>/dev/null || true

print_status "Local build completed successfully!"
echo ""
echo "You can now use the local image:"
echo "  docker run -d --name btt-auto-manager --restart unless-stopped -p 5680:5680 \\"
echo "    -v \$(pwd)/db:/app/db -v \$(pwd)/logs:/app/logs \\"
echo "    -v \$(pwd)/btt_config.json:/app/btt_config.json \\"
echo "    -v /dev/bus/usb:/dev/bus/usb --privileged \\"
echo "    btt-auto-manager:local"
echo ""
echo "Or update docker-compose.yml to use:"
echo "  image: btt-auto-manager:local"
echo ""
echo "To push to GitHub Container Registry later:"
echo "  1. Go to: https://github.com/craigst/btt-auto-manager/actions"
echo "  2. Run the 'Manual Docker Build and Publish' workflow"
echo "  3. Then use: ghcr.io/craigst/btt-auto-manager:main" 
#!/bin/bash

# BTT Auto Manager Environment Setup Script

set -e

echo "🔧 BTT Auto Manager Environment Setup"
echo "====================================="

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

# Check if .env file already exists
if [ -f .env ]; then
    print_warning ".env file already exists"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Keeping existing .env file"
        exit 0
    fi
fi

# Check if env.example exists
if [ ! -f env.example ]; then
    print_error "env.example file not found"
    exit 1
fi

# Copy env.example to .env
print_status "Creating .env file from env.example..."
cp env.example .env

# Set proper permissions
chmod 600 .env

print_status ".env file created successfully!"

# Ask user if they want to customize the configuration
echo ""
read -p "Do you want to customize the configuration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    print_status "Customizing configuration..."
    
    # Webhook Port
    read -p "Webhook port (default: 5680): " webhook_port
    if [ ! -z "$webhook_port" ]; then
        sed -i "s/WEBHOOK_PORT=5680/WEBHOOK_PORT=$webhook_port/" .env
    fi
    
    # Auto Update
    read -p "Enable auto-update on startup? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i "s/AUTO_ENABLED=false/AUTO_ENABLED=true/" .env
    fi
    
    # Update Interval
    read -p "Update interval in minutes (default: 20): " interval
    if [ ! -z "$interval" ]; then
        sed -i "s/INTERVAL_MINUTES=20/INTERVAL_MINUTES=$interval/" .env
    fi
    
    # Environment
    read -p "Environment (production/development, default: production): " env
    if [ ! -z "$env" ]; then
        sed -i "s/ENVIRONMENT=production/ENVIRONMENT=$env/" .env
    fi
    
    # Debug Mode
    read -p "Enable debug mode? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i "s/DEBUG=false/DEBUG=true/" .env
        sed -i "s/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/" .env
    fi
    
    print_status "Configuration customized!"
fi

echo ""
print_status "Environment setup complete!"
echo ""
echo "Your .env file contains:"
echo "========================"
cat .env | grep -v "^#" | grep -v "^$"
echo ""
echo "To use these settings:"
echo "  docker-compose up -d"
echo ""
echo "To modify settings later:"
echo "  nano .env"
echo "  docker-compose down && docker-compose up -d" 
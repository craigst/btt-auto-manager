#!/bin/bash

# BTT Auto Manager Setup Script

set -e

echo "🚀 BTT Auto Manager Setup Script"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p db logs

# Create default configuration if it doesn't exist
if [ ! -f btt_config.json ]; then
    echo "⚙️ Creating default configuration..."
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
    echo "✅ Configuration file created"
else
    echo "✅ Configuration file already exists"
fi

# Set proper permissions
chmod 644 btt_config.json
chmod 755 db logs

echo ""
echo "🔧 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Connect your Android device via USB"
echo "2. Enable USB debugging on your device"
echo "3. Run: docker-compose up -d"
echo "4. Access webhook API at: http://localhost:5680"
echo "5. Check health: curl http://localhost:5680/healthz"
echo ""
echo "For more information, see README.md" 
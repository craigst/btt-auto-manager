#!/bin/bash

# BTT Auto Manager Docker Entrypoint Script

set -e

echo "🚀 Starting BTT Auto Manager..."

# Create necessary directories if they don't exist
mkdir -p /app/db /app/logs

# Set proper permissions
chown -R bttuser:bttuser /app

# Check if ADB is available
if ! command -v adb &> /dev/null; then
    echo "❌ ADB not found. Installing..."
    apt-get update && apt-get install -y android-tools-adb
fi

# Start ADB server
echo "📱 Starting ADB server..."
adb start-server

# Check if configuration file exists, create default if not
if [ ! -f /app/btt_config.json ]; then
    echo "⚙️ Creating default configuration..."
    cat > /app/btt_config.json << EOF
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
    chown bttuser:bttuser /app/btt_config.json
fi

# Set environment variables for the application
export WEBHOOK_HOST=${WEBHOOK_HOST:-0.0.0.0}
export WEBHOOK_PORT=${WEBHOOK_PORT:-5680}
export PYTHONUNBUFFERED=1

echo "✅ Environment setup complete"
echo "🌐 Webhook server will be available at http://${WEBHOOK_HOST}:${WEBHOOK_PORT}"
echo "📊 Health check: http://${WEBHOOK_HOST}:${WEBHOOK_PORT}/healthz"

# Execute the main application
exec python3 /app/btt_auto.py 
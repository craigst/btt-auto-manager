# 🚀 Quick Start: Deploy from GitHub Container Registry

This guide shows you how to quickly deploy BTT Auto Manager using the GitHub-hosted Docker image.

## 🐳 One-Command Deployment

### Option 1: Using the Setup Script
```bash
# Download and run the setup script
curl -sSL https://raw.githubusercontent.com/craigst/btt-auto-manager/main/run-from-github.sh | bash
```

### Option 2: Manual Docker Compose
```bash
# Clone the repository
git clone https://github.com/craigst/btt-auto-manager.git
cd btt-auto-manager

# Run the deployment script
./run-from-github.sh
```

## 📋 Docker Compose Configuration

The `docker-compose.yml` file is configured to use the GitHub Container Registry image:

```yaml
version: '3.8'

services:
  btt-auto-manager:
    image: ghcr.io/craigst/btt-auto-manager:main
    container_name: btt-auto-manager
    ports:
      - "5680:5680"  # Webhook API port
    volumes:
      - ./db:/app/db  # Database storage
      - ./logs:/app/logs  # Log files
      - ./btt_config.json:/app/btt_config.json  # Configuration
      - /dev/bus/usb:/dev/bus/usb  # USB device access (for ADB)
    environment:
      - WEBHOOK_HOST=0.0.0.0
      - WEBHOOK_PORT=5680
      - PYTHONUNBUFFERED=1
    devices:
      - /dev/bus/usb:/dev/bus/usb  # USB device access
    privileged: true  # Required for ADB access
    restart: unless-stopped
    networks:
      - btt-network
    user: root
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5680/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  btt-network:
    driver: bridge
```

## 🔧 Manual Setup Steps

If you prefer to set up manually:

### 1. Create Project Directory
```bash
mkdir btt-auto-manager
cd btt-auto-manager
```

### 2. Create Configuration
```bash
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
```

### 3. Create Directories
```bash
mkdir -p db logs
```

### 4. Create Docker Compose File
```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  btt-auto-manager:
    image: ghcr.io/craigst/btt-auto-manager:main
    container_name: btt-auto-manager
    ports:
      - "5680:5680"
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
      - ./btt_config.json:/app/btt_config.json
      - /dev/bus/usb:/dev/bus/usb
    environment:
      - WEBHOOK_HOST=0.0.0.0
      - WEBHOOK_PORT=5680
      - PYTHONUNBUFFERED=1
    devices:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true
    restart: unless-stopped
    networks:
      - btt-network
    user: root
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5680/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  btt-network:
    driver: bridge
EOF
```

### 5. Run the Service
```bash
# Pull the latest image
docker pull ghcr.io/craigst/btt-auto-manager:main

# Start the service
docker-compose up -d
```

## 🧪 Testing the Deployment

### Health Check
```bash
curl http://localhost:5680/healthz
```

### Status Check
```bash
curl http://localhost:5680/status
```

### Test Data Endpoints
```bash
# Get location data
curl http://localhost:5680/webhook/dwjjob

# Get vehicle data
curl http://localhost:5680/webhook/dwvveh

# Get ADB IPs
curl http://localhost:5680/webhook/adb-ips
```

### Control System
```bash
# Toggle auto-update
curl -X POST http://localhost:5680/webhook/control \
  -H "Content-Type: application/json" \
  -d '{"action": "toggle_auto"}'

# Run extraction now
curl -X POST http://localhost:5680/webhook/control \
  -H "Content-Type: application/json" \
  -d '{"action": "run_now"}'
```

## 🔄 Management Commands

### View Logs
```bash
docker-compose logs -f
```

### Stop Service
```bash
docker-compose down
```

### Restart Service
```bash
docker-compose restart
```

### Update to Latest Version
```bash
docker-compose pull
docker-compose up -d
```

### Check Status
```bash
docker-compose ps
```

## 🌐 Available Docker Images

- `ghcr.io/craigst/btt-auto-manager:main` - Latest main branch
- `ghcr.io/craigst/btt-auto-manager:latest` - Latest stable release
- `ghcr.io/craigst/btt-auto-manager:v2.0.0` - Specific version

## 📊 Monitoring

### Container Health
```bash
# Check container status
docker ps | grep btt-auto-manager

# View resource usage
docker stats btt-auto-manager

# Check health status
docker inspect btt-auto-manager | grep Health -A 10
```

### Log Monitoring
```bash
# Follow logs
docker-compose logs -f

# Search for errors
docker-compose logs | grep ERROR

# Export logs
docker-compose logs > btt-logs.txt
```

## 🔒 Security Notes

- **USB Access**: Container runs in privileged mode for ADB access
- **Network**: Webhook server exposed on port 5680
- **Local Access**: Designed for local network use
- **Firewall**: Consider restricting access to trusted networks

## 🐛 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs

# Check if port is in use
netstat -tulpn | grep 5680

# Check Docker daemon
docker info
```

### Webhook Not Responding
```bash
# Check container status
docker ps | grep btt-auto-manager

# Test from inside container
docker exec btt-auto-manager curl http://localhost:5680/healthz

# Check webhook port
docker exec btt-auto-manager netstat -tulpn | grep 5680
```

### ADB Device Issues
```bash
# Check USB devices
lsusb

# Restart ADB in container
docker exec btt-auto-manager adb kill-server
docker exec btt-auto-manager adb start-server

# Check ADB devices
docker exec btt-auto-manager adb devices
```

## 📞 Support

- **Repository**: https://github.com/craigst/btt-auto-manager
- **Issues**: https://github.com/craigst/btt-auto-manager/issues
- **Documentation**: https://github.com/craigst/btt-auto-manager/blob/main/README.md

---

**Quick Start**: `curl -sSL https://raw.githubusercontent.com/craigst/btt-auto-manager/main/run-from-github.sh | bash` 
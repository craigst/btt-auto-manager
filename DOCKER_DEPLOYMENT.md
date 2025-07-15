# 🐳 Docker Deployment Guide

This guide shows you how to deploy BTT Auto Manager using the GitHub-hosted Docker image.

## 🚀 Quick Start with GitHub Container Registry

### 1. Pull the Docker Image
```bash
# Pull the latest image from GitHub Container Registry
docker pull ghcr.io/craigst/btt-auto-manager:main

# Or pull a specific version
docker pull ghcr.io/craigst/btt-auto-manager:latest
```

### 2. Create Configuration
```bash
# Create configuration directory
mkdir -p ~/btt-auto-manager/{db,logs,config}

# Create configuration file
cat > ~/btt-auto-manager/config/btt_config.json << EOF
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

### 3. Run the Container
```bash
docker run -d \
  --name btt-auto-manager \
  --restart unless-stopped \
  -p 5680:5680 \
  -v ~/btt-auto-manager/db:/app/db \
  -v ~/btt-auto-manager/logs:/app/logs \
  -v ~/btt-auto-manager/config/btt_config.json:/app/btt_config.json \
  -v /dev/bus/usb:/dev/bus/usb \
  --privileged \
  ghcr.io/craigst/btt-auto-manager:main
```

## 📋 Docker Compose Method

### 1. Create docker-compose.yml
```yaml
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

networks:
  btt-network:
    driver: bridge
```

### 2. Run with Docker Compose
```bash
# Create directories
mkdir -p db logs

# Create configuration
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

# Start the service
docker-compose up -d
```

## 🔧 One-Line Deployment

### Quick Start Script
```bash
# Download and run in one command
curl -sSL https://raw.githubusercontent.com/craigst/btt-auto-manager/main/scripts/setup.sh | bash && \
docker run -d --name btt-auto-manager --restart unless-stopped -p 5680:5680 \
  -v $(pwd)/db:/app/db -v $(pwd)/logs:/app/logs \
  -v $(pwd)/btt_config.json:/app/btt_config.json \
  -v /dev/bus/usb:/dev/bus/usb --privileged \
  ghcr.io/craigst/btt-auto-manager:main
```

## 🌐 Available Docker Images

### Image Tags
- `ghcr.io/craigst/btt-auto-manager:main` - Latest main branch
- `ghcr.io/craigst/btt-auto-manager:latest` - Latest stable release
- `ghcr.io/craigst/btt-auto-manager:v2.0.0` - Specific version
- `ghcr.io/craigst/btt-auto-manager:sha-abc123` - Specific commit

### View Available Images
Visit: https://github.com/craigst/btt-auto-manager/packages

## 🧪 Testing the Deployment

### Health Check
```bash
curl http://localhost:5680/healthz
```

### Status Check
```bash
curl http://localhost:5680/status | jq
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

## 🔄 Management Commands

### Container Management
```bash
# View logs
docker logs -f btt-auto-manager

# Stop container
docker stop btt-auto-manager

# Start container
docker start btt-auto-manager

# Restart container
docker restart btt-auto-manager

# Remove container
docker rm -f btt-auto-manager
```

### Docker Compose Management
```bash
# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Start service
docker-compose up -d

# Restart service
docker-compose restart
```

## 🔒 Security Considerations

### Network Access
- **Default**: Webhook server runs on localhost (127.0.0.1)
- **Docker**: Exposed on 0.0.0.0:5680
- **Firewall**: Consider restricting access to trusted networks

### USB Device Access
- **Privileged Mode**: Required for ADB access
- **Device Permissions**: Ensure proper USB device permissions
- **Security**: Only use on trusted systems

## 🐛 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker logs btt-auto-manager

# Check if port is in use
netstat -tulpn | grep 5680

# Check Docker daemon
docker info
```

#### ADB Device Not Found
```bash
# Check USB device access
lsusb

# Check container USB access
docker exec btt-auto-manager lsusb

# Restart ADB in container
docker exec btt-auto-manager adb kill-server
docker exec btt-auto-manager adb start-server
```

#### Webhook Not Responding
```bash
# Check if container is running
docker ps | grep btt-auto-manager

# Check webhook port
docker exec btt-auto-manager netstat -tulpn | grep 5680

# Test from inside container
docker exec btt-auto-manager curl http://localhost:5680/healthz
```

## 📊 Monitoring

### Container Stats
```bash
# Resource usage
docker stats btt-auto-manager

# Container info
docker inspect btt-auto-manager
```

### Log Monitoring
```bash
# Follow logs
docker logs -f btt-auto-manager

# Search logs
docker logs btt-auto-manager | grep ERROR

# Export logs
docker logs btt-auto-manager > btt-logs.txt
```

## 🔄 Updates

### Update to Latest Version
```bash
# Pull latest image
docker pull ghcr.io/craigst/btt-auto-manager:main

# Stop and remove old container
docker stop btt-auto-manager
docker rm btt-auto-manager

# Run new container (same command as above)
docker run -d --name btt-auto-manager --restart unless-stopped -p 5680:5680 \
  -v ~/btt-auto-manager/db:/app/db \
  -v ~/btt-auto-manager/logs:/app/logs \
  -v ~/btt-auto-manager/config/btt_config.json:/app/btt_config.json \
  -v /dev/bus/usb:/dev/bus/usb --privileged \
  ghcr.io/craigst/btt-auto-manager:main
```

### Docker Compose Update
```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

## 🌍 Production Deployment

### Systemd Service
```bash
# Create systemd service file
sudo tee /etc/systemd/system/btt-auto-manager.service << EOF
[Unit]
Description=BTT Auto Manager
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/btt-auto-manager
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable btt-auto-manager
sudo systemctl start btt-auto-manager
```

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5680;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

**Repository**: https://github.com/craigst/btt-auto-manager  
**Docker Images**: https://github.com/craigst/btt-auto-manager/packages  
**Documentation**: https://github.com/craigst/btt-auto-manager/blob/main/README.md 
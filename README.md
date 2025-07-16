# BTT Auto Manager

Automated SQL Database Extraction Tool with Webhooks for BTT (Big Truck Tracker) data management.

## Features

- **Automated SQL Extraction**: Automatically extracts data from BTT SQLite databases
- **Webhook Integration**: RESTful API endpoints for remote control and monitoring
- **ADB Device Management**: Connect and manage Android devices via ADB
- **Real-time Status**: Live status monitoring and health checks
- **Dark Theme UI**: Modern web interface with dark theme
- **Ping Testing**: Network connectivity testing before ADB connections
- **Device Naming**: Custom names for ADB devices

## Quick Start

### Docker Deployment (Recommended)

1. **Build the Docker image:**
   ```bash
   docker build -t btt-auto-manager:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d --name btt-auto-manager --restart unless-stopped \
     -p 5680:5680 \
     -v /path/to/your/config.json:/app/btt_config.json \
     btt-auto-manager:latest
   ```

3. **Access the web UI:**
   - **Web Interface**: http://your-server-ip:5680/
   - **Health Check**: http://your-server-ip:5680/healthz

## Webhook API Endpoints

All endpoints are available at `http://your-server-ip:5680/`

### GET Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `/` | Web UI interface | HTML page |
| `/webhook/ui` | Web UI interface (alias) | HTML page |
| `/healthz` | Health check | `OK` |
| `/status` | System status | JSON status data |
| `/webhook/adb-ips` | List ADB devices | JSON array of devices |
| `/webhook/dwjjob` | Get job data | JSON job data |
| `/webhook/dwvveh` | Get vehicle data | JSON vehicle data |

### POST Endpoints

| Endpoint | Description | Request Body |
|----------|-------------|--------------|
| `/webhook/control` | Control operations | `{"action": "toggle_auto"}` |
| `/webhook/adb-ips` | ADB device management | `{"action": "add", "ip": "192.168.1.100:5555"}` |
| `/webhook/test-connection` | Test ADB connection | `{"ip": "192.168.1.100:5555"}` |

### Control Actions

**POST `/webhook/control`**
```json
{
  "action": "toggle_auto" | "set_interval" | "run_extraction" | "update_status",
  "minutes": 20  // for set_interval action
}
```

**POST `/webhook/adb-ips`**
```json
{
  "action": "add" | "remove" | "test_connection" | "rename",
  "ip": "192.168.1.100:5555",
  "name": "Device Name"  // for rename action
}
```

## Configuration

The application uses `btt_config.json` for configuration:

```json
{
  "auto_enabled": false,
  "interval_minutes": 20,
  "last_sql_atime": null,
  "last_locations": 0,
  "last_cars": 0,
  "last_loads": 0,
  "webhook_enabled": true,
  "webhook_port": 5680,
  "adb_ips": [
    {
      "ip": "192.168.1.24:5555",
      "name": "My Android Phone"
    }
  ]
}
```

## Port Configuration

- **Default Port**: 5680
- **Docker Port Mapping**: `-p 5680:5680`
- **Environment Variable**: `WEBHOOK_PORT=5680`
- **Health Check**: `http://localhost:5680/healthz`

## Docker Configuration

### Dockerfile Features
- Ubuntu 22.04 base image
- Python 3 with required dependencies
- ADB tools installed
- Ping utilities for network testing
- Non-root user (bttuser) for security
- Health checks configured
- Port 5680 exposed

### Environment Variables
- `WEBHOOK_HOST=0.0.0.0` (bind to all interfaces)
- `WEBHOOK_PORT=5680` (webhook server port)
- `PYTHONUNBUFFERED=1` (unbuffered Python output)

### Volume Mounts
- `/app/btt_config.json` - Configuration file
- `/app/db` - Database directory
- `/app/logs` - Log files directory

## Features

### ADB Device Management
- **Connection Testing**: Ping test before ADB connection
- **Device Naming**: Custom names for easy identification
- **Status Monitoring**: Real-time connection status
- **Command Output**: Detailed ADB command results

### Web Interface
- **Dark Theme**: Modern dark UI design
- **Real-time Updates**: Live status monitoring
- **Device Management**: Add, remove, rename devices
- **Connection Testing**: Test ADB connections with ping
- **Modal Popups**: Command output display

### Automation
- **Scheduled Extraction**: Automatic SQL data extraction
- **Configurable Intervals**: Set custom update intervals
- **Status Tracking**: Monitor last extraction times
- **Error Handling**: Robust error handling and logging

## Development

### Local Development
```bash
# Install dependencies
pip3 install -r requirements.txt

# Run locally
python3 btt_auto.py
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:5680/healthz

# Get status
curl http://localhost:5680/status

# List ADB devices
curl http://localhost:5680/webhook/adb-ips

# Test ADB connection
curl -X POST http://localhost:5680/webhook/test-connection \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100:5555"}'
```

## Troubleshooting

### Common Issues

1. **Container Permission Errors**
   - Ensure config file has correct permissions
   - Use volume mount for config file

2. **ADB Connection Issues**
   - Check device IP and port (default: 5555)
   - Verify network connectivity with ping
   - Ensure ADB server is running

3. **Port Access Issues**
   - Verify port 5680 is exposed in Docker
   - Check firewall settings
   - Test with `curl http://localhost:5680/healthz`

### Logs
```bash
# View container logs
docker logs btt-auto-manager

# Follow logs in real-time
docker logs -f btt-auto-manager
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
# BTT Auto Manager

A Python-based automated SQL database extraction tool for Android devices running the BCA Track app. Features a modern web UI, ADB device management, and webhook API for integration.

## Features

- **Automated SQL Extraction**: Automatically extracts SQLite databases from Android devices
- **Web UI**: Modern React-based interface for monitoring and control
- **ADB Device Management**: Manage multiple Android device connections
- **Webhook API**: RESTful API for integration with other systems
- **Auto-Update**: Configurable automatic extraction intervals
- **Docker Support**: Easy deployment with Docker containers

## Quick Start

### Docker Deployment (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/craigst/btt-auto-manager.git
   cd btt-auto-manager
   ```

2. **Build and run with Docker:**
   ```bash
   docker build -t btt-auto-manager:latest .
   docker run -d --name btt-auto-manager -p 5680:5680 \
     -v $(pwd)/db:/app/db \
     -v $(pwd)/logs:/app/logs \
     --restart unless-stopped \
     btt-auto-manager:latest
   ```

3. **Access the web UI:**
   - Open your browser to `http://localhost:5680`
   - The web UI provides full control over the system

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ADB tools:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install android-tools-adb
   
   # macOS
   brew install android-platform-tools
   ```

3. **Run the application:**
   ```bash
   python3 btt_auto.py
   ```

## Web UI Features

The web interface provides:

- **System Status**: Real-time monitoring of auto-update status, server uptime, and database statistics
- **SQL Data Viewer**: Browse extracted DWJJOB and DWVVEH data
- **ADB Device Management**: Add/remove Android device IPs and test connections
- **System Controls**: Toggle auto-update, set intervals, and trigger manual extractions
- **Auto-refresh**: Updates every 30 seconds to show current status

## Webhook API

The application provides a RESTful API for integration:

### Status Endpoints

- `GET /status` - Get system status and statistics
- `GET /healthz` - Health check endpoint
- `GET /webhook/dwjjob` - Get DWJJOB data
- `GET /webhook/dwvveh` - Get DWVVEH data
- `GET /webhook/adb-ips` - Get configured ADB IP addresses

### Control Endpoints

- `POST /webhook/control` - Control system operations
  ```json
  {
    "action": "toggle_auto" | "set_interval" | "run_extraction" | "update_status",
    "minutes": 5  // for set_interval action
  }
  ```

- `POST /webhook/adb-ips` - Manage ADB IP addresses
  ```json
  {
    "action": "add" | "remove",
    "ip": "192.168.1.100:5555"
  }
  ```

- `POST /webhook/test-connection` - Test ADB connection
  ```json
  {
    "ip": "192.168.1.100:5555"
  }
  ```

### Example API Usage

```bash
# Get system status
curl http://localhost:5680/status

# Toggle auto-update
curl -X POST http://localhost:5680/webhook/control \
  -H "Content-Type: application/json" \
  -d '{"action": "toggle_auto"}'

# Add ADB device
curl -X POST http://localhost:5680/webhook/adb-ips \
  -H "Content-Type: application/json" \
  -d '{"action": "add", "ip": "192.168.1.24:5555"}'

# Test connection
curl -X POST http://localhost:5680/webhook/test-connection \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.24:5555"}'
```

## Configuration

The application uses `btt_config.json` for configuration:

```json
{
  "auto_enabled": false,
  "interval_minutes": 5,
  "last_sql_atime": "2025-07-15 22:45:19",
  "last_locations": 18,
  "last_cars": 58,
  "last_loads": 8,
  "webhook_enabled": true,
  "webhook_port": 5680,
  "adb_ips": ["192.168.1.24:5555"]
}
```

### Configuration Options

- `auto_enabled`: Enable/disable automatic extraction
- `interval_minutes`: Minutes between automatic extractions (1-1440)
- `webhook_enabled`: Enable/disable webhook server
- `webhook_port`: Port for webhook server (default: 5680)
- `adb_ips`: List of Android device IP addresses

## ADB Device Setup

1. **Enable Developer Options** on your Android device
2. **Enable USB Debugging** and **Network Debugging**
3. **Get device IP** from Settings > About Phone > Status > IP address
4. **Add device** via web UI or API: `IP:5555` (e.g., `192.168.1.24:5555`)

## Auto-Update Behavior

- **Enabled**: Automatically extracts SQL data at the configured interval
- **Disabled**: Manual extraction only
- **No ADB Connection**: Auto-update is automatically disabled when no devices are connected
- **Connection Test**: Tests all configured devices and shows connection status

## File Structure

```
btt-auto-manager/
├── btt_auto.py          # Main application
├── getsql.py            # SQL extraction logic
├── btt_launcher.py      # Launcher script
├── web_ui.html          # Web interface
├── btt_config.json      # Configuration file
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-entrypoint.sh # Docker entry point
├── db/                 # Extracted database files
└── logs/               # Application logs
```

## Docker Configuration

The Docker setup includes:

- **Base Image**: Ubuntu 22.04 with Python 3
- **Dependencies**: ADB tools, Python packages
- **Volumes**: Database and logs directories
- **Port**: 5680 for web interface
- **User**: Non-root user for security

### Docker Compose (Optional)

```yaml
version: '3.8'
services:
  btt-auto-manager:
    build: .
    ports:
      - "5680:5680"
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
    restart: unless-stopped
```

## Troubleshooting

### Common Issues

1. **ADB Connection Failed**
   - Ensure device has network debugging enabled
   - Check device IP address is correct
   - Verify device is on the same network

2. **Web UI Not Loading**
   - Check container is running: `docker ps`
   - Verify port 5680 is accessible
   - Check logs: `docker logs btt-auto-manager`

3. **Auto-Update Not Working**
   - Verify ADB device is connected
   - Check auto-update is enabled in web UI
   - Review logs for extraction errors

### Logs

- **Container logs**: `docker logs btt-auto-manager`
- **Application logs**: Check `logs/` directory
- **Webhook logs**: Available in web UI

## Development

### Building React Web UI

The web UI is built with vanilla JavaScript/HTML for simplicity. For React development:

1. Create a new React app
2. Copy the web UI logic to React components
3. Build and serve static files

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs for error messages
- Open an issue on GitHub

---

**BTT Auto Manager** - Automated SQL extraction for Android devices with modern web interface and API integration. 
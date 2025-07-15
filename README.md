# BTT Auto Manager

A comprehensive Python-based automation tool for extracting SQLite databases from Android devices running the BCA Track application. Provides both manual and automated extraction capabilities with a RESTful webhook API.

## 🚀 Features

- **Automated SQL Extraction**: Scheduled extraction with configurable intervals
- **ADB Device Management**: Support for both USB and network-connected devices
- **Webhook API**: RESTful endpoints for data access and remote control
- **Real-time Status Monitoring**: Live status updates and statistics
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Cross-platform**: Works on Linux, Windows, and macOS

## 📋 Prerequisites

- **Docker** and **Docker Compose** (for containerized deployment)
- **ADB** (Android Debug Bridge) - included in Docker image
- **Android Device** with USB debugging enabled
- **BCA Track App** installed on the Android device

## 🐳 Quick Start with Docker

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/btt-auto-manager.git
cd btt-auto-manager
```

### 2. Create Configuration File
```bash
# Create default configuration
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

### 3. Create Required Directories
```bash
mkdir -p db logs
```

### 4. Build and Run with Docker Compose
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### 5. Access the Webhook API
The webhook server will be available at `http://localhost:5680`

## 🔧 Manual Installation

### 1. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install ADB (Linux)
sudo apt install android-tools-adb

# Install ADB (macOS)
brew install android-platform-tools

# Install ADB (Windows)
# Download from Android SDK Platform Tools
```

### 2. Enable USB Debugging
1. Go to Settings > Developer options on your Android device
2. Enable "USB debugging"
3. Connect device via USB

### 3. Run the Application
```bash
# Launch the program
python3 btt_launcher.py

# Or run directly
python3 btt_auto.py
```

## 🌐 Webhook API

### Base URL
```
http://localhost:5680
```

### Available Endpoints

#### Data Endpoints
- `GET /webhook/dwjjob` - Get location data (DWJJOB table)
- `GET /webhook/dwvveh` - Get vehicle data (DWVVEH table)
- `GET /webhook/adb-ips` - Get configured ADB IP addresses

#### Control Endpoints
- `POST /webhook/control` - Control auto-update and extraction
- `POST /webhook/adb-ips` - Manage ADB IP addresses

#### Status Endpoints
- `GET /status` - Get comprehensive system status
- `GET /healthz` - Health check

### Example Usage
```bash
# Get location data
curl http://localhost:5680/webhook/dwjjob

# Get vehicle data
curl http://localhost:5680/webhook/dwvveh

# Toggle auto-update
curl -X POST http://localhost:5680/webhook/control \
  -H "Content-Type: application/json" \
  -d '{"action": "toggle_auto"}'

# Set 10-minute interval
curl -X POST http://localhost:5680/webhook/control \
  -H "Content-Type: application/json" \
  -d '{"action": "set_interval", "minutes": 10}'

# Add ADB IP address
curl -X POST http://localhost:5680/webhook/adb-ips \
  -H "Content-Type: application/json" \
  -d '{"action": "add", "ip": "192.168.1.100:5555"}'

# Get system status
curl http://localhost:5680/status
```

## 📁 Project Structure

```
btt-auto-manager/
├── btt_launcher.py        # Program entry point
├── getsql.py              # Core SQL extraction engine
├── btt_auto.py            # Main auto manager with webhooks
├── btt_config.json        # Configuration file
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── .dockerignore          # Docker ignore file
├── .gitignore             # Git ignore file
├── README.md              # This file
├── AUTOREADME.md          # Detailed documentation
├── BTT_AUTO_MANAGER_CODEX.md  # Technical codex
├── db/                    # Database storage (created automatically)
└── logs/                  # Log files (created automatically)
```

## 🔧 Configuration

The application uses `btt_config.json` for configuration:

```json
{
  "auto_enabled": false,           // Auto-update toggle
  "interval_minutes": 20,          // Update interval in minutes
  "last_sql_atime": null,          // Last SQL file access time
  "last_locations": 0,             // Last known location count
  "last_cars": 0,                  // Last known car count
  "last_loads": 0,                 // Last known load count
  "webhook_enabled": true,         // Webhook server toggle
  "webhook_port": 5680,            // Webhook server port
  "adb_ips": []                    // Stored ADB IP addresses
}
```

## 🗄️ Database Schema

### DWJJOB Table (Locations/Jobs)
Contains job/location information with GPS coordinates and delivery details.

**Key Columns**:
- `dwjkey`: Unique job identifier
- `dwjDriver`: Driver ID/name
- `dwjLoad`: Load number/reference
- `dwjDate`, `dwjTime`: Date and time
- `dwjName`: Customer/contact name
- `dwjAdd1-4`: Address lines
- `dwjLat`, `dwjLong`: GPS coordinates
- `dwjStatus`: Job status

### DWVVEH Table (Vehicles)
Contains vehicle information and fleet management data.

**Key Columns**:
- `dwvKey`: Unique vehicle identifier
- `dwvDriver`: Assigned driver ID
- `dwvLoad`: Current load assignment
- `dwvSerial`: Vehicle serial/VIN number
- `dwvMake`, `dwvModel`: Vehicle details
- `dwvStatus`: Vehicle status
- `dwvLocation`: Current location

## 🐛 Troubleshooting

### Common Issues

#### ADB Device Not Found
- Enable USB debugging on device
- Try different USB cables
- Add device IP address for network connection
- Check device authorization

#### Permission Denied
- Device may need root access
- Try different ADB connection methods
- Check device file permissions

#### Webhook Server Won't Start
- Check if port 5680 is available
- Ensure no firewall blocking
- Verify Docker container is running

#### Docker Issues
- Ensure Docker and Docker Compose are installed
- Check container logs: `docker-compose logs -f`
- Verify USB device access permissions

### Debug Commands
```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs -f btt-auto-manager

# Access container shell
docker-compose exec btt-auto-manager bash

# Check webhook health
curl http://localhost:5680/healthz
```

## 🔒 Security Considerations

- **Local Access Only**: Webhook server runs on localhost by default
- **No Authentication**: Designed for local network use
- **USB Device Access**: Docker container requires privileged mode for ADB
- **Network Security**: If exposing to network, implement proper security measures

## 📈 Performance

- **Extraction Time**: Typically 2-5 seconds per extraction
- **Memory Usage**: ~50MB typical
- **Webhook Response**: Sub-second response times
- **Concurrent Requests**: Supports multiple simultaneous webhook requests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is designed for internal use with the BCA Track application. Ensure compliance with your organization's policies and the Android app's terms of service.

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review container logs
3. Verify ADB and device connectivity
4. Ensure all prerequisites are met

---

**Version**: 2.0.0  
**Last Updated**: 2025-07-15  
**Compatibility**: Python 3.7+, Android 5.0+, Docker 20.0+ 
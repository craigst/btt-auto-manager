# BTT Auto Manager - Complete Technical Codex

## 📋 Program Overview

**BTT Auto Manager** is a sophisticated Python-based automation system designed for extracting SQLite databases from Android devices running the BCA Track application. The system provides both manual and automated extraction capabilities, serving extracted data via a RESTful webhook API for integration with other systems.

### Core Purpose
- Extract SQLite database (`sql.db`) from Android devices using ADB (Android Debug Bridge)
- Provide automated extraction scheduling with configurable intervals
- Serve extracted data via HTTP/JSON webhook API
- Manage ADB device connections (both USB and network)
- Support both root and non-root device access methods

### Target Application
- **BCA Track Android App**: Fleet management application
- **Database Path**: `/data/data/com.bca.bcatrack/cache/cache/data/sql.db`
- **Primary Tables**: DWJJOB (locations) and DWVVEH (vehicles)

---

## 🏗️ System Architecture

### Multi-Threaded Design
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main Thread   │    │ Auto-Update     │    │ Webhook Server  │
│   (UI/Menu)     │    │ Thread          │    │ Thread          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Shared Config   │
                    │ (btt_config.json)│
                    └─────────────────┘
```

### Component Interaction Flow
1. **Main Thread**: Handles user interface and menu system
2. **Auto-Update Thread**: Manages scheduled SQL extraction
3. **Webhook Thread**: Serves HTTP API endpoints
4. **Shared Configuration**: JSON-based persistent storage

---

## 📁 File Structure & Components

### Core Files
```
BCA-BTT-APP/
├── btt_launcher.py        # Program entry point and menu selector
├── getsql.py              # Core SQL extraction engine (558 lines)
├── btt_auto.py            # Main auto manager with webhooks (800 lines)
├── btt_config.json        # Configuration persistence
├── AUTOREADME.md          # User documentation
├── getsql.log             # Extraction activity logs
└── db/                    # Extracted database storage
    └── sql.db            # Latest extracted SQLite database
```

### File Responsibilities

#### `btt_launcher.py` (42 lines)
- **Purpose**: Simple launcher with menu interface
- **Functions**:
  - Display program options
  - Launch single SQL extraction (`getsql.py`)
  - Launch Auto Manager (`btt_auto.py`)
- **Dependencies**: `rich` library for UI

#### `getsql.py` (558 lines)
- **Purpose**: Core extraction engine
- **Key Functions**:
  - ADB device detection and connection
  - Root/non-root file access handling
  - SQLite database extraction and parsing
  - Database statistics calculation
  - Error handling and diagnostics
- **Technical Implementation**:
  - Uses `subprocess` for ADB command execution
  - Implements fallback mechanisms for different root access methods
  - Parses SQLite data using native Python `sqlite3` module
  - Provides detailed timing and diagnostic information

#### `btt_auto.py` (800 lines)
- **Purpose**: Main auto manager with webhook server
- **Key Functions**:
  - Automated extraction scheduling
  - Webhook server (HTTP/JSON API)
  - ADB IP address management
  - Configuration persistence
  - Real-time status monitoring
- **Technical Implementation**:
  - Multi-threaded architecture
  - Built-in HTTP server using Python's `http.server`
  - JSON-based configuration management
  - Thread-safe operations

#### `btt_config.json`
- **Purpose**: Persistent configuration storage
- **Configuration Schema**:
```json
{
  "auto_enabled": false,           // Auto-update toggle
  "interval_minutes": 20,          // Update interval in minutes
  "last_sql_atime": "2025-07-15 22:45:19",  // Last SQL file access time
  "last_locations": 18,            // Last known location count
  "last_cars": 58,                 // Last known car count
  "last_loads": 8,                 // Last known load count
  "webhook_enabled": true,         // Webhook server toggle
  "webhook_port": 5680,            // Webhook server port
  "adb_ips": []                    // Stored ADB IP addresses
}
```

---

## 🔧 Technical Implementation Details

### ADB Integration (`getsql.py`)

#### Device Connection Methods
```python
def get_connected_device():
    """Detect connected ADB devices"""
    out = run_adb('adb devices')
    lines = out.splitlines()
    for line in lines[1:]:
        if line.strip() and ('device' in line and not 'offline' in line):
            return line.split()[0]
    return None
```

#### Root Access Handling
```python
def run_adb_with_root(cmd, device, timeout=10):
    """Try non-root first, then root methods"""
    # Try non-root first
    try:
        out = run_adb(cmd, timeout=timeout)
        if out is not None and 'Permission denied' not in str(out):
            return out, 'non-root', None
    except Exception as e:
        return None, 'non-root', f"Non-root error: {e}"
    
    # Try su -c method
    shell_part = cmd.split('shell',1)[1].strip() if 'shell' in cmd else cmd
    rootc_cmd = f'adb -s {device} shell su -c "{shell_part}"'
    try:
        rootc_out = run_adb(rootc_cmd, timeout=timeout)
        if rootc_out is not None and 'Permission denied' not in str(rootc_out):
            return rootc_out, 'suc', None
    except Exception as e:
        return None, 'suc', f"RootC error: {e}"
    
    return None, 'all-failed', 'All root forms failed'
```

#### Database Extraction Process
1. **Check ADB Installation**: Verify ADB is available
2. **Detect Connected Device**: Find available Android device
3. **Clean Up Old Files**: Remove previous `/sdcard/sql.db`
4. **Verify Database Exists**: Check if `sql.db` exists on device
5. **Copy to SD Card**: Copy database to accessible location
6. **Pull to Local**: Download database to local `db/` directory
7. **Clean Up**: Remove temporary file from device
8. **Analyze Data**: Extract statistics and metadata

### Webhook Server Implementation (`btt_auto.py`)

#### HTTP Server Setup
```python
class WebhookHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop('manager', None)
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to use custom logging"""
        message = format % args
        if self.manager:
            self.manager.log_webhook(f"HTTP: {message}")
```

#### Thread Management
```python
def start_webhook_server(self):
    """Start webhook server in separate thread"""
    def handler_factory(*args, **kwargs):
        return WebhookHandler(*args, manager=self, **kwargs)
    
    self.webhook_server = HTTPServer((WEBHOOK_HOST, self.config.get('webhook_port', WEBHOOK_PORT)), handler_factory)
    self.webhook_thread = threading.Thread(target=self.webhook_server.serve_forever, daemon=True)
    self.webhook_thread.start()
```

### Auto-Update System

#### Scheduling Loop
```python
def auto_update_loop(self):
    """Main loop for auto-updating"""
    while self.running:
        try:
            # Check if auto is still enabled
            if not self.config.get("auto_enabled", False):
                break
            
            # Try to connect to ADB devices if needed
            if not getsql.get_connected_device():
                self.try_connect_adb_ips()
            
            # Run getsql
            self.run_getsql()
            
            # Wait for next interval
            interval_seconds = self.config.get("interval_minutes", 5) * 60
            time.sleep(interval_seconds)
            
        except Exception as e:
            console.print(f"[red]Auto-update error: {e}[/red]")
            time.sleep(60)  # Wait 1 minute before retrying
```

---

## 🌐 Webhook API Reference

### Base Configuration
- **Host**: `localhost`
- **Port**: `5680` (configurable)
- **Protocol**: HTTP/1.1
- **Authentication**: None (local server only)
- **CORS**: Enabled with `Access-Control-Allow-Origin: *`

### Endpoint Categories

#### 📊 Data Endpoints

##### GET `/webhook/dwjjob`
Returns DWJJOB table data as JSON array.

**Response Format**:
```json
[
  {
    "dwjkey": "S155183-WBAC-000070-C",
    "dwjDriver": "DRIVER001",
    "dwjDate": "2025-07-15",
    "dwjTime": "14:30:00",
    "dwjLoad": "S155183",
    "dwjName": "Customer Name",
    "dwjAdd1": "123 Main St",
    "dwjAdd2": "Suite 100",
    "dwjAdd3": "City, State 12345",
    "dwjAdd4": "Country",
    "dwjLat": "40.7128",
    "dwjLong": "-74.0060",
    "dwjStatus": "COMPLETED",
    "dwjNotes": "Delivery completed",
    "dwjCreated": "2025-07-15T14:30:00",
    "dwjModified": "2025-07-15T14:35:00",
    "dwjSync": "1",
    "dwjVersion": "1.0"
  }
]
```

##### GET `/webhook/dwvveh`
Returns DWVVEH table data as JSON array.

**Response Format**:
```json
[
  {
    "dwvKey": "VEH001",
    "dwvDriver": "DRIVER001",
    "dwvLoad": "S155183",
    "dwvSerial": "ABC123",
    "dwvMake": "Ford",
    "dwvModel": "F-150",
    "dwvYear": "2023",
    "dwvColor": "White",
    "dwvStatus": "ACTIVE",
    "dwvLocation": "Warehouse A",
    "dwvFuel": "85",
    "dwvMileage": "15000",
    "dwvLastService": "2025-06-15",
    "dwvNextService": "2025-09-15",
    "dwvInsurance": "ACTIVE",
    "dwvRegistration": "2025-12-31",
    "dwvCreated": "2025-01-15T10:00:00",
    "dwvModified": "2025-07-15T14:30:00",
    "dwvSync": "1",
    "dwvVersion": "1.0"
  }
]
```

##### GET `/webhook/adb-ips`
Returns list of configured ADB IP addresses.

**Response Format**:
```json
[
  "192.168.1.100:5555",
  "192.168.1.101:5555"
]
```

#### 🔧 Control Endpoints

##### POST `/webhook/control`
Control the auto manager system.

**Request Format**:
```json
{
  "action": "toggle_auto" | "set_interval" | "run_now",
  "minutes": 10  // Required for set_interval action
}
```

**Actions**:
- `toggle_auto`: Enable/disable automatic extraction
- `set_interval`: Set update interval (1-1440 minutes)
- `run_now`: Trigger immediate SQL extraction

**Response Format**:
```json
{
  "status": "success" | "error",
  "message": "Action completed successfully"
}
```

##### POST `/webhook/adb-ips`
Manage ADB IP addresses.

**Request Format**:
```json
{
  "action": "add" | "remove",
  "ip": "192.168.1.100:5555"
}
```

**Response Format**:
```json
{
  "status": "success" | "error",
  "message": "Added IP: 192.168.1.100:5555"
}
```

#### 📈 Status & Health Endpoints

##### GET `/status`
Returns comprehensive system status.

**Response Format**:
```json
{
  "status": "idle" | "processing" | "processed" | "error",
  "lastProcessed": "2025-07-15T14:30:00",
  "timeSinceLastUpdate": 300000,
  "timeSinceLastUpdateFormatted": "5 minutes ago",
  "dwjjobCount": 18,
  "dwvvehCount": 58,
  "serverTime": "2025-07-15T14:35:00",
  "uptime": 3600.5,
  "webhookEnabled": true,
  "webhookPort": 5680,
  "autoEnabled": true,
  "intervalMinutes": 5,
  "lastLocations": 18,
  "lastCars": 58,
  "lastLoads": 8,
  "adbIps": ["192.168.1.100:5555"]
}
```

##### GET `/healthz`
Simple health check endpoint.

**Response**: `OK` (text/plain)

---

## 🗄️ Database Schema

### DWJJOB Table (Locations/Jobs)
Contains job/location information with GPS coordinates and delivery details.

**Primary Key**: `dwjkey`

**Key Columns**:
- `dwjkey`: Unique job identifier (Primary Key)
- `dwjDriver`: Driver ID/name
- `dwjLoad`: Load number/reference
- `dwjDate`: Job date (YYYY-MM-DD)
- `dwjTime`: Job time (HH:MM:SS)
- `dwjName`: Customer/contact name
- `dwjAdd1-4`: Address lines 1-4
- `dwjLat`: Latitude coordinate
- `dwjLong`: Longitude coordinate
- `dwjStatus`: Job status (COMPLETED, PENDING, etc.)
- `dwjNotes`: Additional notes
- `dwjCreated`: Record creation timestamp
- `dwjModified`: Last modification timestamp
- `dwjSync`: Sync status flag
- `dwjVersion`: Data version

**Additional Columns** (30+ fields):
- Contact information
- Delivery instructions
- Route information
- Time windows
- Special requirements

### DWVVEH Table (Vehicles)
Contains vehicle information and fleet management data.

**Primary Key**: `dwvKey`

**Key Columns**:
- `dwvKey`: Unique vehicle identifier (Primary Key)
- `dwvDriver`: Assigned driver ID
- `dwvLoad`: Current load assignment
- `dwvSerial`: Vehicle serial/VIN number
- `dwvMake`: Vehicle manufacturer
- `dwvModel`: Vehicle model
- `dwvYear`: Vehicle year
- `dwvColor`: Vehicle color
- `dwvStatus`: Vehicle status (ACTIVE, MAINTENANCE, etc.)
- `dwvLocation`: Current location
- `dwvFuel`: Fuel level percentage
- `dwvMileage`: Current mileage
- `dwvLastService`: Last service date
- `dwvNextService`: Next service due date
- `dwvInsurance`: Insurance status
- `dwvRegistration`: Registration expiry
- `dwvCreated`: Record creation timestamp
- `dwvModified`: Last modification timestamp
- `dwvSync`: Sync status flag
- `dwvVersion`: Data version

**Additional Columns** (35+ fields):
- Vehicle specifications
- Maintenance history
- Fuel consumption
- Route assignments
- Performance metrics

---

## 🔄 Data Flow & Processing

### Extraction Process Flow
```
1. Device Detection
   ├── Check ADB installation
   ├── Detect connected devices
   └── Try network connections (if configured)

2. Database Access
   ├── Verify database exists on device
   ├── Check file permissions
   └── Determine access method (root/non-root)

3. File Transfer
   ├── Copy database to /sdcard
   ├── Pull database to local storage
   └── Clean up temporary files

4. Data Processing
   ├── Parse SQLite database
   ├── Extract DWJJOB and DWVVEH tables
   ├── Calculate statistics
   └── Update configuration

5. Webhook Serving
   ├── Convert data to JSON format
   ├── Serve via HTTP endpoints
   └── Log activity
```

### Error Handling Strategy
1. **Graceful Degradation**: System continues operation despite individual failures
2. **Retry Mechanisms**: Automatic retry for transient failures
3. **Fallback Methods**: Multiple approaches for root access
4. **Detailed Logging**: Comprehensive error tracking
5. **User Feedback**: Clear status reporting

---

## 🛠️ Configuration Management

### Configuration File Structure
```json
{
  "auto_enabled": false,           // Auto-update toggle
  "interval_minutes": 20,          // Update interval (1-1440)
  "last_sql_atime": "2025-07-15 22:45:19",  // Last extraction time
  "last_locations": 18,            // Last known DWJJOB count
  "last_cars": 58,                 // Last known DWVVEH count
  "last_loads": 8,                 // Last known unique loads
  "webhook_enabled": true,         // Webhook server toggle
  "webhook_port": 5680,            // Webhook server port
  "adb_ips": []                    // Network ADB IP addresses
}
```

### Configuration Operations
- **Loading**: Automatic loading on startup
- **Saving**: Automatic saving on changes
- **Validation**: Range checking for numeric values
- **Defaults**: Fallback to default values if missing
- **Persistence**: Survives program restarts

---

## 🔍 Logging & Diagnostics

### Log Files
1. **`getsql.log`**: Detailed extraction activity
2. **Webhook Logs**: HTTP request/response logging
3. **Console Output**: Real-time status updates

### Diagnostic Features
- **Timing Information**: Step-by-step timing analysis
- **Error Tracking**: Detailed error messages and stack traces
- **Device Information**: ADB device status and capabilities
- **File Statistics**: Database file metadata
- **Performance Metrics**: Extraction time and data counts

### Debug Commands
```python
def run_diagnostics_commands(device):
    """Run comprehensive device diagnostics"""
    diag_cmds = [
        ('whoami', f'adb -s {device} shell whoami'),
        ('id', f'adb -s {device} shell id'),
        ('su_whoami_0', f'adb -s {device} shell su 0 whoami'),
        ('su_id_0', f'adb -s {device} shell su 0 id'),
        ('su_whoami_c', f'adb -s {device} shell su -c "whoami"'),
        ('su_id_c', f'adb -s {device} shell su -c "id"'),
        ('ls_file', f'adb -s {device} shell ls -l "{DEVICE_DB_PATH}"'),
        ('ls_file_su0', f'adb -s {device} shell su 0 ls -l "{DEVICE_DB_PATH}"'),
        ('ls_file_suc', f'adb -s {device} shell su -c "ls -l {DEVICE_DB_PATH}"'),
        ('lsd_data', f'adb -s {device} shell ls -ld /data/data/com.bca.bcatrack/cache/cache/data'),
        ('lsd_data_su0', f'adb -s {device} shell su 0 ls -ld /data/data/com.bca.bcatrack/cache/cache/data'),
        ('lsd_data_suc', f'adb -s {device} shell su -c "ls -ld /data/data/com.bca.bcatrack/cache/cache/data"'),
    ]
```

---

## 🔒 Security Considerations

### Current Security Model
- **Local Access Only**: Webhook server runs on localhost
- **No Authentication**: Designed for local network use
- **File Permissions**: Relies on OS file permissions
- **Network Isolation**: No external network access

### Security Recommendations
1. **Network Security**: If exposing to network, implement proper authentication
2. **File Permissions**: Ensure proper file permissions for configuration
3. **ADB Security**: Use authorized devices only
4. **Data Protection**: Consider encryption for sensitive data
5. **Access Control**: Implement user authentication if needed

---

## 📈 Performance Characteristics

### Timing Benchmarks
- **ADB Connection**: 1-3 seconds
- **Database Copy**: 2-5 seconds (depending on size)
- **Data Extraction**: 1-2 seconds
- **Webhook Response**: <100ms
- **Memory Usage**: ~50MB typical

### Scalability Considerations
- **Concurrent Requests**: Supports multiple simultaneous webhook requests
- **Database Size**: Handles databases up to several hundred MB
- **Device Count**: Supports multiple ADB devices
- **Update Frequency**: Configurable from 1 minute to 24 hours

---

## 🚀 Usage Examples

### Command Line Usage
```bash
# Launch program
python btt_launcher.py

# Direct single extraction
python getsql.py

# Start auto manager
python btt_auto.py
```

### Webhook API Usage
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

### Integration Examples
```python
import requests
import json

# Get current location data
response = requests.get('http://localhost:5680/webhook/dwjjob')
locations = response.json()

# Get vehicle data
response = requests.get('http://localhost:5680/webhook/dwvveh')
vehicles = response.json()

# Control system
requests.post('http://localhost:5680/webhook/control', 
             json={'action': 'run_now'})

# Get system status
response = requests.get('http://localhost:5680/status')
status = response.json()
```

---

## 🐛 Troubleshooting Guide

### Common Issues & Solutions

#### ADB Device Not Found
**Symptoms**: "No device connected" error
**Solutions**:
- Enable USB debugging on device
- Try different USB cables
- Add device IP address for network connection
- Check device authorization

#### Permission Denied
**Symptoms**: "Permission denied" in logs
**Solutions**:
- Device may need root access
- Try different ADB connection methods
- Check device file permissions
- Use network connection instead of USB

#### Webhook Server Won't Start
**Symptoms**: "Failed to start webhook server"
**Solutions**:
- Check if port 5680 is available
- Ensure no firewall blocking
- Verify Python permissions
- Try different port number

#### SQL Extraction Fails
**Symptoms**: Extraction process fails
**Solutions**:
- Check device connection
- Verify BCA Track app is installed
- Review getsql.log for detailed errors
- Try manual extraction first

### Debug Procedures
1. **Check Logs**: Review `getsql.log` for detailed error information
2. **Run Diagnostics**: Use diagnostic commands to check device status
3. **Test Connectivity**: Verify ADB connection manually
4. **Check Permissions**: Ensure proper file and network permissions
5. **Validate Configuration**: Check `btt_config.json` for valid settings

---

## 🔄 Maintenance & Updates

### Configuration Updates
- All settings persist between restarts
- Configuration file is automatically created
- Manual editing of `btt_config.json` is supported
- Default values are applied for missing settings

### Log Management
- Logs are automatically managed
- Old entries are cleaned up automatically
- Maximum 100 webhook log entries retained
- Detailed logs available for troubleshooting

### Performance Monitoring
- Real-time status monitoring via webhook
- Extraction timing information
- Database statistics tracking
- System uptime monitoring

---

## 📋 Dependencies & Requirements

### Python Dependencies
- **Python 3.7+**: Core runtime
- **rich**: Terminal UI library
- **sqlite3**: Database operations (built-in)
- **subprocess**: ADB command execution (built-in)
- **threading**: Multi-threading support (built-in)
- **http.server**: Webhook server (built-in)
- **json**: Configuration management (built-in)

### System Requirements
- **ADB**: Android Debug Bridge
- **Android Device**: Running BCA Track app
- **Network**: For network device connections
- **Storage**: ~100MB for database storage
- **Memory**: ~50MB RAM usage

### Installation Commands
```bash
# Install Python dependencies
pip install rich

# Install ADB (Linux)
sudo apt install android-tools-adb

# Install ADB (macOS)
brew install android-platform-tools

# Install ADB (Windows)
# Download from Android SDK Platform Tools
```

---

## 📄 License & Compliance

### Usage Rights
- Designed for internal use with BCA Track application
- Ensure compliance with organization policies
- Respect Android app terms of service
- Follow data protection regulations

### Data Handling
- Local data storage only
- No external data transmission
- Respect device privacy settings
- Follow data retention policies

---

**Version**: 2.0.0  
**Last Updated**: 2025-07-15  
**Compatibility**: Python 3.7+, Android 5.0+  
**Author**: BTT Auto Manager Development Team  
**Documentation**: Complete technical reference for BTT Auto Manager system 
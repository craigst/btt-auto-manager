#!/usr/bin/env python3
import os
import sys
import json
import time
import threading
import subprocess
import sqlite3
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich import box
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
# Consolidated functions from getsql.py

# Configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'btt_config.json')
console = Console()

# Consolidated functions from getsql.py
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db')
LOCAL_DB_PATH = os.path.join(DB_DIR, 'sql.db')
DEVICE_DB_PATH = '/data/data/com.bca.bcatrack/cache/cache/data/sql.db'

def run_adb(cmd, timeout=15, capture_output=True):
    """Run ADB command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True, timeout=timeout)
        if result.returncode != 0:
            return None
        return result.stdout.strip() if capture_output else True
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None

def get_connected_device():
    """Get the first connected ADB device"""
    out = run_adb('adb devices')
    if not isinstance(out, str):
        return None
    lines = out.splitlines()
    for line in lines[1:]:
        if line.strip() and ('device' in line and not 'offline' in line):
            return line.split()[0]
    return None

def run_adb_with_root(cmd, device, timeout=10):
    """Run ADB command with root access fallback"""
    # Try non-root first
    try:
        out = run_adb(cmd, timeout=timeout)
        if out is not None and 'Permission denied' not in str(out):
            return out, 'non-root', None
    except Exception as e:
        return None, 'non-root', f"Non-root error: {e}"
    
    # Try su 0 (works on some devices)
    shell_part = cmd.split('shell',1)[1].strip() if 'shell' in cmd else cmd
    su0_cmd = f'adb -s {device} shell su 0 {shell_part}'
    try:
        su0_out = run_adb(su0_cmd, timeout=timeout)
        if su0_out is not None and 'Permission denied' not in str(su0_out):
            return su0_out, 'su0', None
    except Exception as e:
        return None, 'su0', f"Su0 error: {e}"
    
    # Try su -c (works on other devices)
    rootc_cmd = f'adb -s {device} shell su -c "{shell_part}"'
    try:
        rootc_out = run_adb(rootc_cmd, timeout=timeout)
        if rootc_out is not None and 'Permission denied' not in str(rootc_out):
            return rootc_out, 'suc', None
    except Exception as e:
        return None, 'suc', f"RootC error: {e}"
    
    return None, 'all-failed', 'All root forms failed'

def copy_to_sdcard(device, use_root=False):
    """Copy database from device to sdcard"""
    dst = '/sdcard/sql.db'
    if use_root == 'su0':
        copy_cmd = f'adb -s {device} shell su 0 cp {DEVICE_DB_PATH} {dst}'
    elif use_root == 'suc':
        copy_cmd = f'adb -s {device} shell su -c "cp {DEVICE_DB_PATH} {dst}"'
    else:
        copy_cmd = f'adb -s {device} shell cp "{DEVICE_DB_PATH}" "{dst}"'
    out = run_adb(copy_cmd, timeout=15)
    return out is not None

def pull_from_sdcard(device):
    """Pull database from sdcard to local"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    pull_cmd = f'adb -s {device} pull /sdcard/sql.db "{LOCAL_DB_PATH}"'
    out = run_adb(pull_cmd, timeout=30)
    return os.path.exists(LOCAL_DB_PATH)

def extract_sqlite_data_from_device():
    """Main extraction function from getsql.py"""
    try:
        # Check ADB
        if not run_adb('adb version'):
            return "ADB not available"
        
        # Get connected device
        device = get_connected_device()
        if not device:
            return "No ADB device connected"
        
        # Check if database exists on device
        cmd = f'adb -s {device} shell ls -l "{DEVICE_DB_PATH}"'
        out, used_root, err = run_adb_with_root(cmd, device, timeout=10)
        
        if not out or 'No such file' in str(out) or 'Permission denied' in str(out):
            return f"Database not found on device: {err or 'File not accessible'}"
        
        # Copy to sdcard
        if not copy_to_sdcard(device, used_root):
            return "Failed to copy database to sdcard"
        
        # Pull from sdcard
        if not pull_from_sdcard(device):
            return "Failed to pull database from sdcard"
        
        # Clean up sdcard
        cleanup_cmd = f'adb -s {device} shell rm /sdcard/sql.db'
        run_adb(cleanup_cmd, timeout=10)
        
        return "SUCCESS"
        
    except Exception as e:
        return f"Extraction error: {str(e)}"

# Webhook server configuration
WEBHOOK_PORT = 5680
WEBHOOK_HOST = '0.0.0.0'  # Changed from 'localhost' to '0.0.0.0' for Docker access

class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook endpoints"""
    
    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop('manager', None)
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to use our logging system"""
        message = format % args
        if self.manager:
            self.manager.log_webhook(f"HTTP: {message}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            # Log the incoming request
            if self.manager:
                self.manager.log_webhook(f"GET request: {path}")
            
            if path == '/':
                self.serve_web_ui()
            elif path == '/webhook/ui':
                self.serve_web_ui()
            elif path == '/webhook/dwjjob':
                self.serve_dwjjob()
            elif path == '/webhook/dwvveh':
                self.serve_dwvveh()
            elif path == '/healthz':
                self.serve_health()
            elif path == '/status':
                self.serve_status()
            elif path == '/webhook/adb-ips':
                self.serve_adb_ips()
            elif path == '/webhook/load-numbers':
                self.serve_load_numbers()
            elif path == '/network-server.png':
                self.serve_icon()
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            error_msg = f"Webhook GET error: {e}"
            if self.manager:
                self.manager.log_webhook(error_msg)
            console.print(f"[red]{error_msg}[/red]")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_POST(self):
        """Handle POST requests for controls"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            # Log the incoming request
            if self.manager:
                self.manager.log_webhook(f"POST request: {path}")
            
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            if path == '/webhook/control':
                self.handle_control(post_data)
            elif path == '/webhook/adb-ips':
                self.handle_adb_ips(post_data)
            elif path == '/webhook/test-connection':
                self.handle_test_connection(post_data)
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            error_msg = f"Webhook POST error: {e}"
            if self.manager:
                self.manager.log_webhook(error_msg)
            console.print(f"[red]{error_msg}[/red]")
            self.send_error(500, f"Internal server error: {e}")
    
    def handle_control(self, post_data):
        """Handle control commands via webhook"""
        try:
            data = json.loads(post_data)
            action = data.get('action')
            
            if action == 'toggle_auto':
                self.manager.log_webhook(f"DEBUG: Toggle auto-update requested. Current state: {self.manager.config.get('auto_enabled', False)}")
                result = self.manager.toggle_auto_update_webhook()
                self.manager.log_webhook(f"DEBUG: Toggle result: {result}")
                response = {'status': 'success', 'message': 'Auto-update toggled', 'autoEnabled': result.get('autoEnabled', False)}
            elif action == 'set_interval':
                minutes = data.get('minutes', 5)
                self.manager.set_interval(minutes)
                response = {'status': 'success', 'message': f'Interval set to {minutes} minutes'}
            elif action == 'run_extraction':
                extraction_result = self.manager.run_getsql_webhook()
                response = {'status': 'success', 'message': 'SQL extraction finished', 'extractionResult': extraction_result}
            elif action == 'update_status':
                self.manager.update_last_stats()
                response = {'status': 'success', 'message': 'Status updated'}
            elif action == 'set_preferred_device':
                ip = data.get('ip')
                if ip:
                    result = self.manager.set_preferred_device(ip)
                    response = {'status': 'success', 'message': f'Preferred device set to {ip}', 'preferredDeviceName': result}
                else:
                    response = {'status': 'error', 'message': 'IP address required'}
            else:
                response = {'status': 'error', 'message': 'Invalid action'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, f"Control error: {e}")
    
    def handle_adb_ips(self, post_data):
        """Handle ADB IP management via webhook"""
        try:
            data = json.loads(post_data)
            action = data.get('action')
            
            if action == 'add':
                ip = data.get('ip')
                if ip:
                    self.manager.add_adb_ip(ip)
                    response = {'status': 'success', 'message': f'Added IP: {ip}'}
                else:
                    response = {'status': 'error', 'message': 'IP address required'}
            elif action == 'remove':
                ip = data.get('ip')
                if ip:
                    self.manager.remove_adb_ip(ip)
                    response = {'status': 'success', 'message': f'Removed IP: {ip}'}
                else:
                    response = {'status': 'error', 'message': 'IP address required'}
            elif action == 'test_connection':
                ip = data.get('ip')
                if ip:
                    connected = self.manager.test_adb_connection(ip)
                    response = {'status': 'success', 'connected': connected, 'message': f'Connection test for {ip}'}
                else:
                    response = {'status': 'error', 'message': 'IP address required'}
            elif action == 'rename':
                ip = data.get('ip')
                name = data.get('name')
                if ip and name:
                    try:
                        self.manager.rename_adb_device(ip, name)
                        response = {'status': 'success', 'message': f'Renamed device {ip} to {name}'}
                    except Exception as e:
                        response = {'status': 'error', 'message': f'Failed to rename device: {e}'}
                else:
                    response = {'status': 'error', 'message': 'IP and name required for rename'}
            else:
                response = {'status': 'error', 'message': 'Invalid action'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, f"ADB IP error: {e}")
    
    def handle_test_connection(self, post_data):
        """Handle ADB connection testing via webhook"""
        try:
            data = json.loads(post_data)
            ip = data.get('ip')
            
            if ip:
                connected, command_output = self.manager.test_adb_connection(ip)
                response = {
                    'status': 'success', 
                    'connected': connected, 
                    'message': f'Connection test for {ip}',
                    'commandOutput': command_output
                }
            else:
                response = {'status': 'error', 'message': 'IP address required'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, f"Test connection error: {e}")
    
    def serve_dwjjob(self):
        """Serve DWJJOB data as JSON"""
        try:
            data = self.manager.get_dwjjob_data()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Failed to serve DWJJOB data: {e}")
    
    def serve_dwvveh(self):
        """Serve DWVVEH data as JSON"""
        try:
            data = self.manager.get_dwvveh_data()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Failed to serve DWVVEH data: {e}")
    
    def serve_health(self):
        """Serve health check endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
    
    def serve_status(self):
        """Serve status information as JSON"""
        try:
            # Check if manager exists and has required attributes
            if not self.manager:
                self.send_error(500, "Manager not initialized")
                return
                
            # Check ADB device connections with error handling
            adb_ips = []
            any_connected = False
            try:
                adb_ips = self.manager.get_adb_ips()
                for device in adb_ips:
                    ip = device.get('ip', device)
                    try:
                        connected, _ = self.manager.test_adb_connection(ip)
                        if connected:
                            any_connected = True
                            break
                    except Exception as e:
                        self.manager.log_webhook(f"Error testing ADB connection for {ip}: {e}")
            except Exception as e:
                self.manager.log_webhook(f"Error getting ADB IPs: {e}")
            
            # If no ADB device is connected, force auto_enabled to False
            if not any_connected:
                try:
                    self.manager.auto_enabled = False
                    self.manager.config['auto_enabled'] = False
                    self.manager.save_config()
                except Exception as e:
                    self.manager.log_webhook(f"Error updating auto_enabled: {e}")
            
            # Build status with safe attribute access
            status = {
                'autoEnabled': self.manager.config.get('auto_enabled', False),
                'intervalMinutes': self.manager.config.get('interval_minutes', 5),
                'uptime': time.time() - getattr(self.manager, 'start_time', time.time()),
                'lastLocations': self.manager.config.get('last_locations', 0),
                'lastCars': self.manager.config.get('last_cars', 0),
                'lastLoads': self.manager.config.get('last_loads', 0),
                'lastProcessed': self.manager.config.get('last_sql_atime', None),
                'webhookServer': 'Running',
                'timestamp': datetime.now().isoformat(),
                'adbConnected': any_connected,
                'preferredDevice': self.manager.config.get('preferred_device', None)
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
            
        except Exception as e:
            error_msg = f"Status error: {e}"
            if self.manager:
                self.manager.log_webhook(error_msg)
            self.send_error(500, error_msg)
    
    def serve_adb_ips(self):
        """Serve ADB IP list with connection status"""
        try:
            adb_ips = self.manager.get_adb_ips()
            result = []
            for device in adb_ips:
                ip = device.get('ip', device)
                connected, _ = self.manager.test_adb_connection(ip)
                result.append({'ip': ip, 'name': device.get('name', ip), 'connected': connected})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Failed to serve ADB IPs: {e}")

    def serve_load_numbers(self):
        """Serve load numbers as JSON"""
        try:
            data = self.manager.get_load_numbers()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Failed to serve load numbers: {e}")

    def serve_icon(self):
        """Serve the application icon"""
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'network-server.png')
            if os.path.exists(icon_path):
                with open(icon_path, 'rb') as f:
                    icon_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'image/png')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                self.wfile.write(icon_content)
            else:
                self.send_error(404, "Icon file not found")
        except Exception as e:
            self.send_error(500, f"Failed to serve icon: {e}")

    def serve_web_ui(self):
        """Serve the web UI HTML page"""
        try:
            # Read the web UI HTML file
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_ui.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))
            else:
                # Fallback HTML if file doesn't exist
                fallback_html = """
                <!DOCTYPE html>
                <html>
                <head><title>BTT Auto Manager</title></head>
                <body>
                <h1>BTT Auto Manager</h1>
                <p>Web UI file not found. Please check the installation.</p>
                <p><a href="/status">Status</a> | <a href="/healthz">Health</a></p>
                </body>
                </html>
                """
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(fallback_html.encode('utf-8'))
                
        except Exception as e:
            self.send_error(500, f"Failed to serve web UI: {e}")

class BTTAutoManager:
    def __init__(self):
        # Set start_time first before any other operations
        self.start_time = time.time()
        
        self.config = self.load_config()
        self.running = False
        self.last_run = None
        self.last_stats = None
        self.auto_thread = None
        self.webhook_server = None
        self.webhook_thread = None
        self.webhook_logs = []
        self.next_update_time = None
        
        # Initialize attributes from config with safe defaults
        self.auto_enabled = self.config.get('auto_enabled', False)
        self.interval_minutes = self.config.get('interval_minutes', 5)
        self.last_locations = self.config.get('last_locations', 0)
        self.last_cars = self.config.get('last_cars', 0)
        self.last_loads = self.config.get('last_loads', 0)
        self.last_processed = self.config.get('last_sql_atime', None)
        
        self.extracted_data = {
            'DWJJOB': [],
            'DWVVEH': [],
            'lastProcessed': None,
            'processingStatus': 'idle'
        }
        
    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "auto_enabled": False,
            "interval_minutes": 5,
            "last_sql_atime": None,
            "last_locations": 0,
            "last_cars": 0,
            "last_loads": 0,
            "webhook_enabled": True,
            "webhook_port": WEBHOOK_PORT,
            "adb_ips": [],
            "preferred_device": None
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                console.print(f"[red]Error loading config: {e}[/red]")
                return default_config
        else:
            # Create default config file
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Save configuration to JSON file"""
        if config is None:
            config = self.config
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
    
    def add_adb_ip(self, ip):
        """Add ADB IP address to the list"""
        if ip not in [device.get('ip', device) for device in self.config.get('adb_ips', [])]:
            if 'adb_ips' not in self.config:
                self.config['adb_ips'] = []
            # Store as object with ip and name
            self.config['adb_ips'].append({'ip': ip, 'name': f'Device {len(self.config["adb_ips"]) + 1}'})
            self.save_config()
            self.log_webhook(f"Added ADB IP: {ip}")
            console.print(f"[green]Added ADB IP: {ip}[/green]")
    
    def remove_adb_ip(self, ip):
        """Remove ADB IP address from the list"""
        adb_ips = self.config.get('adb_ips', [])
        for i, device in enumerate(adb_ips):
            device_ip = device.get('ip', device) if isinstance(device, dict) else device
            if device_ip == ip:
                self.config['adb_ips'].pop(i)
                self.save_config()
                self.log_webhook(f"Removed ADB IP: {ip}")
                console.print(f"[yellow]Removed ADB IP: {ip}[/yellow]")
            break
    
    def rename_adb_device(self, ip, name):
        """Rename an ADB device"""
        adb_ips = self.config.get('adb_ips', [])
        for device in adb_ips:
            device_ip = device.get('ip', device) if isinstance(device, dict) else device
            if device_ip == ip:
                if isinstance(device, dict):
                    device['name'] = name
                else:
                    # Convert string to dict
                    idx = adb_ips.index(device)
                    adb_ips[idx] = {'ip': device, 'name': name}
                self.save_config()
                self.log_webhook(f"Renamed ADB device {ip} to: {name}")
                console.print(f"[green]Renamed ADB device {ip} to: {name}[/green]")
                break
    
    def set_preferred_device(self, ip):
        """Set the preferred ADB device for extraction"""
        adb_ips = self.config.get('adb_ips', [])
        device_name = None
        
        # Find the device and get its name
        for device in adb_ips:
            device_ip = device.get('ip', device)
            if device_ip == ip:
                device_name = device.get('name', ip) if isinstance(device, dict) else ip
                break
        
        # Set as preferred device
        self.config['preferred_device'] = ip
        self.save_config()
        
        self.log_webhook(f"Set preferred device to: {ip} ({device_name})")
        console.print(f"[green]Set preferred device to: {ip} ({device_name})[/green]")
        
        return device_name
    
    def get_adb_ips(self):
        """Get list of ADB IP addresses with names"""
        adb_ips = self.config.get('adb_ips', [])
        # Convert old format (strings) to new format (objects)
        result = []
        for device in adb_ips:
            if isinstance(device, dict):
                result.append(device)
            else:
                # Old format - convert to new format
                result.append({'ip': device, 'name': f'Device {len(result) + 1}'})
        return result
    
    def try_connect_adb_ips(self):
        """Try to connect to ADB devices using stored IPs"""
        ips = self.config.get('adb_ips', [])
        for device in ips:
            ip = device.get('ip', device)
            try:
                # Try to connect to the IP
                result = subprocess.run(f'adb connect {ip}', shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and 'connected' in result.stdout.lower():
                    self.log_webhook(f"Successfully connected to ADB device: {ip}")
                    console.print(f"[green]Connected to ADB device: {ip}[/green]")
                    return True
            except Exception as e:
                self.log_webhook(f"Failed to connect to {ip}: {e}")
        
        return False
    
    def test_adb_connection(self, ip):
        """Test if an ADB device is connected at the specified IP"""
        command_output = ""
        try:
            # First ping the IP to check if device is reachable
            ping_result = subprocess.run(f'ping -c 1 -W 3 {ip.split(":")[0]}', shell=True, capture_output=True, text=True, timeout=5)
            command_output += f"$ ping -c 1 -W 3 {ip.split(':')[0]}\n"
            command_output += f"Return code: {ping_result.returncode}\n"
            command_output += f"Output: {ping_result.stdout}\n"
            if ping_result.stderr:
                command_output += f"Error: {ping_result.stderr}\n"
            
            if ping_result.returncode != 0:
                self.log_webhook(f"Ping test FAIL for {ip} - device not reachable")
                command_output += f"\n❌ Device is not reachable via ping - Android may be offline or device disconnected\n"
                return False, command_output
            
            command_output += f"\n✅ Device is reachable via ping - proceeding with ADB connection test\n\n"
            
            # Now try to connect to the IP via ADB
            result = subprocess.run(f'adb connect {ip}', shell=True, capture_output=True, text=True, timeout=10)
            command_output += f"$ adb connect {ip}\n"
            command_output += f"Return code: {result.returncode}\n"
            command_output += f"Output: {result.stdout}\n"
            if result.stderr:
                command_output += f"Error: {result.stderr}\n"
            
            if result.returncode == 0 and 'connected' in result.stdout.lower():
                # Now check if the device is actually connected
                devices_result = subprocess.run('adb devices', shell=True, capture_output=True, text=True, timeout=5)
                command_output += f"\n$ adb devices\n"
                command_output += f"Return code: {devices_result.returncode}\n"
                command_output += f"Output: {devices_result.stdout}\n"
                if devices_result.stderr:
                    command_output += f"Error: {devices_result.stderr}\n"
                
                if devices_result.returncode == 0:
                    lines = devices_result.stdout.splitlines()
                    for line in lines[1:]:  # Skip the first line (header)
                        if ip in line and 'device' in line and 'offline' not in line:
                            self.log_webhook(f"ADB connection test PASS for {ip}")
                            command_output += f"\n✅ ADB connection successful - device is online and ready\n"
                            return True, command_output
                
                self.log_webhook(f"ADB connection test FAIL for {ip} - device not found in device list")
                command_output += f"\n❌ ADB connection failed - device not found in device list\n"
                return False, command_output
            else:
                self.log_webhook(f"ADB connection test FAIL for {ip} - connection failed")
                command_output += f"\n❌ ADB connection failed - Android may be offline or ADB not enabled\n"
                return False, command_output
        except Exception as e:
            command_output += f"\nException: {e}\n"
            self.log_webhook(f"ADB connection test ERROR for {ip}: {e}")
            return False, command_output
    
    def log_webhook(self, message):
        """Log webhook activity"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.webhook_logs.append(log_entry)
        # Keep only last 100 log entries
        if len(self.webhook_logs) > 100:
            self.webhook_logs = self.webhook_logs[-100:]
    
    def extract_sqlite_data(self, db_path):
        """Extract data from SQLite database"""
        try:
            if not os.path.exists(db_path):
                self.log_webhook(f"Database file not found: {db_path}")
                return None
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Extract DWJJOB data
            cursor.execute("SELECT * FROM DWJJOB")
            dwjjob_rows = cursor.fetchall()
            
            # Get column names for DWJJOB
            cursor.execute("PRAGMA table_info(DWJJOB)")
            dwjjob_columns = [col[1] for col in cursor.fetchall()]
            
            # Extract DWVVEH data
            cursor.execute("SELECT * FROM DWVVEH")
            dwvveh_rows = cursor.fetchall()
            
            # Get column names for DWVVEH
            cursor.execute("PRAGMA table_info(DWVVEH)")
            dwvveh_columns = [col[1] for col in cursor.fetchall()]
            
            conn.close()
            
            # Convert to list of dictionaries
            dwjjob_data = []
            for row in dwjjob_rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if i < len(dwjjob_columns):
                        row_dict[dwjjob_columns[i]] = value if value is not None else ''
                dwjjob_data.append(row_dict)
            
            dwvveh_data = []
            for row in dwvveh_rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if i < len(dwvveh_columns):
                        row_dict[dwvveh_columns[i]] = value if value is not None else ''
                dwvveh_data.append(row_dict)
            
            self.extracted_data = {
                'DWJJOB': dwjjob_data,
                'DWVVEH': dwvveh_data,
                'lastProcessed': datetime.now().isoformat(),
                'processingStatus': 'processed'
            }
            
            self.log_webhook(f"Extracted {len(dwjjob_data)} DWJJOB records and {len(dwvveh_data)} DWVVEH records")
            return self.extracted_data
            
        except Exception as e:
            self.log_webhook(f"Error extracting SQLite data: {e}")
            self.extracted_data['processingStatus'] = 'error'
            return None
    
    def get_dwjjob_data(self):
        """Get DWJJOB data for webhook"""
        return self.extracted_data.get('DWJJOB', [])
    
    def get_dwvveh_data(self):
        """Get DWVVEH data for webhook"""
        return self.extracted_data.get('DWVVEH', [])
    
    def get_load_numbers(self):
        """Get list of load numbers from DWJJOB data"""
        try:
            dwjjob_data = self.extracted_data.get('DWJJOB', [])
            load_numbers = []
            
            # Extract unique load numbers from DWJJOB data
            seen_loads = set()
            for record in dwjjob_data:
                load_number = record.get('dwjLoad')
                if load_number and load_number not in seen_loads:
                    seen_loads.add(load_number)
                    load_numbers.append({
                        'loadNumber': load_number,
                        'count': sum(1 for r in dwjjob_data if r.get('dwjLoad') == load_number)
                    })
            
            # Sort by load number
            load_numbers.sort(key=lambda x: x['loadNumber'])
            
            return {
                'loadNumbers': load_numbers,
                'totalLoads': len(load_numbers),
                'totalRecords': len(dwjjob_data)
            }
        except Exception as e:
            self.log_webhook(f"Error getting load numbers: {e}")
            return {
                'loadNumbers': [],
                'totalLoads': 0,
                'totalRecords': 0,
                'error': str(e)
            }
    
    def get_status_data(self):
        """Get status data for webhook"""
        now = datetime.now()
        last_processed = self.extracted_data.get('lastProcessed')
        time_since_last_update = None
        time_since_last_update_formatted = None
        next_update_time = self.next_update_time.isoformat() if self.next_update_time else None
        uptime_seconds = time.time() - getattr(self, '_start_time', time.time())
        uptime_formatted = self.format_uptime(uptime_seconds)
        if last_processed:
            try:
                last_time = datetime.fromisoformat(last_processed.replace('Z', '+00:00'))
                time_diff = now - last_time.replace(tzinfo=None)
                time_since_last_update = int(time_diff.total_seconds() * 1000)
                time_since_last_update_formatted = self.format_time_difference(time_diff.total_seconds())
                if not next_update_time and self.config.get('auto_enabled', False):
                    interval_minutes = self.config.get('interval_minutes', 5)
                    next_update_time = (last_time.replace(tzinfo=None) + timedelta(minutes=interval_minutes)).isoformat()
            except:
                pass
        return {
            'status': self.extracted_data.get('processingStatus', 'idle'),
            'lastProcessed': last_processed,
            'timeSinceLastUpdate': time_since_last_update,
            'timeSinceLastUpdateFormatted': time_since_last_update_formatted,
            'nextUpdateTime': next_update_time,
            'dwjjobCount': len(self.extracted_data.get('DWJJOB', [])),
            'dwvvehCount': len(self.extracted_data.get('DWVVEH', [])),
            'serverTime': now.isoformat(),
            'uptime': uptime_seconds,
            'uptimeFormatted': uptime_formatted,
            'webhookEnabled': self.config.get('webhook_enabled', True),
            'webhookPort': self.config.get('webhook_port', WEBHOOK_PORT),
            'autoEnabled': self.config.get('auto_enabled', False),
            'intervalMinutes': self.config.get('interval_minutes', 5),
            'lastLocations': self.config.get('last_locations', 0),
            'lastCars': self.config.get('last_cars', 0),
            'lastLoads': self.config.get('last_loads', 0),
            'adbIps': self.config.get('adb_ips', []),
            'preferredDevice': self.config.get('preferred_device', None)
        }

    def format_uptime(self, seconds):
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        hours = minutes // 60
        minutes = minutes % 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
        days = hours // 24
        hours = hours % 24
        return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"

    def format_time_difference(self, seconds):
        """Format time difference in human readable format"""
        if not seconds:
            return None
        
        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)
        
        if days > 0:
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return f"{int(seconds)} second{'s' if seconds > 1 else ''} ago"
    
    def start_webhook_server(self):
        """Start the webhook server"""
        if self.webhook_server is not None:
            return
        
        try:
            # Create custom handler with manager reference
            def handler_factory(*args, **kwargs):
                return WebhookHandler(*args, manager=self, **kwargs)
            
            host = WEBHOOK_HOST
            port = self.config.get('webhook_port', WEBHOOK_PORT)
            
            console.print(f"[blue]Starting webhook server on {host}:{port}...[/blue]")
            self.log_webhook(f"Attempting to start webhook server on {host}:{port}")
            
            self.webhook_server = HTTPServer((host, port), handler_factory)
            self.webhook_thread = threading.Thread(target=self.webhook_server.serve_forever, daemon=True)
            self.webhook_thread.start()
            
            # Use the existing start_time attribute
            success_msg = f"Webhook server started successfully on http://{host}:{port}"
            self.log_webhook(success_msg)
            console.print(f"[green]{success_msg}[/green]")
            
        except Exception as e:
            error_msg = f"Failed to start webhook server: {e}"
            console.print(f"[red]{error_msg}[/red]")
            self.log_webhook(error_msg)
            import traceback
            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
    
    def stop_webhook_server(self):
        """Stop the webhook server"""
        if self.webhook_server:
            self.webhook_server.shutdown()
            self.webhook_server = None
            self.webhook_thread = None
            self.log_webhook("Webhook server stopped")
            console.print("[yellow]Webhook server stopped[/yellow]")
    
    def update_last_stats(self):
        """Update last known statistics from the database"""
        try:
            db_path = LOCAL_DB_PATH
            if os.path.exists(db_path):
                # Get file stats
                stat = os.stat(db_path)
                atime = datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S')
                
                # Get database counts
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get DWJJOB count
                cursor.execute("SELECT COUNT(*) FROM DWJJOB")
                locations = cursor.fetchone()[0]
                
                # Get DWVVEH count
                cursor.execute("SELECT COUNT(*) FROM DWVVEH")
                cars = cursor.fetchone()[0]
                
                # Get unique loads count
                cursor.execute("SELECT COUNT(DISTINCT dwjLoad) FROM DWJJOB WHERE dwjLoad IS NOT NULL")
                loads = cursor.fetchone()[0]
                
                conn.close()
                
                # Extract data for webhooks
                self.extract_sqlite_data(db_path)
                
                self.config.update({
                    "last_sql_atime": atime,
                    "last_locations": locations,
                    "last_cars": cars,
                    "last_loads": loads
                })
                self.save_config()
                self.last_stats = {'DWJJOB': locations, 'DWVVEH': cars, 'unique_loads': loads}
        except Exception as e:
            console.print(f"[yellow]Warning: Could not update stats: {e}[/yellow]")
    
    def run_getsql(self):
        """Run the SQL extraction process"""
        try:
            console.print("[blue]Running SQL extraction...[/blue]")
            
            # Use the consolidated extraction function
            result = extract_sqlite_data_from_device()
            
            output = {
                'result': result,
                'success': result == "SUCCESS"
            }
            
            if result == "SUCCESS":
                console.print("[green]SQL extraction completed successfully[/green]")
                self.last_run = datetime.now()
                self.update_last_stats()
            else:
                console.print(f"[red]SQL extraction failed: {result}[/red]")
            
            return output
        except Exception as e:
            console.print(f"[red]Error running SQL extraction: {e}[/red]")
            return {'success': False, 'error': str(e)}

    def run_getsql_webhook(self):
        """Run getsql for webhook calls synchronously and return output"""
        self.log_webhook("SQL extraction started via webhook")
        return self.run_getsql()
    
    def toggle_auto_update_webhook(self):
        current_state = self.config.get("auto_enabled", False)
        self.log_webhook(f"DEBUG: toggle_auto_update_webhook called. Current state: {current_state}")
        if current_state:
            self.log_webhook("DEBUG: Stopping auto-update...")
            self.stop_auto_update()
            new_state = self.config.get('auto_enabled', False)
            self.log_webhook(f"DEBUG: Auto-update toggled via webhook: {'enabled' if new_state else 'disabled'}")
            self.log_webhook(f"DEBUG: Config after toggle: {self.config.get('auto_enabled', False)}")
            return {'success': True, 'status': 'success', 'autoEnabled': new_state}
        else:
            # Only allow toggling ON if an ADB device is connected
            adb_ips = self.get_adb_ips()
            any_connected = False
            for device in adb_ips:
                ip = device.get('ip', device)
                try:
                    connected, _ = self.test_adb_connection(ip)
                    if connected:
                        any_connected = True
                        break
                except Exception as e:
                    self.log_webhook(f"Error testing ADB connection for {ip}: {e}")
            if not any_connected:
                self.log_webhook("DEBUG: Cannot enable auto-update, no ADB device connected.")
                return {'success': False, 'status': 'error', 'error': 'No ADB device connected. Cannot enable auto-update.'}
            self.log_webhook("DEBUG: Starting auto-update...")
            self.start_auto_update()
            new_state = self.config.get('auto_enabled', False)
            self.log_webhook(f"DEBUG: Auto-update toggled via webhook: {'enabled' if new_state else 'disabled'}")
            self.log_webhook(f"DEBUG: Config after toggle: {self.config.get('auto_enabled', False)}")
            return {'success': True, 'status': 'success', 'autoEnabled': new_state}
    
    def auto_update_loop(self):
        """Main loop for auto-updating"""
        self.log_webhook(f"DEBUG: auto_update_loop started. running={self.running}, auto_enabled={self.config.get('auto_enabled', False)}")
        while self.running:
            try:
                auto_enabled = self.config.get("auto_enabled", False)
                self.log_webhook(f"DEBUG: auto_update_loop check. running={self.running}, auto_enabled={auto_enabled}")
                if not auto_enabled:
                    self.log_webhook("DEBUG: Auto-update disabled, breaking loop")
                    break
                
                # Try to connect to ADB devices if needed
                if not get_connected_device():
                    connected = self.try_connect_adb_ips()
                    if not connected:
                        msg = "[yellow]No ADB device connected. Retrying in 60 seconds...[/yellow]"
                        self.log_webhook("No ADB device connected. Retrying in 60 seconds...")
                        console.print(msg)
                        time.sleep(60)
                        continue
                
                # Run getsql
                self.run_getsql()
                
                # Set next update time
                interval_seconds = self.config.get("interval_minutes", 5) * 60
                self.next_update_time = datetime.now() + timedelta(seconds=interval_seconds)
                self.log_webhook(f"DEBUG: Next update scheduled for {self.next_update_time}")
                time.sleep(interval_seconds)
                
            except Exception as e:
                console.print(f"[red]Auto-update error: {e}[/red]")
                self.log_webhook(f"DEBUG: Exception in auto_update_loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
        self.running = False
        self.log_webhook("DEBUG: auto_update_loop exited, running set to False")
    
    def start_auto_update(self):
        """Start the auto-update thread"""
        self.log_webhook(f"DEBUG: start_auto_update called. running={self.running}")
        if self.running:
            self.log_webhook("DEBUG: start_auto_update - already running, skipping")
            return
        self.running = True
        self.config["auto_enabled"] = True
        self.save_config()
        self.log_webhook(f"DEBUG: start_auto_update - config saved. auto_enabled={self.config.get('auto_enabled', False)}")
        self.auto_thread = threading.Thread(target=self.auto_update_loop, daemon=True)
        self.auto_thread.start()
        console.print("[green]Auto-update started[/green]")
        self.log_webhook("DEBUG: Auto-update thread started")
    
    def stop_auto_update(self):
        """Stop the auto-update thread"""
        self.log_webhook(f"DEBUG: stop_auto_update called. running={self.running}")
        self.running = False
        self.config["auto_enabled"] = False
        self.save_config()
        self.log_webhook(f"DEBUG: stop_auto_update - config saved. auto_enabled={self.config.get('auto_enabled', False)}")
        if self.auto_thread and self.auto_thread.is_alive():
            self.auto_thread.join(timeout=5)
            self.log_webhook("DEBUG: Auto-update thread joined")
        self.next_update_time = None
        console.print("[yellow]Auto-update stopped[/yellow]")
        self.log_webhook("DEBUG: Auto-update stopped")
    
    def set_interval(self, minutes):
        """Set the update interval"""
        if minutes < 1:
            minutes = 1
        elif minutes > 1440:  # 24 hours
            minutes = 1440
            
        self.config["interval_minutes"] = minutes
        self.save_config()
        console.print(f"[green]Update interval set to {minutes} minutes[/green]")
    
    def toggle_webhook(self):
        """Toggle webhook server on/off"""
        if self.webhook_server:
            self.stop_webhook_server()
            self.config["webhook_enabled"] = False
        else:
            self.start_webhook_server()
            self.config["webhook_enabled"] = True
        self.save_config()
    
    def create_status_display(self):
        """Create the status display"""
        # Status panel
        status_text = Text()
        status_text.append("Auto-Update Status\n\n", style="bold")
        
        if self.config.get("auto_enabled", False):
            status_text.append("🟢 ENABLED\n", style="green")
        else:
            status_text.append("🔴 DISABLED\n", style="red")
        
        status_text.append(f"Interval: {self.config.get('interval_minutes', 5)} minutes\n")
        
        if self.last_run:
            status_text.append(f"Last Run: {self.last_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
        else:
            status_text.append("Last Run: Never\n")
        
        # ADB IPs
        status_text.append("\nADB IP Addresses:\n", style="bold")
        ips = self.config.get('adb_ips', [])
        if ips:
            for device in ips:
                ip = device.get('ip', device)
                name = device.get('name', ip)
                status_text.append(f"  {name} ({ip})\n")
        else:
            status_text.append("  None configured\n")
        
        # Webhook status
        status_text.append("\nWebhook Server:\n", style="bold")
        if self.webhook_server:
            status_text.append("🟢 RUNNING\n", style="green")
            status_text.append(f"URL: http://{WEBHOOK_HOST}:{self.config.get('webhook_port', WEBHOOK_PORT)}\n")
            status_text.append("Endpoints:\n")
            status_text.append("  /webhook/dwjjob - DWJJOB data\n")
            status_text.append("  /webhook/dwvveh - DWVVEH data\n")
            status_text.append("  /webhook/control - Control system\n")
            status_text.append("  /webhook/adb-ips - Manage ADB IPs\n")
            status_text.append("  /status - Server status\n")
            status_text.append("  /healthz - Health check\n")
        else:
            status_text.append("🔴 STOPPED\n", style="red")
        
        # Last SQL info
        status_text.append("\nLast SQL Database:\n", style="bold")
        atime = self.config.get("last_sql_atime", "Never")
        status_text.append(f"  Last Modified: {atime}\n")
        status_text.append(f"  Locations: {self.config.get('last_locations', 0)}\n")
        status_text.append(f"  Cars: {self.config.get('last_cars', 0)}\n")
        status_text.append(f"  Loads: {self.config.get('last_loads', 0)}\n")
        
        return Panel(status_text, title="BTT Auto Manager", style="blue")
    
    def show_menu(self):
        """Show the main menu"""
        while True:
            console.clear()
            console.print(self.create_status_display())
            
            # Menu options
            menu_table = Table(box=box.SIMPLE, title="Menu Options")
            menu_table.add_column("Option", style="bold")
            menu_table.add_column("Description")
            
            menu_table.add_row("1", "Toggle Auto-Update")
            menu_table.add_row("2", "Set Update Interval")
            menu_table.add_row("3", "Run SQL Extraction Now")
            menu_table.add_row("4", "Update Status")
            menu_table.add_row("5", "Toggle Webhook Server")
            menu_table.add_row("6", "Show Webhook Logs")
            menu_table.add_row("7", "Manage ADB IP Addresses")
            menu_table.add_row("8", "Exit")
            
            console.print(menu_table)
            
            choice = console.input("\n[bold]Select option (1-8): [/bold]").strip()
            
            if choice == "1":
                self.toggle_auto_update()
            elif choice == "2":
                self.set_interval_menu()
            elif choice == "3":
                self.run_getsql()
                console.input("\nPress Enter to continue...")
            elif choice == "4":
                self.update_last_stats()
                console.print("[green]Status updated[/green]")
                console.input("\nPress Enter to continue...")
            elif choice == "5":
                self.toggle_webhook()
                console.input("\nPress Enter to continue...")
            elif choice == "6":
                self.show_webhook_logs()
            elif choice == "7":
                self.manage_adb_ips()
            elif choice == "8":
                if self.running:
                    self.stop_auto_update()
                if self.webhook_server:
                    self.stop_webhook_server()
                console.print("[blue]Goodbye![/blue]")
                break
            else:
                console.print("[red]Invalid option. Please try again.[/red]")
                console.input("\nPress Enter to continue...")
    
    def toggle_auto_update(self):
        """Toggle auto-update on/off"""
        if self.config.get("auto_enabled", False):
            self.stop_auto_update()
        else:
            self.start_auto_update()
        console.input("\nPress Enter to continue...")
    
    def set_interval_menu(self):
        """Menu for setting update interval"""
        console.print("\n[bold]Set Update Interval[/bold]")
        console.print("Enter interval in minutes (1-1440):")
        
        try:
            minutes = int(console.input("Minutes: ").strip())
            self.set_interval(minutes)
        except ValueError:
            console.print("[red]Invalid input. Please enter a number.[/red]")
        
        console.input("\nPress Enter to continue...")
    
    def manage_adb_ips(self):
        """Menu for managing ADB IP addresses"""
        while True:
            console.clear()
            console.print("[bold]ADB IP Address Management[/bold]\n")
            
            ips = self.config.get('adb_ips', [])
            if ips:
                console.print("Current ADB IP addresses:")
                for i, device in enumerate(ips, 1):
                    ip = device.get('ip', device)
                    name = device.get('name', ip)
                    console.print(f"  {i}. {name} ({ip})")
            else:
                console.print("[yellow]No ADB IP addresses configured[/yellow]")
            
            console.print("\nOptions:")
            console.print("1. Add IP address")
            console.print("2. Remove IP address")
            console.print("3. Test connections")
            console.print("4. Back to main menu")
            
            choice = console.input("\n[bold]Select option (1-4): [/bold]").strip()
            
            if choice == "1":
                ip = console.input("Enter IP address (e.g., 192.168.1.100:5555): ").strip()
                if ip:
                    self.add_adb_ip(ip)
                console.input("\nPress Enter to continue...")
            elif choice == "2":
                if ips:
                    try:
                        idx = int(console.input("Enter number to remove: ").strip()) - 1
                        if 0 <= idx < len(ips):
                            ip_to_remove = ips[idx].get('ip', ips[idx])
                            self.remove_adb_ip(ip_to_remove)
                        else:
                            console.print("[red]Invalid number[/red]")
                    except ValueError:
                        console.print("[red]Invalid input[/red]")
                else:
                    console.print("[yellow]No IPs to remove[/yellow]")
                console.input("\nPress Enter to continue...")
            elif choice == "3":
                console.print("[blue]Testing ADB connections...[/blue]")
                if self.try_connect_adb_ips():
                    console.print("[green]Successfully connected to at least one device[/green]")
                else:
                    console.print("[red]Failed to connect to any devices[/red]")
                console.input("\nPress Enter to continue...")
            elif choice == "4":
                break
            else:
                console.print("[red]Invalid option[/red]")
                console.input("\nPress Enter to continue...")
    
    def show_webhook_logs(self):
        """Show recent webhook logs"""
        console.clear()
        console.print("[bold]Recent Webhook Logs[/bold]\n")
        
        if not self.webhook_logs:
            console.print("[yellow]No webhook logs available[/yellow]")
        else:
            for log_entry in self.webhook_logs[-20:]:  # Show last 20 entries
                console.print(log_entry)
        
        console.input("\nPress Enter to continue...")

def main():
    """Main function"""
    console.print("[bold blue]BTT Auto Manager[/bold blue]")
    console.print("Automated SQL Database Extraction Tool with Webhooks\n")
    
    try:
        # Initialize manager
        console.print("[blue]Initializing manager...[/blue]")
        manager = BTTAutoManager()
        
        # Update initial status
        console.print("[blue]Updating initial status...[/blue]")
        manager.update_last_stats()
        
        # Start webhook server if enabled
        console.print("[blue]Starting webhook server...[/blue]")
        if manager.config.get("webhook_enabled", True):
            manager.start_webhook_server()
            console.print("[green]Webhook server started successfully[/green]")
        else:
            console.print("[yellow]Webhook server disabled[/yellow]")
        
        # Check if running in non-interactive mode (Docker container)
        import sys
        if not sys.stdin.isatty():
            console.print("[yellow]Running in non-interactive mode (Docker container)[/yellow]")
            console.print("[green]Webhook server started[/green]")
            console.print(f"[green]Available at: http://localhost:{manager.config.get('webhook_port', WEBHOOK_PORT)}[/green]")
            
            # Start auto-update if enabled
            if manager.config.get("auto_enabled", False):
                console.print("[blue]Starting auto-update...[/blue]")
                manager.start_auto_update()
                console.print("[green]Auto-update started[/green]")
            else:
                console.print("[yellow]Auto-update disabled[/yellow]")
            
            # Always keep the process alive in Docker
            console.print("[blue]Entering main loop...[/blue]")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutting down...[/yellow]")
                if manager.running:
                    manager.stop_auto_update()
                if manager.webhook_server:
                    manager.stop_webhook_server()
        else:
            # Interactive mode - show menu
            console.print("[blue]Starting interactive menu...[/blue]")
            manager.show_menu()
            
    except Exception as e:
        console.print(f"[red]Error in main function: {e}[/red]")
        import traceback
        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        raise

if __name__ == "__main__":
    main() 
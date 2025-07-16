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
import getsql

# Configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'btt_config.json')
console = Console()

# Webhook server configuration
WEBHOOK_PORT = 5680
WEBHOOK_HOST = 'localhost'

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
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            if self.manager:
                self.manager.log_webhook(f"Webhook error: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def do_POST(self):
        """Handle POST requests for controls"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            if path == '/webhook/control':
                self.handle_control(post_data)
            elif path == '/webhook/adb-ips':
                self.handle_adb_ips(post_data)
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            if self.manager:
                self.manager.log_webhook(f"Webhook POST error: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def handle_control(self, post_data):
        """Handle control commands via webhook"""
        try:
            data = json.loads(post_data)
            action = data.get('action')
            
            if action == 'toggle_auto':
                self.manager.toggle_auto_update_webhook()
                response = {'status': 'success', 'message': 'Auto-update toggled'}
            elif action == 'set_interval':
                minutes = data.get('minutes', 5)
                self.manager.set_interval(minutes)
                response = {'status': 'success', 'message': f'Interval set to {minutes} minutes'}
            elif action == 'run_now':
                self.manager.run_getsql_webhook()
                response = {'status': 'success', 'message': 'SQL extraction started'}
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
        """Serve status endpoint"""
        try:
            status_data = self.manager.get_status_data()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status_data, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Failed to serve status: {e}")
    
    def serve_adb_ips(self):
        """Serve ADB IP list"""
        try:
            ips = self.manager.get_adb_ips()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(ips, indent=2).encode())
        except Exception as e:
            self.send_error(500, f"Failed to serve ADB IPs: {e}")

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
        self.config = self.load_config()
        self.running = False
        self.last_run = None
        self.last_stats = None
        self.auto_thread = None
        self.webhook_server = None
        self.webhook_thread = None
        self.webhook_logs = []
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
            "adb_ips": []
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
        if ip not in self.config.get('adb_ips', []):
            if 'adb_ips' not in self.config:
                self.config['adb_ips'] = []
            self.config['adb_ips'].append(ip)
            self.save_config()
            self.log_webhook(f"Added ADB IP: {ip}")
            console.print(f"[green]Added ADB IP: {ip}[/green]")
    
    def remove_adb_ip(self, ip):
        """Remove ADB IP address from the list"""
        if ip in self.config.get('adb_ips', []):
            self.config['adb_ips'].remove(ip)
            self.save_config()
            self.log_webhook(f"Removed ADB IP: {ip}")
            console.print(f"[yellow]Removed ADB IP: {ip}[/yellow]")
    
    def get_adb_ips(self):
        """Get list of ADB IP addresses"""
        return self.config.get('adb_ips', [])
    
    def try_connect_adb_ips(self):
        """Try to connect to ADB devices using stored IPs"""
        ips = self.config.get('adb_ips', [])
        for ip in ips:
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
    
    def get_status_data(self):
        """Get status data for webhook"""
        now = datetime.now()
        last_processed = self.extracted_data.get('lastProcessed')
        
        time_since_last_update = None
        time_since_last_update_formatted = None
        
        if last_processed:
            try:
                last_time = datetime.fromisoformat(last_processed.replace('Z', '+00:00'))
                time_diff = now - last_time.replace(tzinfo=None)
                time_since_last_update = int(time_diff.total_seconds() * 1000)
                time_since_last_update_formatted = self.format_time_difference(time_diff.total_seconds())
            except:
                pass
        
        return {
            'status': self.extracted_data.get('processingStatus', 'idle'),
            'lastProcessed': last_processed,
            'timeSinceLastUpdate': time_since_last_update,
            'timeSinceLastUpdateFormatted': time_since_last_update_formatted,
            'dwjjobCount': len(self.extracted_data.get('DWJJOB', [])),
            'dwvvehCount': len(self.extracted_data.get('DWVVEH', [])),
            'serverTime': now.isoformat(),
            'uptime': time.time() - getattr(self, '_start_time', time.time()),
            'webhookEnabled': self.config.get('webhook_enabled', True),
            'webhookPort': self.config.get('webhook_port', WEBHOOK_PORT),
            'autoEnabled': self.config.get('auto_enabled', False),
            'intervalMinutes': self.config.get('interval_minutes', 5),
            'lastLocations': self.config.get('last_locations', 0),
            'lastCars': self.config.get('last_cars', 0),
            'lastLoads': self.config.get('last_loads', 0),
            'adbIps': self.config.get('adb_ips', [])
        }
    
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
            
            self.webhook_server = HTTPServer((WEBHOOK_HOST, self.config.get('webhook_port', WEBHOOK_PORT)), handler_factory)
            self.webhook_thread = threading.Thread(target=self.webhook_server.serve_forever, daemon=True)
            self.webhook_thread.start()
            
            self._start_time = time.time()
            self.log_webhook(f"Webhook server started on http://{WEBHOOK_HOST}:{self.config.get('webhook_port', WEBHOOK_PORT)}")
            console.print(f"[green]Webhook server started on http://{WEBHOOK_HOST}:{self.config.get('webhook_port', WEBHOOK_PORT)}[/green]")
            
        except Exception as e:
            console.print(f"[red]Failed to start webhook server: {e}[/red]")
            self.log_webhook(f"Failed to start webhook server: {e}")
    
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
            db_path = getsql.LOCAL_DB_PATH
            if os.path.exists(db_path):
                # Get file stats
                stat = os.stat(db_path)
                atime = datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S')
                
                # Get database counts
                counts, _ = getsql.get_db_counts(db_path)
                
                # Extract data for webhooks
                self.extract_sqlite_data(db_path)
                
                self.config.update({
                    "last_sql_atime": atime,
                    "last_locations": counts.get('DWJJOB', 0),
                    "last_cars": counts.get('DWVVEH', 0),
                    "last_loads": counts.get('unique_loads', 0)
                })
                self.save_config()
                self.last_stats = counts
        except Exception as e:
            console.print(f"[yellow]Warning: Could not update stats: {e}[/yellow]")
    
    def run_getsql(self):
        """Run the getsql program"""
        try:
            console.print("[blue]Running SQL extraction...[/blue]")
            result = subprocess.run([sys.executable, 'getsql.py'], 
                                  capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode == 0:
                console.print("[green]SQL extraction completed successfully[/green]")
                self.last_run = datetime.now()
                self.update_last_stats()
            else:
                console.print(f"[red]SQL extraction failed: {result.stderr}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error running getsql: {e}[/red]")
    
    def run_getsql_webhook(self):
        """Run getsql for webhook calls"""
        try:
            self.log_webhook("SQL extraction started via webhook")
            # Run in a separate thread to avoid blocking
            thread = threading.Thread(target=self.run_getsql, daemon=True)
            thread.start()
        except Exception as e:
            self.log_webhook(f"Error starting SQL extraction via webhook: {e}")
    
    def toggle_auto_update_webhook(self):
        """Toggle auto-update for webhook calls"""
        if self.config.get("auto_enabled", False):
            self.stop_auto_update()
        else:
            self.start_auto_update()
        self.log_webhook(f"Auto-update toggled via webhook: {'enabled' if self.config.get('auto_enabled', False) else 'disabled'}")
    
    def auto_update_loop(self):
        """Main loop for auto-updating"""
        while self.running:
            try:
                # Check if auto is still enabled
                if not self.config.get("auto_enabled", False):
                    break

                # Try to connect to ADB devices if needed
                if not getsql.get_connected_device():
                    connected = self.try_connect_adb_ips()
                    if not connected:
                        msg = "[yellow]No ADB device connected. Retrying in 60 seconds...[/yellow]"
                        self.log_webhook("No ADB device connected. Retrying in 60 seconds...")
                        console.print(msg)
                        time.sleep(60)
                        continue

                # Run getsql
                self.run_getsql()

                # Wait for next interval
                interval_seconds = self.config.get("interval_minutes", 5) * 60
                time.sleep(interval_seconds)

            except Exception as e:
                console.print(f"[red]Auto-update error: {e}[/red]")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def start_auto_update(self):
        """Start the auto-update thread"""
        if not self.running:
            self.running = True
            self.config["auto_enabled"] = True
            self.save_config()
            self.auto_thread = threading.Thread(target=self.auto_update_loop, daemon=True)
            self.auto_thread.start()
            console.print("[green]Auto-update started[/green]")
    
    def stop_auto_update(self):
        """Stop the auto-update thread"""
        self.running = False
        self.config["auto_enabled"] = False
        self.save_config()
        if self.auto_thread and self.auto_thread.is_alive():
            self.auto_thread.join(timeout=5)
        console.print("[yellow]Auto-update stopped[/yellow]")
    
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
            for ip in ips:
                status_text.append(f"  {ip}\n")
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
                for i, ip in enumerate(ips, 1):
                    console.print(f"  {i}. {ip}")
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
                            self.remove_adb_ip(ips[idx])
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
    
    # Initialize manager
    manager = BTTAutoManager()
    
    # Update initial status
    manager.update_last_stats()
    
    # Start webhook server if enabled
    if manager.config.get("webhook_enabled", True):
        manager.start_webhook_server()
    
    # Check if running in non-interactive mode (Docker container)
    import sys
    if not sys.stdin.isatty():
        console.print("[yellow]Running in non-interactive mode (Docker container)[/yellow]")
        console.print("[green]Webhook server started[/green]")
        console.print(f"[green]Available at: http://localhost:{manager.config.get('webhook_port', WEBHOOK_PORT)}[/green]")
        
        # Start auto-update if enabled
        if manager.config.get("auto_enabled", False):
            manager.start_auto_update()
            console.print("[green]Auto-update started[/green]")
        else:
            console.print("[yellow]Auto-update disabled[/yellow]")
        
        # Always keep the process alive in Docker
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
        manager.show_menu()

if __name__ == "__main__":
    main() 
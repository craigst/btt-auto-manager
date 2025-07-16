import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || window.location.origin;

function App() {
  const [status, setStatus] = useState(null);
  const [sqlData, setSqlData] = useState({ dwjjob: [], dwvveh: [] });
  const [adbIPs, setAdbIPs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [newIP, setNewIP] = useState('');
  const [updateInterval, setUpdateInterval] = useState(5);
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(false);
  const [extractionModalOpen, setExtractionModalOpen] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);

  // Utility functions
  const apiCall = async (endpoint, method = 'GET', data = null) => {
    try {
      const options = {
        method: method,
        headers: {
          'Content-Type': 'application/json',
        }
      };
      
      if (data) {
        options.body = JSON.stringify(data);
      }
      
      const response = await fetch(`${API_BASE}${endpoint}`, options);
      return await response.json();
    } catch (error) {
      console.error('API call failed:', error);
      return { error: error.message };
    }
  };

  const showMessage = (msg, type = 'success') => {
    setMessage({ text: msg, type });
    setTimeout(() => setMessage(null), 5000);
  };

  // Data fetching functions
  const fetchStatus = async () => {
    try {
      const data = await apiCall('/status');
      if (data.error) {
        setError(`Error loading status: ${data.error}`);
        return;
      }
      setStatus(data);
      setAutoUpdateEnabled(data.autoEnabled || false);
      setUpdateInterval(data.intervalMinutes || 5);
      setError(null);
    } catch (error) {
      setError(`Error loading status: ${error.message}`);
    }
  };

  const fetchSQLData = async () => {
    try {
      const [dwjjob, dwvveh] = await Promise.all([
        apiCall('/webhook/dwjjob'),
        apiCall('/webhook/dwvveh')
      ]);
      
      setSqlData({
        dwjjob: dwjjob.error ? [] : dwjjob,
        dwvveh: dwvveh.error ? [] : dwvveh
      });
    } catch (error) {
      console.error('Error loading SQL data:', error);
    }
  };

  const fetchADBIPs = async () => {
    try {
      const data = await apiCall('/webhook/adb-ips');
      if (data.error) {
        setError(`Error loading ADB IPs: ${data.error}`);
        return;
      }
      setAdbIPs(Array.isArray(data) ? data : []);
      setError(null);
    } catch (error) {
      setError(`Error loading ADB IPs: ${error.message}`);
    }
  };

  // Control functions
  const toggleAutoUpdate = async () => {
    const result = await apiCall('/webhook/control', 'POST', {
      action: 'toggle_auto'
    });
    
    if (result.error) {
      showMessage(`Error: ${result.error}`, 'error');
    } else {
      showMessage('Auto-update toggled successfully');
      fetchStatus();
    }
  };

  const setInterval = async () => {
    const minutes = parseInt(updateInterval);
    if (isNaN(minutes) || minutes < 1 || minutes > 1440) {
      showMessage('Please enter a valid interval between 1 and 1440 minutes', 'error');
      return;
    }
    
    const result = await apiCall('/webhook/control', 'POST', {
      action: 'set_interval',
      minutes: minutes
    });
    
    if (result.error) {
      showMessage(`Error: ${result.error}`, 'error');
    } else {
      showMessage(`Update interval set to ${minutes} minutes`);
      fetchStatus();
    }
  };

  const runExtraction = async () => {
    const result = await apiCall('/webhook/control', 'POST', {
      action: 'run_extraction'
    });
    
    if (result.error) {
      showMessage(`Error: ${result.error}`, 'error');
    } else {
      setExtractionResult(result.extractionResult || { message: result.message });
      setExtractionModalOpen(true);
      setTimeout(() => {
        fetchStatus();
        fetchSQLData();
      }, 5000);
    }
  };

  const addADBIP = async () => {
    if (!newIP.trim()) {
      showMessage('Please enter an IP address', 'error');
      return;
    }
    
    const result = await apiCall('/webhook/adb-ips', 'POST', {
      action: 'add',
      ip: newIP.trim()
    });
    
    if (result.error) {
      showMessage(`Error adding IP: ${result.error}`, 'error');
    } else {
      showMessage(`Successfully added IP: ${newIP}`);
      setNewIP('');
      fetchADBIPs();
    }
  };

  const removeADBIP = async (ip) => {
    if (!window.confirm(`Are you sure you want to remove ${ip}?`)) {
      return;
    }
    
    const result = await apiCall('/webhook/adb-ips', 'POST', {
      action: 'remove',
      ip: ip
    });
    
    if (result.error) {
      showMessage(`Error removing IP: ${result.error}`, 'error');
    } else {
      showMessage(`Successfully removed IP: ${ip}`);
      fetchADBIPs();
    }
  };

  const testConnection = async (ip) => {
    const result = await apiCall('/webhook/test-connection', 'POST', {
      ip: ip
    });
    
    if (result.error) {
      showMessage(`Connection test failed: ${result.error}`, 'error');
    } else {
      showMessage(`Connection test ${result.connected ? 'PASSED' : 'FAILED'} for ${ip}`);
      fetchADBIPs(); // Refresh the list to show updated status
    }
  };

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchStatus(),
        fetchSQLData(),
        fetchADBIPs()
      ]);
      setLoading(false);
    };
    
    loadData();
  }, []);

  // Auto-refresh status every 30 seconds (without flashing)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStatus();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading BTT Auto Manager...</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <h1>🚛 BTT Auto Manager</h1>
        <p>SQL Database Extraction & ADB Management</p>
      </div>
      
      <div className="content">
        {message && (
          <div className={`message ${message.type}`}>
            {message.text}
          </div>
        )}
        
        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {/* System Status Section */}
        <div className="section">
          <h2>📊 System Status 
            <button className="refresh-btn" onClick={fetchStatus}>
              🔄 Refresh
            </button>
          </h2>
          
          {status && (
            <div className="status-grid">
              <div className="status-card">
                <h3>Auto-Update Status</h3>
                <div className={`status-value ${status.autoEnabled ? 'status-online' : 'status-offline'}`}>
                  {status.autoEnabled ? '🟢 Enabled' : '🔴 Disabled'}
                </div>
              </div>
              <div className="status-card">
                <h3>Webhook Server</h3>
                <div className="status-value status-online">🟢 Running</div>
              </div>
              <div className="status-card">
                <h3>Update Interval</h3>
                <div className="status-value">{status.intervalMinutes || 5} minutes</div>
              </div>
              <div className="status-card">
                <h3>Server Uptime</h3>
                <div className="status-value">{Math.round(status.uptime || 0)} seconds</div>
              </div>
            </div>
          )}
          
          {status && (
            <div className="status-card">
              <h3>Database Statistics</h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Last Updated</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Locations</td>
                    <td>{status.lastLocations || 0}</td>
                    <td>{status.lastProcessed || 'Never'}</td>
                  </tr>
                  <tr>
                    <td>Cars</td>
                    <td>{status.lastCars || 0}</td>
                    <td>{status.lastProcessed || 'Never'}</td>
                  </tr>
                  <tr>
                    <td>Loads</td>
                    <td>{status.lastLoads || 0}</td>
                    <td>{status.lastProcessed || 'Never'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* SQL Data Section */}
        <div className="section">
          <h2>🗄️ SQL Database Data 
            <button className="refresh-btn" onClick={fetchSQLData}>
              🔄 Refresh
            </button>
          </h2>
          
          <div className="status-grid">
            <div className="status-card">
              <h3>DWJJOB Data ({sqlData.dwjjob.length} records)</h3>
              <div className="status-value">{sqlData.dwjjob.length} locations</div>
              {sqlData.dwjjob.length > 0 && (
                <button className="button" onClick={() => alert('View DWJJOB data functionality')}>
                  View Details
                </button>
              )}
            </div>
            <div className="status-card">
              <h3>DWVVEH Data ({sqlData.dwvveh.length} records)</h3>
              <div className="status-value">{sqlData.dwvveh.length} vehicles</div>
              {sqlData.dwvveh.length > 0 && (
                <button className="button" onClick={() => alert('View DWVVEH data functionality')}>
                  View Details
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ADB Device Management Section */}
        <div className="section">
          <h2>📱 ADB Device Management 
            <button className="refresh-btn" onClick={fetchADBIPs}>
              🔄 Refresh
            </button>
          </h2>
          
          <div className="status-card">
            <h3>Configured ADB IP Addresses</h3>
            
            {adbIPs.length === 0 ? (
              <p>No ADB IP addresses configured</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Connection Status</th>
                    <th>Test Result</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {adbIPs.map((entry, index) => {
                    const ip = entry.ip || entry;
                    const connected = entry.connected === true;
                    return (
                      <tr key={index}>
                        <td>{ip}</td>
                        <td>
                          <span className={`connection-status ${connected ? 'connection-connected' : 'connection-disconnected'}`}>
                            {connected ? 'Connected' : 'Disconnected'}
                          </span>
                        </td>
                        <td>{connected ? 'PASS' : 'FAIL'}</td>
                        <td>
                          <button className="button danger" onClick={() => removeADBIP(ip)}>
                            Remove
                          </button>
                          <button className="button warning" onClick={() => testConnection(ip)}>
                            Test
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          
          <div className="input-group">
            <label htmlFor="new-ip">Add New ADB IP:</label>
            <input
              type="text"
              id="new-ip"
              value={newIP}
              onChange={(e) => setNewIP(e.target.value)}
              placeholder="192.168.1.100:5555"
            />
            <button className="button success" onClick={addADBIP}>
              Add IP
            </button>
          </div>
        </div>

        {/* Control Section */}
        <div className="section">
          <h2>⚙️ System Controls</h2>
          
          <div className="status-grid">
            <div className="status-card">
              <h3>Auto-Update Settings</h3>
              <div className="input-group">
                <label>Auto-Update Status:</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={autoUpdateEnabled}
                      onChange={toggleAutoUpdate}
                    />
                    <span className="slider"></span>
                  </label>
                  <span>{autoUpdateEnabled ? 'Enabled' : 'Disabled'}</span>
                </div>
              </div>
              <div className="input-group">
                <label htmlFor="update-interval">Update Interval (minutes):</label>
                <input
                  type="number"
                  id="update-interval"
                  value={updateInterval}
                  onChange={(e) => setUpdateInterval(e.target.value)}
                  min="1"
                  max="1440"
                />
                <button className="button" onClick={setInterval}>
                  Set Interval
                </button>
              </div>
            </div>
            
            <div className="status-card">
              <h3>Manual Controls</h3>
              <button className="button" onClick={runExtraction}>
                Run Extraction Now
              </button>
              <button className="button" onClick={fetchStatus}>
                Update Status
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* Extraction Result Modal */}
      {extractionModalOpen && (
        <div className="modal-overlay" onClick={() => setExtractionModalOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>SQL Extraction Result</h2>
            {extractionResult && (
              <div style={{ maxHeight: '60vh', overflowY: 'auto', textAlign: 'left', fontSize: '0.95em' }}>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {extractionResult.success === true ? '✅ Extraction Succeeded\n' : ''}
                  {extractionResult.success === false ? '❌ Extraction Failed\n' : ''}
                  {extractionResult.stdout ? `\n[stdout]\n${extractionResult.stdout}` : ''}
                  {extractionResult.stderr ? `\n[stderr]\n${extractionResult.stderr}` : ''}
                  {extractionResult.log ? `\n[getsql.log]\n${extractionResult.log}` : ''}
                  {extractionResult.error ? `\n[error]\n${extractionResult.error}` : ''}
                  {extractionResult.message ? `\n${extractionResult.message}` : ''}
                </pre>
              </div>
            )}
            <button className="button" onClick={() => setExtractionModalOpen(false)} style={{ marginTop: 16 }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App; 
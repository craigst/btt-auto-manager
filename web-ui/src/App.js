import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { useRef } from 'react';

if (typeof window !== 'undefined') {
  const origFetch = window.fetch;
  window.fetch = function(...args) {
    if (args[0] && typeof args[0] === 'string' && args[0].includes('/webhook/control')) {
      console.warn('[GLOBAL FETCH INTERCEPTOR] POST to /webhook/control', args);
      console.trace('[GLOBAL FETCH INTERCEPTOR] Call stack for /webhook/control');
    }
    return origFetch.apply(this, args);
  };
}

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
  const [hasIntervalBeenEdited, setHasIntervalBeenEdited] = useState(false);
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(false);
  const [extractionModalOpen, setExtractionModalOpen] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [loadNumbers, setLoadNumbers] = useState([]);
  const [loadNumbersStats, setLoadNumbersStats] = useState({ totalLoads: 0, totalRecords: 0 });
  const [loadDetails, setLoadDetails] = useState(null);
  const [loadDetailsModalOpen, setLoadDetailsModalOpen] = useState(false);
  const [countdown, setCountdown] = useState('--:--:--');
  const [uptime, setUptime] = useState(0);
  const countdownInterval = useRef(null);
  const uptimeInterval = useRef(null);
  // Add device modal state
  const [addDeviceModalOpen, setAddDeviceModalOpen] = useState(false);
  const [newDeviceIP, setNewDeviceIP] = useState('');
  const [newDeviceName, setNewDeviceName] = useState('');
  // Track last interval to prevent repeated messages
  const [lastInterval, setLastInterval] = useState(null);
  // State for data table modal
  const [dataTableModalOpen, setDataTableModalOpen] = useState(false);
  const [dataTableModalTitle, setDataTableModalTitle] = useState('');
  const [dataTableModalRows, setDataTableModalRows] = useState([]);
  // State for Load Numbers modal
  const [loadNumbersModalOpen, setLoadNumbersModalOpen] = useState(false);
  const [loadNumbersTable, setLoadNumbersTable] = useState([]);
  const [loadNumbersStatsTable, setLoadNumbersStatsTable] = useState({ totalLoads: 0, totalRecords: 0 });
  const [loadDetailsData, setLoadDetailsData] = useState(null);
  // State for Map Popup modal
  const [mapPopupOpen, setMapPopupOpen] = useState(false);
  const [mapPopupUrl, setMapPopupUrl] = useState('');
  // Color palette for letter badges
  const letterColors = ['#4f46e5','#16a34a','#f59e42','#e11d48','#0ea5e9','#fbbf24','#a21caf','#059669','#b91c1c','#7c3aed'];
  function letterBadge(letter) {
    if (!letter) return null;
    const idx = letter.charCodeAt(0) - 65;
    const color = letterColors[idx % letterColors.length];
    return <span style={{display:'inline-block',background:color,color:'#fff',borderRadius:'50%',width:'22px',height:'22px',lineHeight:'22px',textAlign:'center',fontWeight:'bold',fontSize:'14px',marginRight:'4px'}}>{letter}</span>;
  }
  // Map popup handler
  function openMapPopup(lat, lng, postcode) {
    let embedUrl = '';
    if (lat && lng) {
      embedUrl = `https://www.google.com/maps?q=${lat},${lng}&hl=en&z=16&output=embed`;
    } else if (postcode) {
      embedUrl = `https://www.google.com/maps?q=${encodeURIComponent(postcode)}&hl=en&z=16&output=embed`;
    }
    setMapPopupUrl(embedUrl);
    setMapPopupOpen(true);
    console.debug('Map popup opened:', embedUrl);
  }

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
  const fetchStatus = async (forceUpdateInterval = false) => {
    try {
      const data = await apiCall('/status');
      if (data.error) {
        setError(`Error loading status: ${data.error}`);
        return;
      }
      setStatus(data);
      setAutoUpdateEnabled(data.autoEnabled || false);
      // Only update interval from backend if not edited by user or if forced
      setUpdateInterval(prev => {
        if (!hasIntervalBeenEdited || forceUpdateInterval) {
          console.debug(`[fetchStatus] updateInterval set from backend: ${data.intervalMinutes}`);
          setHasIntervalBeenEdited(false);
          return data.intervalMinutes || 5;
        } else {
          console.debug(`[fetchStatus] updateInterval NOT overwritten (user editing): ${prev}`);
          return prev;
        }
      });
      setLastInterval(data.intervalMinutes || 5);
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
      console.debug('[fetchADBIPs] Received:', data);
      if (data.error) {
        setError(`Error loading ADB IPs: ${data.error}`);
        return;
      }
      setAdbIPs(Array.isArray(data) ? data : []);
      if (!Array.isArray(data) || data.length === 0) {
        setError('No ADB devices found or failed to load.');
      } else {
        setError(null);
      }
    } catch (error) {
      setError(`Error loading ADB IPs: ${error.message}`);
      console.error('[fetchADBIPs] Error:', error);
    }
  };

  // Fetch Load Numbers
  const fetchLoadNumbers = async () => {
    const data = await apiCall('/webhook/load-numbers');
    if (data && !data.error) {
      setLoadNumbers(data.loadNumbers || []);
      setLoadNumbersStats({ totalLoads: data.totalLoads || 0, totalRecords: data.totalRecords || 0 });
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

  // Remove all interval editing logic and UI
  // Remove updateInterval, setUpdateInterval, hasIntervalBeenEdited, setIntervalPending, handleSetInterval, and related state
  // Only display the interval as read-only from the backend
  // In the settings modal, replace the interval input and button with a read-only display
  // ... existing code ...
  // In the settings modal, replace the interval input and button with a read-only display
  const handleSetInterval = async () => {
    console.trace('[handleSetInterval] called');
    const minutes = parseInt(updateInterval);
    if (isNaN(minutes) || minutes < 1 || minutes > 1440) {
      showMessage('Please enter a valid interval between 1 and 1440 minutes', 'error');
      return;
    }
    if (lastInterval === minutes) {
      // Debug: No change, do not show message
      console.debug('[handleSetInterval] Interval unchanged, not showing message');
      return;
    }
    setIntervalPending(true);
    console.debug(`[handleSetInterval] Sending set_interval to backend: ${minutes}`);
    const result = await apiCall('/webhook/control', 'POST', {
      action: 'set_interval',
      minutes: minutes
    });
    setIntervalPending(false);
    if (result.error) {
      showMessage(`Error: ${result.error}`, 'error');
    } else {
      showMessage(`Update interval set to ${minutes} minutes`);
      setLastInterval(minutes);
      setHasIntervalBeenEdited(false);
      fetchStatus(true); // force updateInterval from backend
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

  // Update addADBIP to support device name
  const addADBIP = async () => {
    if (!newDeviceIP.trim()) {
      showMessage('Please enter an IP address', 'error');
      return;
    }
    const result = await apiCall('/webhook/adb-ips', 'POST', {
      action: 'add',
      ip: newDeviceIP.trim(),
      name: newDeviceName.trim() || null
    });
    if (result.error) {
      showMessage(`Error adding device: ${result.error}`, 'error');
    } else {
      showMessage(`Successfully added device: ${newDeviceIP}`);
      setNewDeviceIP('');
      setNewDeviceName('');
      setAddDeviceModalOpen(false);
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

  // Add state for editing device name
  const [editingDevice, setEditingDevice] = useState(null);
  const [editingDeviceName, setEditingDeviceName] = useState('');

  // Add function to handle rename
  const renameADBDevice = async (ip, name) => {
    if (!name.trim()) {
      showMessage('Device name cannot be empty', 'error');
      return;
    }
    const result = await apiCall('/webhook/adb-ips', 'POST', {
      action: 'rename',
      ip,
      name: name.trim()
    });
    if (result.error) {
      showMessage(`Error renaming device: ${result.error}`, 'error');
    } else {
      showMessage(`Renamed device: ${ip}`);
      setEditingDevice(null);
      setEditingDeviceName('');
      fetchADBIPs();
    }
  };

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchStatus(),
        fetchSQLData(),
        fetchADBIPs(),
        fetchLoadNumbers()
      ]);
      setLoading(false);
    };
    
    loadData();
  }, []);

  // Auto-refresh status every 30 seconds (without flashing)
  useEffect(() => {
    const interval = window.setInterval(() => {
      fetchStatus();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  // --- LIVE COUNTERS AND RESPONSIVE TOGGLE PATCH ---
  // Helper to get next update time from status
  function getNextUpdateTime(status) {
    if (!status || !status.autoEnabled) return null;
    if (status.nextUpdateTime) return new Date(status.nextUpdateTime);
    const intervalMinutes = status.intervalMinutes || 5;
    return new Date(Date.now() + intervalMinutes * 60 * 1000);
  }

  // Live countdown effect
  useEffect(() => {
    if (!status || !status.autoEnabled) {
      setCountdown('--:--:--');
      if (countdownInterval.current) clearInterval(countdownInterval.current);
      return;
    }
    let nextUpdate = getNextUpdateTime(status);
    function updateCountdown() {
      const now = new Date();
      const timeLeft = Math.max(0, nextUpdate.getTime() - now.getTime());
      if (timeLeft <= 0) {
        setCountdown('00:00:00');
        nextUpdate = new Date(now.getTime() + (status.intervalMinutes || 5) * 60 * 1000);
        return;
      }
      const hours = Math.floor(timeLeft / (1000 * 60 * 60));
      const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
      setCountdown(`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    }
    updateCountdown();
    countdownInterval.current && clearInterval(countdownInterval.current);
    countdownInterval.current = setInterval(updateCountdown, 1000);
    return () => clearInterval(countdownInterval.current);
  }, [status]);

  // Live uptime effect
  useEffect(() => {
    if (!status || typeof status.uptime !== 'number') {
      if (uptimeInterval.current) clearInterval(uptimeInterval.current);
      return;
    }
    setUptime(status.uptime);
    uptimeInterval.current && clearInterval(uptimeInterval.current);
    uptimeInterval.current = setInterval(() => setUptime(u => u + 1), 1000);
    return () => clearInterval(uptimeInterval.current);
  }, [status]);

  // Responsive toggle
  const [toggleLoading, setToggleLoading] = useState(false);
  const handleToggleAutoUpdate = async () => {
    setToggleLoading(true);
    // Optimistically update UI
    setAutoUpdateEnabled(val => {
      const newVal = !val;
      if (!newVal) {
        setCountdown('--:--:--');
        if (countdownInterval.current) clearInterval(countdownInterval.current);
      }
      return newVal;
    });
    await toggleAutoUpdate();
    setToggleLoading(false);
  };

  // Show Load Numbers modal
  const handleShowLoadNumbers = () => {
    // Build table: Load Number, Date, Record Count
    const dwjjob = sqlData.dwjjob || [];
    // Use top-level loadNumbers state variable directly
    console.debug('handleShowLoadNumbers: loadNumbers', loadNumbers);
    // Build a map of loadNumber -> most recent date
    const loadDateMap = {};
    dwjjob.forEach(row => {
      const load = row.dwjLoad;
      const date = row.dwjDate;
      if (!load || !date) return;
      if (!loadDateMap[load] || date > loadDateMap[load]) {
        loadDateMap[load] = date;
      }
    });
    // Add date to each load entry
    const dataWithDate = loadNumbers.map(load => ({
      ...load,
      date: (loadDateMap[load.loadNumber] || '').toString()
    }));
    // Sort by date descending
    dataWithDate.sort((a, b) => {
      const dateA = (a.date || '').toString();
      const dateB = (b.date || '').toString();
      return dateB.localeCompare(dateA);
    });
    console.debug('handleShowLoadNumbers: dataWithDate', dataWithDate);
    setLoadNumbersTable(dataWithDate);
    setLoadNumbersStatsTable(loadNumbersStats);
    setLoadNumbersModalOpen(true);
  };
  // Show Load Details modal for a load number
  const handleShowLoadDetails = async (loadNumber) => {
    const result = await apiCall(`/webhook/load-details?loadNumber=${encodeURIComponent(loadNumber)}`);
    if (result && !result.error) {
      setLoadDetailsData({ ...result, loadNumber });
      setLoadDetailsModalOpen(true);
    } else {
      showMessage(`Error loading details for load number ${loadNumber}: ${result.error || 'Unknown error'}`, 'error');
    }
  };

  // Show DWJJOB or DWVVEH data in modal
  const handleShowDataTable = (type) => {
    if (type === 'DWJJOB') {
      setDataTableModalTitle('DWJJOB Data');
      setDataTableModalRows(sqlData.dwjjob || []);
    } else if (type === 'DWVVEH') {
      setDataTableModalTitle('DWVVEH Data');
      setDataTableModalRows(sqlData.dwvveh || []);
    }
    setDataTableModalOpen(true);
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading BTT Auto Manager...</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header" style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div style={{display:'flex',alignItems:'center',gap:'10px'}}>
          <span style={{fontSize:'2.5em',marginRight:'12px'}}>🚛</span>
          <div>
            <h1 style={{margin:0,display:'inline-block',verticalAlign:'middle'}}>BTT Auto Manager</h1>
            <p style={{margin:0}}>SQL Database Extraction & ADB Management</p>
          </div>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:'15px'}}>
          <div className="auto-update-controls" style={{display:'flex',alignItems:'center',gap:'10px'}}>
            <div className="countdown-timer" style={{fontFamily:'Courier New,monospace',fontSize:'1.2em',fontWeight:'bold',padding:'5px 10px',borderRadius:'5px',background:'#1a1a1a',border:'2px solid #22c55e',color:'#22c55e',minWidth:'80px',textAlign:'center'}}>{countdown}</div>
            <label className="toggle-switch">
              <input type="checkbox" checked={autoUpdateEnabled} onChange={handleToggleAutoUpdate} disabled={toggleLoading} />
              <span className="slider"></span>
            </label>
          </div>
          <button className="settings-btn" onClick={()=>setSettingsModalOpen(true)} title="Settings" style={{background:'none',border:'none',color:'white',cursor:'pointer',padding:'10px',borderRadius:'50%'}}>
            <span style={{fontSize:'24px'}}>⚙️</span>
          </button>
        </div>
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

        {/* System Status Section - no title */}
        <div className="section">
          {status && (
            <div className="status-grid">
              <div className="status-card">
                <h3>Auto-Update Status</h3>
                <div className={`status-value ${status.autoEnabled ? 'status-online' : 'status-offline'}`}>{status.autoEnabled ? '🟢 Enabled' : '🔴 Disabled'}</div>
              </div>
              <div className="status-card">
                <h3>Webhook Server</h3>
                <div className="status-value status-online">🟢 Running</div>
              </div>
              <div className="status-card">
                <h3>ADB Status</h3>
                <div className={`status-value ${status.adbConnected ? 'status-online' : 'status-offline'}`}>{status.adbConnected ? '🟢 Connected' : '🔴 Not Connected'}</div>
              </div>
              <div className="status-card">
                <h3>Server Uptime</h3>
                <div className="status-value">{formatUptime(uptime)}</div>
              </div>
            </div>
          )}
        </div>

        {/* SQL Data Section */}
        <div className="section">
          <h2 id="sql-header">🗄️ SQL Database Data <span id="sql-last-updated" style={{fontSize:'0.8em',color:'#9ca3af',marginLeft:'10px'}}>Last updated: {status && status.lastProcessed ? status.lastProcessed : 'Never'}</span></h2>
          
          <div className="status-grid">
            <div className="status-card">
              <h3>DWJJOB Data ({sqlData.dwjjob.length} records)</h3>
              <div className="status-value">{sqlData.dwjjob.length} locations</div>
              {sqlData.dwjjob.length > 0 && (
                <button className="button" onClick={() => handleShowDataTable('DWJJOB')}>
                  View Details
                </button>
              )}
            </div>
            <div className="status-card">
              <h3>DWVVEH Data ({sqlData.dwvveh.length} records)</h3>
              <div className="status-value">{sqlData.dwvveh.length} vehicles</div>
              {sqlData.dwvveh.length > 0 && (
                <button className="button" onClick={() => handleShowDataTable('DWVVEH')}>
                  View Details
                </button>
              )}
            </div>
            <div className="status-card">
              <h3>Load Numbers ({loadNumbersStats.totalLoads} unique)</h3>
              <div className="status-value">{loadNumbersStats.totalRecords} total records</div>
              {loadNumbersStats.totalLoads > 0 && (
                <button className="button" onClick={handleShowLoadNumbers}>
                  View Details
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ADB Device Management Section */}
        <div className="section">
          <h2>📱 ADB Device Management 
            <button className="add-device-btn" onClick={()=>setAddDeviceModalOpen(true)} title="Add New Device">+</button>
            <button className="refresh-btn" onClick={fetchADBIPs}>
              🔄 Refresh
            </button>
          </h2>
          {error && (
            <div className="warning">{error}</div>
          )}
          <div className="status-card">
            <h3>Configured ADB IP Addresses</h3>
            {adbIPs.length === 0 && !error ? (
              <p>No ADB IP addresses configured</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{minWidth:'220px'}}>Device Name / IP Address</th>
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
                      <tr key={index} className="fade-in-row">
                        <td style={{minWidth:'220px'}}>
                          {editingDevice === ip ? (
                            <>
                              <input
                                type="text"
                                value={editingDeviceName}
                                onChange={e => setEditingDeviceName(e.target.value)}
                                style={{width:'120px',marginRight:'6px'}}
                                autoFocus
                              />
                              <button className="button success" onClick={() => renameADBDevice(ip, editingDeviceName)}>Save</button>
                              <button className="button" onClick={() => setEditingDevice(null)} style={{marginLeft:'4px'}}>Cancel</button>
                            </>
                          ) : (
                            <>
                              <span>{entry.name ? entry.name : <span style={{color:'#888'}}>(No Name)</span>}<span style={{color:'#aaa',marginLeft:'6px'}}>{ip}</span></span>
                              <button className="button warning" style={{marginLeft:'8px',padding:'2px 8px',display:'inline-block'}} onClick={() => {setEditingDevice(ip);setEditingDeviceName(entry.name||'')}}>Edit</button>
                            </>
                          )}
                        </td>
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
          {/* Remove the old add device input group */}
        </div>
        {/* Add Device Modal */}
        {addDeviceModalOpen && (
          <div className="modal-overlay" onClick={()=>setAddDeviceModalOpen(false)}>
            <div className="modal" onClick={e=>e.stopPropagation()}>
              <div className="modal-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #555',paddingBottom:'10px',marginBottom:'15px'}}>
                <div className="modal-title" style={{fontSize:'1.5em',fontWeight:'bold',color:'#e0e0e0'}}>📱 Add New ADB Device</div>
                <span className="close" style={{color:'#aaa',fontSize:'28px',fontWeight:'bold',cursor:'pointer'}} onClick={()=>setAddDeviceModalOpen(false)}>&times;</span>
              </div>
              <div className="input-group">
                <label htmlFor="new-device-ip">Device IP Address:</label>
                <input type="text" id="new-device-ip" value={newDeviceIP} onChange={e=>setNewDeviceIP(e.target.value)} placeholder="192.168.1.100:5555" />
              </div>
              <div className="input-group">
                <label htmlFor="new-device-name">Device Name (Optional):</label>
                <input type="text" id="new-device-name" value={newDeviceName} onChange={e=>setNewDeviceName(e.target.value)} placeholder="My Android Device" />
              </div>
              <div style={{marginTop:'20px'}}>
                <button className="button success" onClick={addADBIP}>Add Device</button>
                <button className="button" onClick={()=>setAddDeviceModalOpen(false)} style={{marginLeft:'10px'}}>Cancel</button>
              </div>
            </div>
          </div>
        )}

        {/* Control Section */}
        {/* System Controls moved to Settings Modal */}
      </div>
      {/* Settings Modal */}
      {settingsModalOpen && (
        <div className="modal-overlay" onClick={()=>setSettingsModalOpen(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()}>
            <div className="modal-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #555',paddingBottom:'10px',marginBottom:'15px'}}>
              <div className="modal-title" style={{fontSize:'1.5em',fontWeight:'bold',color:'#e0e0e0'}}>⚙️ System Settings</div>
              <span className="close" style={{color:'#aaa',fontSize:'28px',fontWeight:'bold',cursor:'pointer'}} onClick={()=>setSettingsModalOpen(false)}>&times;</span>
            </div>
            <div style={{display:'flex',flexDirection:'row',gap:'24px'}}>
              <div style={{flex:1,background:'#353535',borderRadius:'10px',padding:'20px',boxShadow:'0 2px 8px #0002',border:'1px solid #4a90e2'}}>
                <h3 style={{marginTop:0,color:'#e0e0e0'}}>Auto-Update Settings</h3>
                <div className="input-group">
                  <label>Auto-Update Status:</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <label className="toggle-switch">
                      <input type="checkbox" checked={autoUpdateEnabled} onChange={handleToggleAutoUpdate} disabled={toggleLoading} />
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
                    value={5}
                    readOnly
                    disabled
                  />
                  <span style={{color:'#aaa',marginLeft:'10px'}}>Fixed (5 min)</span>
                </div>
              </div>
              <div style={{flex:1,background:'#353535',borderRadius:'10px',padding:'20px',boxShadow:'0 2px 8px #0002',border:'1px solid #4a90e2'}}>
                <h3 style={{marginTop:0,color:'#e0e0e0'}}>Manual Controls</h3>
                <button className="button" onClick={runExtraction} style={{marginRight:'10px'}}>Run Extraction Now</button>
                <button className="button" onClick={fetchStatus}>Update Status</button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Load Numbers Modal */}
      {loadNumbersModalOpen && (
        <div className="modal-overlay" onClick={()=>setLoadNumbersModalOpen(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()} style={{maxWidth:'90vw',maxHeight:'90vh',width:'900px'}}>
            <div className="modal-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #555',paddingBottom:'10px',marginBottom:'15px'}}>
              <div className="modal-title" style={{fontSize:'1.5em',fontWeight:'bold',color:'#e0e0e0'}}>Load Numbers Data</div>
              <span className="close" style={{color:'#aaa',fontSize:'28px',fontWeight:'bold',cursor:'pointer'}} onClick={()=>setLoadNumbersModalOpen(false)}>&times;</span>
            </div>
            <div style={{overflow:'auto',maxHeight:'70vh',background:'#222',borderRadius:'8px',padding:'8px'}}>
              <p><strong>Total Unique Loads:</strong> {loadNumbersStatsTable.totalLoads || 0}</p>
              <p><strong>Total Records:</strong> {loadNumbersStatsTable.totalRecords || 0}</p>
              <table className="data-table" style={{minWidth:'700px'}}>
                <thead>
                  <tr>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Load Number</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Date</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Record Count</th>
                  </tr>
                </thead>
                <tbody>
                  {loadNumbersTable.map((load, idx) => {
                    console.debug('Rendering load row', load);
                    const formattedDate = formatDate(load.date);
                    return (
                      <tr key={idx}>
                        <td>
                          <a
                            href="#"
                            style={{color:'#4a90e2',textDecoration:'underline'}}
                            onClick={e=>{
                              e.preventDefault();
                              console.debug('Clicked load number', load.loadNumber);
                              // Do NOT close the Load Numbers modal; just open Load Details on top
                              handleShowLoadDetails(load.loadNumber);
                            }}
                          >
                            {load.loadNumber}
                          </a>
                        </td>
                        <td>{formattedDate}</td>
                        <td>{load.count}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <button className="button" onClick={()=>setLoadNumbersModalOpen(false)} style={{marginTop:'16px'}}>Close</button>
          </div>
        </div>
      )}
      {/* Load Details Modal */}
      {loadDetailsModalOpen && loadDetailsData && (
        <div className="modal-overlay" onClick={()=>setLoadDetailsModalOpen(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()} style={{maxWidth:'90vw',maxHeight:'90vh',width:'700px'}}>
            <div className="modal-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #555',paddingBottom:'10px',marginBottom:'15px'}}>
              <div className="modal-title" style={{fontSize:'1.5em',fontWeight:'bold',color:'#e0e0e0'}}>Load Details</div>
              <span className="close" style={{color:'#aaa',fontSize:'28px',fontWeight:'bold',cursor:'pointer'}} onClick={()=>setLoadDetailsModalOpen(false)}>&times;</span>
            </div>
            <div style={{marginBottom:'10px',fontWeight:'bold',fontSize:'1.1em'}}>Details for Load Number: {loadDetailsData.loadNumber}</div>
            {/* Collections */}
            {loadDetailsData.collections && loadDetailsData.collections.length > 0 && (
              <table className="data-table" style={{marginBottom:'8px'}}>
                <thead>
                  <tr>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}></th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Name</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Postcode</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Map</th>
                  </tr>
                </thead>
                <tbody>
                  {loadDetailsData.collections.sort((a,b)=>(a.letter||'').localeCompare(b.letter||''))
                    .map((col,idx)=>(
                    <tr key={idx}>
                      <td>{letterBadge(col.letter)}</td>
                      <td>{col.dwjName||''}</td>
                      <td>{col.dwjPostco||''}</td>
                      <td>{(col.dwjLat && col.dwjLong) ? (
                        <a href="#" onClick={e=>{e.preventDefault();openMapPopup(col.dwjLat,col.dwjLong,null);}} title="Show Map" style={{color:'#4f46e5',fontSize:'1.2em'}}>🗺️</a>
                      ) : (col.dwjPostco ? (
                        <a href="#" onClick={e=>{e.preventDefault();openMapPopup(null,null,col.dwjPostco);}} title="Show Map by Postcode" style={{color:'#4f46e5',fontSize:'1.2em'}}>🗺️</a>
                      ) : null)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {/* Deliveries */}
            {loadDetailsData.deliveries && loadDetailsData.deliveries.length > 0 && (
              <table className="data-table" style={{marginBottom:'12px'}}>
                <thead>
                  <tr>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}></th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Name</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Postcode</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Map</th>
                  </tr>
                </thead>
                <tbody>
                  {loadDetailsData.deliveries.sort((a,b)=>(a.letter||'').localeCompare(b.letter||''))
                    .map((del,idx)=>(
                    <tr key={idx}>
                      <td>{letterBadge(del.letter)}</td>
                      <td>{del.dwjName||''}</td>
                      <td>{del.dwjPostco||''}</td>
                      <td>{(del.dwjLat && del.dwjLong) ? (
                        <a href="#" onClick={e=>{e.preventDefault();openMapPopup(del.dwjLat,del.dwjLong,null);}} title="Show Map" style={{color:'#4f46e5',fontSize:'1.2em'}}>🗺️</a>
                      ) : (del.dwjPostco ? (
                        <a href="#" onClick={e=>{e.preventDefault();openMapPopup(null,null,del.dwjPostco);}} title="Show Map by Postcode" style={{color:'#4f46e5',fontSize:'1.2em'}}>🗺️</a>
                      ) : null)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {/* Vehicles */}
            {loadDetailsData.vehicles && loadDetailsData.vehicles.length > 0 && (
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Vehicle Ref</th>
                    <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Model</th>
                    {((loadDetailsData.collections||[]).length>1) && <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Collection</th>}
                    {((loadDetailsData.deliveries||[]).length>1) && <th style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>Delivery</th>}
                  </tr>
                </thead>
                <tbody>
                  {loadDetailsData.vehicles.slice().sort((a,b)=>{
                    const la = ((a.colLetter || a.delLetter || '').charCodeAt(0)) || 0;
                    const lb = ((b.colLetter || b.delLetter || '').charCodeAt(0)) || 0;
                    return la - lb;
                  }).map((row,idx)=>(
                    <tr key={idx}>
                      <td>{row.dwvVehRef}</td>
                      <td>{row.dwvModDes}</td>
                      {((loadDetailsData.collections||[]).length>1) && <td>{row.colLetter && letterBadge(row.colLetter)}</td>}
                      {((loadDetailsData.deliveries||[]).length>1) && <td>{row.delLetter && letterBadge(row.delLetter)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <button className="button" onClick={()=>setLoadDetailsModalOpen(false)} style={{marginTop:'16px'}}>Close</button>
          </div>
        </div>
      )}
      {/* Map Popup Modal */}
      {mapPopupOpen && (
        <div className="modal-overlay" onClick={()=>setMapPopupOpen(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()} style={{maxWidth:'820px'}}>
            <div className="modal-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #555',paddingBottom:'10px',marginBottom:'15px'}}>
              <div className="modal-title" style={{fontSize:'1.2em',fontWeight:'bold',color:'#e0e0e0'}}>Location Map</div>
              <span className="close" style={{color:'#aaa',fontSize:'28px',fontWeight:'bold',cursor:'pointer'}} onClick={()=>setMapPopupOpen(false)}>&times;</span>
            </div>
            <div style={{textAlign:'center'}}>
              {mapPopupUrl ? (
                <iframe src={mapPopupUrl} width="800" height="500" style={{borderRadius:'8px',border:0,boxShadow:'0 2px 8px #0003'}} allowFullScreen loading="lazy" referrerPolicy="no-referrer-when-downgrade"></iframe>
              ) : (
                <div style={{color:'#aaa',padding:'20px'}}>No GPS coordinates or postcode available for this location.</div>
              )}
            </div>
          </div>
        </div>
      )}
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
      {/* Data Table Modal for DWJJOB/DWVVEH */}
      {dataTableModalOpen && (
        <div className="modal-overlay" onClick={()=>setDataTableModalOpen(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()} style={{maxWidth:'90vw',maxHeight:'90vh',width:'1000px'}}>
            <div className="modal-header" style={{display:'flex',justifyContent:'space-between',alignItems:'center',borderBottom:'1px solid #555',paddingBottom:'10px',marginBottom:'15px'}}>
              <div className="modal-title" style={{fontSize:'1.5em',fontWeight:'bold',color:'#e0e0e0'}}>{dataTableModalTitle}</div>
              <span className="close" style={{color:'#aaa',fontSize:'28px',fontWeight:'bold',cursor:'pointer'}} onClick={()=>setDataTableModalOpen(false)}>&times;</span>
            </div>
            <div style={{overflow:'auto',maxHeight:'70vh',background:'#222',borderRadius:'8px',padding:'8px'}}>
              {dataTableModalRows.length > 0 ? (
                <table className="data-table" style={{minWidth:'900px'}}>
                  <thead>
                    <tr>
                      {Object.keys(dataTableModalRows[0]).map((key, idx) => (
                        <th key={idx} style={{position:'sticky',top:0,zIndex:2,background:'#4a90e2',color:'#fff'}}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dataTableModalRows.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val, j) => (
                          <td key={j}>{val || ''}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{color:'#aaa',padding:'20px'}}>No data available</div>
              )}
            </div>
            <button className="button" onClick={()=>setDataTableModalOpen(false)} style={{marginTop:'16px'}}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App; 
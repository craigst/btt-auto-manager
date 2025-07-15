#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
import sqlite3
import traceback

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'getsql.log')
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db')
LOCAL_DB_PATH = os.path.join(DB_DIR, 'sql.db')
DEVICE_DB_PATH = '/data/data/com.bca.bcatrack/cache/cache/data/sql.db'

console = Console()

def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a') as f:
        f.write(f'[{timestamp}] {msg}\n')

def clear_log():
    with open(LOG_FILE, 'w') as f:
        f.write(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] Log started\n')

def run_adb(cmd, timeout=15, capture_output=True):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True, timeout=timeout)
        if result.returncode != 0:
            log(f"ADB command failed: {cmd}\n{result.stderr}")
            return None
        return result.stdout.strip() if capture_output else True
    except subprocess.TimeoutExpired:
        log(f"ADB command timed out: {cmd}")
        return None
    except Exception as e:
        log(f"ADB command error: {cmd} - {e}")
        return None

def check_adb():
    out = run_adb('adb version')
    return isinstance(out, str) and 'Android Debug Bridge' in out

def get_connected_device():
    out = run_adb('adb devices')
    if not isinstance(out, str):
        return None
    lines = out.splitlines()
    for line in lines[1:]:
        if line.strip() and ('device' in line and not 'offline' in line):
            return line.split()[0]
    return None

def run_adb_with_root(cmd, device, timeout=10):
    # Try non-root first
    try:
        out = run_adb(cmd, timeout=timeout)
        if out is not None and 'Permission denied' not in str(out):
            return out, 'non-root', None
    except Exception as e:
        log(f"Non-root command error: {e}\n{traceback.format_exc()}")
        return None, 'non-root', f"Non-root error: {e}"
    # Try su -c ...
    shell_part = cmd.split('shell',1)[1].strip() if 'shell' in cmd else cmd
    rootc_cmd = f'adb -s {device} shell su -c "{shell_part}"'
    try:
        rootc_out = run_adb(rootc_cmd, timeout=timeout)
        if rootc_out is not None and 'Permission denied' not in str(rootc_out):
            return rootc_out, 'suc', None
    except Exception as e:
        log(f"RootC command error: {e}\n{traceback.format_exc()}")
        return None, 'suc', f"RootC error: {e}"
    return None, 'all-failed', 'All root forms failed'

def check_device_db_exists(device):
    cmd = f'adb -s {device} shell ls -l "{DEVICE_DB_PATH}"'
    out, used_root, err = run_adb_with_root(cmd, device, timeout=10)
    log(f"ls output ({'root' if used_root == 'suc' else 'non-root'}): {out!r}")
    if err:
        log(f"ls error ({'root' if used_root == 'suc' else 'non-root'}): {err}")
    if isinstance(out, str) and out.strip() and 'No such file' not in out and 'Permission denied' not in out:
        return True, out, used_root, err
    return False, out, used_root, err

def copy_to_sdcard(device, use_root=False):
    dst = '/sdcard/sql.db'
    if use_root == 'suc':
        copy_cmd = f'adb -s {device} shell su -c "cp {DEVICE_DB_PATH} {dst}"'
    else:
        copy_cmd = f'adb -s {device} shell cp "{DEVICE_DB_PATH}" "{dst}"'
    out = run_adb(copy_cmd, timeout=15)
    if out is None:
        log(f"Failed to copy sql.db to /sdcard ({'root' if use_root == 'suc' else 'non-root'})")
        return False
    log(f"Copied sql.db to /sdcard ({'root' if use_root == 'suc' else 'non-root'})")
    return True

def delete_sdcard_db(device, use_root=False):
    if use_root == 'suc':
        del_cmd = f'adb -s {device} shell su -c "rm /sdcard/sql.db"'
    else:
        del_cmd = f'adb -s {device} shell rm /sdcard/sql.db'
    try:
        result = subprocess.run(del_cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            if 'No such file or directory' in result.stderr:
                log(f"/sdcard/sql.db did not exist (no cleanup needed) ({'root' if use_root == 'suc' else 'non-root'})")
                return True
            log(f"Failed to delete /sdcard/sql.db ({'root' if use_root == 'suc' else 'non-root'}): {result.stderr.strip()}")
            return False
        log(f"Deleted /sdcard/sql.db on device ({'root' if use_root == 'suc' else 'non-root'})")
        return True
    except subprocess.TimeoutExpired:
        log(f"Timeout: Could not delete /sdcard/sql.db ({'root' if use_root == 'suc' else 'non-root'}): command timed out.")
        return False
    except Exception as e:
        log(f"Exception deleting /sdcard/sql.db ({'root' if use_root == 'suc' else 'non-root'}): {e}\n{traceback.format_exc()}")
        return False

def pull_from_sdcard(device):
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    pull_cmd = f'adb -s {device} pull /sdcard/sql.db "{LOCAL_DB_PATH}"'
    out = run_adb(pull_cmd, timeout=30)
    if os.path.exists(LOCAL_DB_PATH):
        log("Pulled sql.db to local db directory")
        return True
    log("Failed to pull sql.db to local db directory")
    return False

def get_file_details(path):
    if not os.path.exists(path):
        return None
    stat = os.stat(path)
    size = stat.st_size
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    return {'size': size, 'mtime': mtime}

def get_device_file_stats(device):
    stat_cmd = f'adb -s {device} shell stat "{DEVICE_DB_PATH}"'
    stat_out, used_root, stat_err = run_adb_with_root(stat_cmd, device, timeout=10)
    log(f"stat output ({'root' if used_root == 'suc' else 'non-root'}): {stat_out!r}")
    if stat_err:
        log(f"stat error ({'root' if used_root == 'suc' else 'non-root'}): {stat_err}")
    mtime = ctime = atime = birth = None
    size = None
    stat_fields = {}
    stat_error = stat_err
    if isinstance(stat_out, str) and stat_out:
        for line in stat_out.splitlines():
            l = line.strip()
            if l.startswith('Modify:'):
                mtime = l.split('Modify:')[1].strip().split()[0]
                stat_fields['Modify'] = l
            elif l.startswith('Change:'):
                ctime = l.split('Change:')[1].strip().split()[0]
                stat_fields['Change'] = l
            elif l.startswith('Access:') and 'Access:' == l[:7]:
                atime = l.split('Access:')[1].strip().split()[0]
                stat_fields['Access'] = l
            elif l.startswith('Birth:'):
                birth = l.split('Birth:')[1].strip().split()[0]
                stat_fields['Birth'] = l
            elif l.lower().startswith('crtime:'):
                birth = l.split(':',1)[1].strip().split()[0]
                stat_fields['crtime'] = l
            elif l.startswith('Size:'):
                size = l.split('Size:')[1].strip().split()[0]
                stat_fields['Size'] = l
        if not birth and not stat_error:
            stat_error = 'No creation time (Birth/crtime) found in stat output.'
    else:
        if not stat_error:
            stat_error = 'stat command failed or returned no output.'
    # Fallback: parse ls -l
    ls_cmd = f'adb -s {device} shell ls -l "{DEVICE_DB_PATH}"'
    ls_out, used_root_ls, ls_err = run_adb_with_root(ls_cmd, device, timeout=10)
    log(f"ls -l output ({'root' if used_root_ls == 'suc' else 'non-root'}): {ls_out!r}")
    if ls_err:
        log(f"ls -l error ({'root' if used_root_ls == 'suc' else 'non-root'}): {ls_err}")
    return {
        'mtime': mtime,
        'ctime': ctime,
        'atime': atime,
        'birth': birth,
        'size': size,
        'ls': ls_out,
        'stat': stat_out,
        'stat_fields': stat_fields,
        'stat_error': stat_error,
        'used_root': used_root,
        'ls_error': ls_err
    }

def get_db_last_update(local_db_path):
    # Try to find a last-update timestamp in the db
    likely_tables = ['meta', 'metadata', 'info', 'settings']
    likely_columns = ['last_update', 'last_updated', 'modified', 'updated_at', 'mod_time', 'update_time']
    found = None
    debug = []
    if not os.path.exists(local_db_path):
        debug.append('No local db file found for last update check.')
        return None, debug
    try:
        conn = sqlite3.connect(local_db_path)
        c = conn.cursor()
        # Get all tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in c.fetchall()]
        debug.append(f"Tables: {tables}")
        for table in tables:
            # Get columns for each table
            c.execute(f'PRAGMA table_info({table});')
            columns = [row[1] for row in c.fetchall()]
            debug.append(f"Table {table} columns: {columns}")
            for col in columns:
                if col.lower() in likely_columns:
                    # Try to get the most recent value
                    try:
                        c.execute(f'SELECT {col} FROM {table} ORDER BY {col} DESC LIMIT 1;')
                        val = c.fetchone()
                        if val and val[0]:
                            found = (table, col, val[0])
                            debug.append(f"Found last update: {found}")
                            conn.close()
                            return found, debug
                    except Exception as e:
                        debug.append(f"Error querying {table}.{col}: {e}")
        conn.close()
    except Exception as e:
        debug.append(f"DB error: {e}")
    return found, debug

def get_db_counts(local_db_path):
    debug = []
    counts = {'DWJJOB': None, 'DWVVEH': None, 'unique_loads': None}
    if not os.path.exists(local_db_path):
        debug.append('No local db file found for counts.')
        return counts, debug
    try:
        import sqlite3
        conn = sqlite3.connect(local_db_path)
        c = conn.cursor()
        # Count locations (DWJJOB)
        try:
            c.execute('SELECT COUNT(*) FROM DWJJOB;')
            counts['DWJJOB'] = c.fetchone()[0]
            debug.append(f"DWJJOB count: {counts['DWJJOB']}")
        except Exception as e:
            debug.append(f"DWJJOB count error: {e}")
        # Count cars (DWVVEH)
        try:
            c.execute('SELECT COUNT(*) FROM DWVVEH;')
            counts['DWVVEH'] = c.fetchone()[0]
            debug.append(f"DWVVEH count: {counts['DWVVEH']}")
        except Exception as e:
            debug.append(f"DWVVEH count error: {e}")
        # Count unique load numbers (DWJJOB.dwjLoad)
        try:
            c.execute('SELECT COUNT(DISTINCT dwjLoad) FROM DWJJOB;')
            counts['unique_loads'] = c.fetchone()[0]
            debug.append(f"Unique load numbers (DWJJOB.dwjLoad): {counts['unique_loads']}")
        except Exception as e:
            debug.append(f"Unique load numbers count error: {e}")
        conn.close()
    except Exception as e:
        debug.append(f"DB error: {e}")
    return counts, debug

def run_diagnostics_commands(device):
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
    diag_results = []
    for label, cmd in diag_cmds:
        try:
            log(f"DIAG: Running {label}: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            out = result.stdout.strip() if result.stdout else ''
            err = result.stderr.strip() if result.stderr else ''
            log(f"DIAG: {label} stdout: {out}")
            log(f"DIAG: {label} stderr: {err}")
            diag_results.append((label, cmd, out, err, result.returncode))
        except subprocess.TimeoutExpired:
            log(f"DIAG: {label} command timed out: {cmd}")
            diag_results.append((label, cmd, '', 'Timeout', -1))
        except Exception as e:
            log(f"DIAG: {label} exception: {e}\n{traceback.format_exc()}")
            diag_results.append((label, cmd, '', f'Exception: {e}', -2))
    # Try interactive root shell
    try:
        log("DIAG: Trying interactive root shell: adb shell, then su, then whoami")
        result = subprocess.run(f'adb -s {device} shell su -c "whoami"', shell=True, capture_output=True, text=True, timeout=10)
        out = result.stdout.strip() if result.stdout else ''
        err = result.stderr.strip() if result.stderr else ''
        log(f"DIAG: interactive su -c whoami stdout: {out}")
        log(f"DIAG: interactive su -c whoami stderr: {err}")
        diag_results.append(('interactive_su_c_whoami', 'adb shell su -c "whoami"', out, err, result.returncode))
    except Exception as e:
        log(f"DIAG: interactive su -c whoami exception: {e}\n{traceback.format_exc()}")
        diag_results.append(('interactive_su_c_whoami', 'adb shell su -c "whoami"', '', f'Exception: {e}', -2))
    return diag_results

def timed_step(label, func, *args, **kwargs):
    start = time.time()
    try:
        result = func(*args, **kwargs)
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
    end = time.time()
    duration = end - start
    log(f"STEP TIMING: {label} took {duration:.2f} seconds")
    return result, success, error, duration

def main():
    clear_log()
    steps = [
        ("Check ADB installed", None),
        ("Check device connected", None),
        ("Clean up old /sdcard/sql.db", None),
        ("Check for sql.db at fixed path", None),
        ("Get device file info", None),
        ("Copy sql.db to /sdcard", None),
        ("Pull sql.db to ./db", None),
        ("Delete /sdcard/sql.db after pull", None),
        ("Show file details", None),
    ]
    status_map = {}
    error_message = None
    summary_details = None
    cleanup_errors = []
    device_file_info = None
    db_last_update = None
    db_last_update_debug = []
    diagnostics_run = False
    diagnostics_results = []
    timings = []
    db_counts = None
    db_counts_debug = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Starting...", total=len(steps))
        # 1. Check ADB
        progress.update(task, description=steps[0][0])
        (adb_ok, success, error, duration) = timed_step('Check ADB', check_adb)
        timings.append((steps[0][0], duration, success, error))
        if not adb_ok:
            status_map[0] = 'fail'
            error_message = "ADB not found. Please install Android Platform Tools."
            log(f"ERROR: {error_message}")
            progress.stop()
            show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run, diagnostics_results, timings, db_counts)
            sys.exit(1)
        status_map[0] = 'done'
        progress.advance(task)

        # 2. Check device
        progress.update(task, description=steps[1][0])
        (device, success, error, duration) = timed_step('Check device', get_connected_device)
        timings.append((steps[1][0], duration, success, error))
        if not device:
            status_map[1] = 'fail'
            error_message = "No device connected. Please connect your Android device and enable USB debugging."
            log(f"ERROR: {error_message}")
            progress.stop()
            show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run, diagnostics_results, timings, db_counts)
            sys.exit(1)
        status_map[1] = 'done'
        log(f"Using device: {device}")
        progress.advance(task)

        # 3. Clean up old /sdcard/sql.db
        progress.update(task, description=steps[2][0])
        (del_result, success, error, duration) = timed_step('Delete old /sdcard/sql.db', delete_sdcard_db, device)
        timings.append((steps[2][0], duration, success, error))
        if not del_result:
            cleanup_errors.append("Could not delete old /sdcard/sql.db before copy (may not exist or permission denied)")
        status_map[2] = 'done'
        progress.advance(task)

        # 4. Check for sql.db at fixed path
        progress.update(task, description=steps[3][0])
        (check_result, success, error, duration) = timed_step('Check device db exists', check_device_db_exists, device)
        timings.append((steps[3][0], duration, success, error))
        found, ls_out, used_root_check, err_check = check_result if check_result else (False, None, None, None)
        if not found:
            status_map[3] = 'fail'
            error_message = f"sql.db not found at {DEVICE_DB_PATH} on device. ls output: {ls_out!r}"
            log(f"ERROR: {error_message}")
            diagnostics_run = True
            diagnostics_results = run_diagnostics_commands(device)
            progress.stop()
            show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run, diagnostics_results, timings, db_counts)
            sys.exit(1)
        status_map[3] = 'done'
        log(f"Found sql.db at {DEVICE_DB_PATH}")
        log(f"File details: {ls_out}")
        progress.advance(task)

        # 5. Get device file info
        progress.update(task, description=steps[4][0])
        (device_file_info, success, error, duration) = timed_step('Get device file stats', get_device_file_stats, device)
        timings.append((steps[4][0], duration, success, error))
        status_map[4] = 'done'
        progress.advance(task)

        # 6. Copy to /sdcard
        progress.update(task, description=steps[5][0])
        (copy_result, success, error, duration) = timed_step('Copy to /sdcard', copy_to_sdcard, device, used_root_check)
        timings.append((steps[5][0], duration, success, error))
        if not copy_result:
            status_map[5] = 'fail'
            error_message = "Failed to copy sql.db to /sdcard. See getsql.log for details."
            log(f"ERROR: {error_message}")
            progress.stop()
            show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run, diagnostics_results, timings, db_counts)
            sys.exit(1)
        status_map[5] = 'done'
        progress.advance(task)

        # 7. Pull to ./db
        progress.update(task, description=steps[6][0])
        (pull_result, success, error, duration) = timed_step('Pull from /sdcard', pull_from_sdcard, device)
        timings.append((steps[6][0], duration, success, error))
        if not pull_result:
            status_map[6] = 'fail'
            error_message = "Failed to pull sql.db to ./db. See getsql.log for details."
            log(f"ERROR: {error_message}")
            progress.stop()
            show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run, diagnostics_results, timings, db_counts)
            sys.exit(1)
        status_map[6] = 'done'
        progress.advance(task)

        # 8. Delete /sdcard/sql.db after pull
        progress.update(task, description=steps[7][0])
        (del2_result, success, error, duration) = timed_step('Delete /sdcard/sql.db after pull', delete_sdcard_db, device, used_root_check)
        timings.append((steps[7][0], duration, success, error))
        if not del2_result:
            cleanup_errors.append("Could not delete /sdcard/sql.db after pull (permission denied, tried as root)")
        status_map[7] = 'done'
        progress.advance(task)

        # 9. Show file details
        progress.update(task, description=steps[8][0])
        (details, success, error, duration) = timed_step('Get local file details', get_file_details, LOCAL_DB_PATH)
        timings.append((steps[8][0], duration, success, error))
        if details:
            status_map[8] = 'done'
            summary_details = details
            db_last_update, db_last_update_debug = get_db_last_update(LOCAL_DB_PATH)
            for dbg in db_last_update_debug:
                log(f"db_last_update_debug: {dbg}")
            db_counts, db_counts_debug = get_db_counts(LOCAL_DB_PATH)
            for dbg in db_counts_debug:
                log(f"db_counts_debug: {dbg}")
        else:
            status_map[8] = 'fail'
            error_message = "Could not get file details."
            log(f"ERROR: {error_message}")
        progress.advance(task)

    show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run, diagnostics_results, timings, db_counts)

def show_final_ui(steps, status_map, error_message, summary_details, cleanup_errors, device_file_info, db_last_update, diagnostics_run=False, diagnostics_results=None, timings=None, db_counts=None):
    table = Table(title="ADB SQL.db Retriever Progress", box=box.SIMPLE, show_lines=True)
    table.add_column("Step", style="bold")
    table.add_column("Status", style="bold")
    for idx, (label, _) in enumerate(steps):
        status = status_map.get(idx, None)
        if status == 'done':
            table.add_row(label, "[green]✔ Done[/green]")
        elif status == 'fail':
            table.add_row(label, "[red]✖ Failed[/red]")
        else:
            table.add_row(label, "[yellow]...[/yellow]")
    console.print(table)
    if timings:
        timing_table = Table(title="Step Timings (seconds)", box=box.SIMPLE)
        timing_table.add_column("Step")
        timing_table.add_column("Duration", justify="right")
        timing_table.add_column("Success", justify="center")
        timing_table.add_column("Error")
        for label, duration, success, error in timings:
            timing_table.add_row(label, f"{duration:.2f}", "✔" if success else "✖", error or "")
        console.print(timing_table)
    if error_message:
        msg = f"[red]Error:[/red] {error_message}\nSee [bold]getsql.log[/bold] for troubleshooting details."
        if diagnostics_run:
            msg += "\n\n[bold yellow]Diagnostics were run. See getsql.log for full output.[/bold yellow]"
            if diagnostics_results:
                msg += "\n\n[bold]Diagnostics summary:[/bold]"
                for label, cmd, out, err, rc in diagnostics_results:
                    msg += f"\n- {label}: rc={rc}"
                    if out:
                        msg += f"\n  stdout: {out[:100]}{'...' if len(out)>100 else ''}"
                    if err:
                        msg += f"\n  stderr: {err[:100]}{'...' if len(err)>100 else ''}"
        console.print(Panel(msg, title="[red]FAILED[/red]", style="red"))
        return
    elif summary_details:
        # Clean SUCCESS panel
        msg = Text()
        msg.append("SQL.db Extraction SUCCESS\n\n", style="bold green")
        msg.append("Device file:\n", style="bold")
        if device_file_info:
            msg.append(f"  atime: {device_file_info.get('atime','?')}\n")
            msg.append(f"  mtime: {device_file_info.get('mtime','?')}\n")
            msg.append(f"  ctime: {device_file_info.get('ctime','?')}\n")
            msg.append(f"  size: {device_file_info.get('size','?')} bytes\n")
        msg.append("\nLocal file:\n", style="bold")
        msg.append(f"  size: {summary_details['size']} bytes\n")
        msg.append(f"  last modified: {summary_details['mtime']}\n")
        msg.append(f"  path: {LOCAL_DB_PATH}\n")
        if db_counts:
            msg.append("\nDatabase summary:\n", style="bold")
            msg.append(f"  Number of Locations (DWJJOB): {db_counts.get('DWJJOB','?')}\n")
            msg.append(f"  Number of Cars (DWVVEH): {db_counts.get('DWVVEH','?')}\n")
            msg.append(f"  Number of Loads (unique DWJJOB.dwjLoad): {db_counts.get('unique_loads','?')}\n")
        if db_last_update:
            msg.append(f"\n[DB] Last Update: table '{db_last_update[0]}', column '{db_last_update[1]}', value: {db_last_update[2]}\n")
        if cleanup_errors:
            msg.append("\nCleanup warnings:\n", style="bold yellow")
            msg.append("\n".join(cleanup_errors) + "\n")
        console.print(Panel(msg, title="SUCCESS", style="green"))
        return
    else:
        console.print(Panel("[yellow]Process completed, but no file details available.[/yellow]", title="[yellow]INFO[/yellow]", style="yellow"))

if __name__ == "__main__":
    main() 
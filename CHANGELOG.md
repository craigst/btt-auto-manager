# Changelog

## [Unreleased]
- Show ADB device name in web UI status
- Server uptime now formatted as days, hours, and minutes
- Robust ADB extraction: tries all root/copy methods, fallback paths, and provides debug logs
- Persistent ADB key: no more repeated device authorization after Docker rebuilds
- Auto-update toggle: works with any connected device, persists across restarts
- Web UI: immediate SQL refresh after extraction, better status display, debug log output 
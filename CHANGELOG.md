# Changelog

All notable changes to the BTT Auto Manager project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-07-15

### Added
- **Docker Support**: Complete Docker containerization with Dockerfile and docker-compose.yml
- **GitHub Actions**: Automated CI/CD pipeline for Docker builds and testing
- **Production Deployment**: Automated deployment scripts for production environments
- **Enhanced Documentation**: Comprehensive README, technical codex, and setup guides
- **Makefile**: Easy-to-use commands for building, running, and managing the application
- **Health Checks**: Docker health checks and webhook health endpoints
- **Logging Improvements**: Enhanced logging with rotation and structured output
- **Security Enhancements**: Non-root user support and proper file permissions
- **Development Tools**: Development override configuration and debugging support

### Changed
- **Webhook Host**: Changed from localhost to 0.0.0.0 for Docker compatibility
- **Configuration Management**: Improved configuration file handling and validation
- **Error Handling**: Enhanced error handling and recovery mechanisms
- **Performance**: Optimized Docker image size and startup time

### Fixed
- **ADB Access**: Fixed ADB device access issues in Docker environment
- **File Permissions**: Resolved file permission issues for database and log files
- **Network Access**: Fixed webhook server network binding for container access

### Technical Improvements
- **Multi-stage Builds**: Optimized Docker image with multi-stage build process
- **Volume Mounting**: Proper volume mounting for persistent data storage
- **Environment Variables**: Comprehensive environment variable configuration
- **Entrypoint Script**: Robust container initialization and startup process

## [1.0.0] - 2025-01-15

### Added
- **Core Functionality**: Initial release of BTT Auto Manager
- **SQL Extraction**: Automated SQLite database extraction from Android devices
- **Webhook API**: RESTful API for data access and system control
- **ADB Integration**: Android Debug Bridge integration for device communication
- **Auto-update System**: Configurable automated extraction scheduling
- **Configuration Management**: JSON-based configuration persistence
- **Logging System**: Comprehensive logging and diagnostics
- **Multi-threading**: Concurrent webhook server and auto-update threads
- **Error Recovery**: Robust error handling and recovery mechanisms

### Features
- Manual and automated SQL extraction
- Support for both USB and network ADB connections
- Root and non-root device access methods
- Real-time status monitoring
- Database statistics and metadata extraction
- Comprehensive diagnostic tools

## [Unreleased]

### Planned
- **Authentication**: Webhook API authentication and authorization
- **SSL/TLS**: HTTPS support for webhook endpoints
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Backup**: Automated database backup and recovery
- **Notifications**: Email/SMS notifications for system events
- **API Versioning**: Versioned webhook API endpoints
- **Rate Limiting**: API rate limiting and throttling
- **Multi-device**: Support for multiple Android devices simultaneously

---

## Version History

- **2.0.0**: Major release with Docker support and production deployment
- **1.0.0**: Initial release with core functionality

## Contributing

When contributing to this project, please update this changelog with a new entry under the [Unreleased] section following the format above. 
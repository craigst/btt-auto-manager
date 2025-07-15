# BTT Auto Manager Makefile

.PHONY: help build run stop logs clean setup deploy test

# Default target
help:
	@echo "BTT Auto Manager - Available Commands:"
	@echo ""
	@echo "  setup     - Initial setup and configuration"
	@echo "  build     - Build Docker image"
	@echo "  run       - Start the container"
	@echo "  stop      - Stop the container"
	@echo "  logs      - View container logs"
	@echo "  clean     - Remove containers and images"
	@echo "  deploy    - Production deployment"
	@echo "  test      - Test webhook endpoints"
	@echo "  shell     - Access container shell"
	@echo "  status    - Check container status"

# Initial setup
setup:
	@echo "🚀 Setting up BTT Auto Manager..."
	@./scripts/setup.sh

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	@docker-compose build

# Start the container
run:
	@echo "🚀 Starting BTT Auto Manager..."
	@docker-compose up -d

# Stop the container
stop:
	@echo "🛑 Stopping BTT Auto Manager..."
	@docker-compose down

# View logs
logs:
	@echo "📋 Viewing logs..."
	@docker-compose logs -f

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down --rmi all --volumes --remove-orphans
	@docker system prune -f

# Production deployment
deploy:
	@echo "🚀 Production deployment..."
	@sudo ./scripts/deploy.sh

# Test webhook endpoints
test:
	@echo "🧪 Testing webhook endpoints..."
	@echo "Health check:"
	@curl -s http://localhost:5680/healthz || echo "❌ Health check failed"
	@echo ""
	@echo "Status endpoint:"
	@curl -s http://localhost:5680/status | python3 -m json.tool || echo "❌ Status endpoint failed"
	@echo ""
	@echo "ADB IPs endpoint:"
	@curl -s http://localhost:5680/webhook/adb-ips | python3 -m json.tool || echo "❌ ADB IPs endpoint failed"

# Access container shell
shell:
	@echo "🐚 Accessing container shell..."
	@docker-compose exec btt-auto-manager bash

# Check container status
status:
	@echo "📊 Container status:"
	@docker-compose ps
	@echo ""
	@echo "📊 System resources:"
	@docker stats --no-stream btt-auto-manager || echo "Container not running"

# Development mode
dev:
	@echo "🔧 Starting in development mode..."
	@docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Restart container
restart:
	@echo "🔄 Restarting container..."
	@docker-compose restart

# Update and rebuild
update:
	@echo "🔄 Updating and rebuilding..."
	@docker-compose down
	@docker-compose build --no-cache
	@docker-compose up -d 
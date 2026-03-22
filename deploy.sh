#!/bin/bash

# Crypto Platform Deployment Script
# This script helps deploy the crypto platform using Docker Compose

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    log_warn ".env file not found. Creating from template..."
    if [ -f .env.docker ]; then
        cp .env.docker .env
        log_info "Created .env from .env.docker template"
        log_warn "Please edit .env file with your configuration before continuing."
        exit 1
    else
        log_error "No .env.docker template found. Please create .env file manually."
        exit 1
    fi
fi

# Load environment variables
source .env

# Check required environment variables
required_vars=("SECRET_KEY" "DB_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        log_error "Required environment variable $var is not set in .env file"
        exit 1
    fi
done

# Function to deploy
deploy() {
    log_info "Starting deployment..."
    
    # Build and start services
    log_info "Building Docker images..."
    docker-compose build
    
    log_info "Starting services..."
    docker-compose up -d
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    docker-compose exec -T db bash -c 'until pg_isready -U crypto_user -d crypto_platform; do sleep 2; done'
    
    # Run migrations
    log_info "Running database migrations..."
    docker-compose exec -T web python manage.py migrate --settings=backend.settings.production
    
    # Collect static files
    log_info "Collecting static files..."
    docker-compose exec -T web python manage.py collectstatic --noinput --settings=backend.settings.production
    
    # Create superuser if it doesn't exist
    log_info "Creating superuser..."
    docker-compose exec -T web python manage.py shell --settings=backend.settings.production << EOF
from backend.users.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        email='admin@cryptoplatform.local',
        username='admin',
        password='SecureAdmin123!'
    )
    print("Superuser created: admin@cryptoplatform.local / SecureAdmin123!")
else:
    print("Superuser already exists")
EOF
    
    # Load initial data if needed
    log_info "Loading initial data..."
    # You can add commands to load initial trading pairs here
    
    log_info "Deployment completed successfully!"
    log_info "Application is available at: http://localhost"
    log_info "Admin panel: http://localhost/admin"
    log_info "API documentation: http://localhost/api/docs"
    log_info "Health check: http://localhost/health"
    log_info "Flower (Celery monitoring): http://localhost:5555"
}

# Function to stop services
stop() {
    log_info "Stopping services..."
    docker-compose down
    log_info "Services stopped."
}

# Function to restart services
restart() {
    log_info "Restarting services..."
    docker-compose restart
    log_info "Services restarted."
}

# Function to show logs
logs() {
    if [ -n "$1" ]; then
        docker-compose logs -f "$1"
    else
        docker-compose logs -f
    fi
}

# Function to backup database
backup() {
    log_info "Creating database backup..."
    timestamp=$(date +"%Y%m%d_%H%M%S")
    backup_file="backup_${timestamp}.sql"
    
    docker-compose exec -T db pg_dump -U crypto_user crypto_platform > "$backup_file"
    
    log_info "Database backup created: $backup_file"
}

# Function to restore database
restore() {
    if [ -z "$1" ]; then
        log_error "Please provide backup file name: ./deploy.sh restore backup_file.sql"
        exit 1
    fi
    
    if [ ! -f "$1" ]; then
        log_error "Backup file $1 not found"
        exit 1
    fi
    
    log_info "Restoring database from $1..."
    docker-compose exec -T db psql -U crypto_user -d crypto_platform < "$1"
    log_info "Database restored successfully."
}

# Function to update
update() {
    log_info "Updating application..."
    
    # Pull latest changes
    git pull
    
    # Build and restart
    docker-compose build
    docker-compose up -d
    
    # Run migrations
    docker-compose exec -T web python manage.py migrate --settings=backend.settings.production
    
    # Collect static files
    docker-compose exec -T web python manage.py collectstatic --noinput --settings=backend.settings.production
    
    log_info "Update completed!"
}

# Main script logic
case "$1" in
    deploy)
        deploy
        ;;
    start)
        deploy
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$2"
        ;;
    backup)
        backup
        ;;
    restore)
        restore "$2"
        ;;
    update)
        update
        ;;
    status)
        docker-compose ps
        ;;
    *)
        echo "Usage: $0 {deploy|start|stop|restart|logs|backup|restore|update|status}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy the application (first time setup)"
        echo "  start    - Start the application"
        echo "  stop     - Stop the application"
        echo "  restart  - Restart the application"
        echo "  logs     - Show logs (optional service name)"
        echo "  backup   - Create database backup"
        echo "  restore  - Restore database from backup"
        echo "  update   - Update the application"
        echo "  status   - Show service status"
        exit 1
        ;;
esac

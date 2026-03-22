#!/bin/bash

# Crypto Platform Stop Script
# Gracefully stops all running services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BLUE}🛑 Stopping Crypto Platform Services${NC}"

# Function to stop process by name
stop_process() {
    local process_name=$1
    local description=$2
    
    if pgrep -f "$process_name" > /dev/null; then
        print_status "Stopping $description..."
        pkill -f "$process_name" || true
        sleep 2
        
        # Force kill if still running
        if pgrep -f "$process_name" > /dev/null; then
            print_warning "Force stopping $description..."
            pkill -9 -f "$process_name" || true
        fi
        
        print_success "$description stopped"
    else
        print_warning "$description was not running"
    fi
}

# Stop Django backend
stop_process "manage.py runserver" "Django backend"

# Stop Next.js frontend
stop_process "next dev" "Next.js frontend"

# Stop Redis (optional)
if pgrep -x "redis-server" > /dev/null; then
    read -p "Do you want to stop Redis server? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        stop_process "redis-server" "Redis server"
    fi
fi

# Kill any remaining processes on ports 8000 and 3000
print_status "Checking for remaining processes on ports 8000 and 3000..."

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Killing remaining process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Killing remaining process on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

print_success "All Crypto Platform services have been stopped"

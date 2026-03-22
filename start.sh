#!/bin/bash

# Crypto Platform Development Starter Script
# This script starts both the Django backend and Next.js frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    print_warning "Killing process on port $port..."
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
}

# Main script
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Cleo Platform Development Environment Starter        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if required directories exist
if [ ! -d "backend" ]; then
    print_error "Backend directory not found!"
    exit 1
fi

if [ ! -d "crypto-platform-web" ]; then
    print_error "Frontend directory not found!"
    exit 1
fi

# Check for Python virtual environment
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    print_warning "No virtual environment found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    print_error "Could not find virtual environment!"
    exit 1
fi

print_success "Virtual environment activated"

# Install Python dependencies if needed
if [ ! -f "venv/pyvenv.cfg" ] || [ "requirements.txt" -nt "venv/pyvenv.cfg" ]; then
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Install Node.js dependencies if needed
if [ ! -d "cleo-web/node_modules" ] || [ "cleo-web/package.json" -nt "cleo-web/node_modules" ]; then
    print_status "Installing Node.js dependencies..."
    cd cleo-web
    npm install
    cd ..
fi

# Check and handle port conflicts
BACKEND_PORT=8000
FRONTEND_PORT=3000

if check_port $BACKEND_PORT; then
    print_warning "Port $BACKEND_PORT is already in use"
    read -p "Do you want to kill the process on port $BACKEND_PORT? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port $BACKEND_PORT
    else
        print_error "Cannot start backend on port $BACKEND_PORT"
        exit 1
    fi
fi

if check_port $FRONTEND_PORT; then
    print_warning "Port $FRONTEND_PORT is already in use"
    read -p "Do you want to kill the process on port $FRONTEND_PORT? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port $FRONTEND_PORT
    else
        print_error "Cannot start frontend on port $FRONTEND_PORT"
        exit 1
    fi
fi

# Run Django migrations
print_status "Running Django migrations..."
python manage.py migrate

# Create superuser if needed (optional)
read -p "Do you want to create a Django superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

# Start Redis (if available)
if command -v redis-server &> /dev/null; then
    if ! pgrep -x "redis-server" > /dev/null; then
        print_status "Starting Redis server..."
        redis-server --daemonize yes
    else
        print_success "Redis server is already running"
    fi
else
    print_warning "Redis not found. Some features may not work without Redis."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to cleanup background processes
cleanup() {
    print_status "Cleaning up background processes..."
    jobs -p | xargs -r kill
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Django backend
print_status "Starting Django backend on port $BACKEND_PORT..."
python manage.py runserver 0.0.0.0:$BACKEND_PORT > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if ! check_port $BACKEND_PORT; then
    print_error "Backend failed to start. Check logs/backend.log"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Backend started successfully on http://localhost:$BACKEND_PORT"

# Start Next.js frontend
print_status "Starting Next.js frontend on port $FRONTEND_PORT..."
cd cleo-web
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 5

# Check if frontend started successfully
if ! check_port $FRONTEND_PORT; then
    print_error "Frontend failed to start. Check logs/frontend.log"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

print_success "Frontend started successfully on http://localhost:$FRONTEND_PORT"

# Display access information
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Crypto Platform is now running!                   ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Frontend:  http://localhost:3000                           ║"
echo "║  Backend:   http://localhost:8000                           ║"
echo "║  API Docs:  http://localhost:8000/api/docs/                 ║"
echo "║  Admin:     http://localhost:8000/admin/                    ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Logs: Backend: logs/backend.log                            ║"
echo "║        Frontend: logs/frontend.log                          ║"
echo "║                                                              ║"
echo "║  Press Ctrl+C to stop both servers                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Wait for user to stop the servers
print_status "Servers are running. Press Ctrl+C to stop all services..."

# Keep the script running and wait for interrupt
while true; do
    # Check if both processes are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend process has stopped unexpectedly"
        kill $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend process has stopped unexpectedly"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    
    sleep 2
done

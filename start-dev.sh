#!/bin/bash

# Quick Development Starter Script
# Simplified version for rapid development

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Crypto Platform Development Environment${NC}"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠ No virtual environment found${NC}"
fi

# Kill existing processes
echo -e "${BLUE}🔄 Stopping any existing servers...${NC}"
pkill -f "manage.py runserver" || true
pkill -f "next dev" || true
sleep 2

# Start backend
echo -e "${BLUE}🐍 Starting Django backend...${NC}"
python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!

# Start frontend
echo -e "${BLUE}⚛️  Starting Next.js frontend...${NC}"
cd cleo-web
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for servers to start
sleep 5

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Cleo Platform is running!                          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Frontend:  http://localhost:3000                           ║"
echo "║  Backend:   http://localhost:8000                           ║"
echo "║  API Docs:  http://localhost:8000/api/docs/                 ║"
echo "║                                                              ║"
echo "║  Press Ctrl+C to stop both servers                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Wait for interrupt
trap "echo -e '${BLUE}🛑 Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

wait

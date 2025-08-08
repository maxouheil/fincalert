#!/bin/bash

# Kill any existing processes on the ports
echo "Stopping existing servers..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "npm.*start.*3001" 2>/dev/null || true

# Start backend in background
echo "Starting backend server..."
./start-backend.sh > backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "Starting frontend server..."
./start-frontend.sh > frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Servers started!"
echo "Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo "Frontend: http://localhost:3001 (PID: $FRONTEND_PID)"
echo ""
echo "To stop servers: ./stop-all.sh"
echo "To view logs: tail -f backend.log frontend.log"

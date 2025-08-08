#!/bin/bash

echo "Stopping all servers..."

# Kill backend processes
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true

# Kill frontend processes
pkill -f "npm.*start.*3001" 2>/dev/null || true
pkill -f "node.*react-scripts" 2>/dev/null || true

# Kill processes on specific ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

echo "All servers stopped!"

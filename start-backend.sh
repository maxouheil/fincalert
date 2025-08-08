#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH=$(pwd)/backend

# Install dependencies if needed
pip install -q -r requirements.txt

# Start the FastAPI server
echo "Starting backend server on http://localhost:8000"
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

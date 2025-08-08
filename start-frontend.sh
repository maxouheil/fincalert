#!/bin/bash

# Navigate to frontend directory
cd frontend

# Install dependencies if needed
npm install --silent --no-audit --no-fund

# Start the React dev server
echo "Starting frontend server on http://localhost:3001"
PORT=3001 BROWSER=none npm start

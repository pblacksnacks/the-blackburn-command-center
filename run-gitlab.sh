#!/bin/bash
# Run the Blackburn Command Center in GitLab mode
# Uses separate database and ports from the Anthropic instance

export TRIAGE_DB="triage_gitlab.db"
export GITLAB_MODE="true"

echo "=== Blackburn Command Center — GitLab Mode ==="
echo "Database: triage_gitlab.db"
echo "Backend: http://localhost:8001"
echo "Frontend: http://localhost:5174"
echo ""

if [ "$1" = "init" ]; then
    echo "Initializing GitLab pipeline..."
    python main.py full --demo
    echo "Done! Now run: ./run-gitlab.sh"
    exit 0
fi

# Start backend on port 8001
echo "Starting backend on port 8001..."
venv/bin/uvicorn server.app:app --reload --port 8001 &
BACKEND_PID=$!

# Start frontend on port 5174, pointing to backend port 8001
echo "Starting frontend on port 5174..."
cd web && VITE_API_PORT=8001 npm run dev -- --port 5174 &
FRONTEND_PID=$!

echo ""
echo "GitLab mode running!"
echo "Open: http://localhost:5174"
echo "Press Ctrl+C to stop"

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

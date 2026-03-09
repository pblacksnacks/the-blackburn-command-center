#!/bin/bash
# Run the Blackburn Command Center in Anthropic mode
# Default database and ports

export TRIAGE_DB="triage.db"

echo "=== Blackburn Command Center — Anthropic Mode ==="
echo "Database: triage.db"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""

if [ "$1" = "init" ]; then
    echo "Initializing Anthropic pipeline..."
    python main.py full --demo
    echo "Done! Now run: ./run-anthropic.sh"
    exit 0
fi

echo "Starting backend on port 8000..."
venv/bin/uvicorn server.app:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting frontend on port 5173..."
cd web && npm run dev &
FRONTEND_PID=$!

echo ""
echo "Anthropic mode running!"
echo "Open: http://localhost:5173"
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

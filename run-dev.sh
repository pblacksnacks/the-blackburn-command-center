#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Save original PATH so venv activation doesn't lose Node ---
ORIGINAL_PATH="$PATH"

# --- Python venv ---
if [ ! -d "venv" ]; then
    echo "Creating Python venv..."
    python3 -m venv venv
fi
source venv/bin/activate

# Restore full PATH (venv prepends, but we also need Node/npm)
export PATH="$VIRTUAL_ENV/bin:$ORIGINAL_PATH"

# Find Node — try common macOS locations
if ! command -v node &>/dev/null; then
    for p in /opt/homebrew/bin /usr/local/bin "$HOME/.nvm/versions/node"/*/bin; do
        if [ -x "$p/node" ]; then
            export PATH="$p:$PATH"
            break
        fi
    done
fi

if ! command -v node &>/dev/null; then
    echo "ERROR: node not found. Install Node.js >= 18 first."
    exit 1
fi

echo "  Using Python: $(python --version) at $(which python)"
echo "  Using Node:   $(node --version) at $(which node)"

if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# --- Node deps ---
if [ ! -d "web/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd web && npm install)
fi

# --- .env check ---
if [ ! -f ".env" ]; then
    echo "No .env file found. Copy .env.example and fill in your keys:"
    echo "  cp .env.example .env"
    exit 1
fi

# --- CLI mode: forward to main.py ---
if [ $# -gt 0 ]; then
    python main.py "$@"
    exit 0
fi

# --- Dev server mode (no args) ---
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "  Starting Email Triage Dashboard"
echo "  Backend:  http://localhost:8000  (API docs: http://localhost:8000/docs)"
echo "  Frontend: http://localhost:5173"
echo ""

# Start FastAPI
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start Vite (call binary directly — avoids npm/npx PATH issues)
VITE_BIN="$SCRIPT_DIR/web/node_modules/.bin/vite"
if [ ! -x "$VITE_BIN" ]; then
    echo "ERROR: Vite not found. Run: cd web && npm install"
    exit 1
fi
(cd web && node "$VITE_BIN" --host 0.0.0.0 --port 5173) &
FRONTEND_PID=$!

# Wait for Vite to be ready, then open browser
sleep 3
open "http://localhost:5173" 2>/dev/null || xdg-open "http://localhost:5173" 2>/dev/null || true

wait

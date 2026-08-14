#!/bin/bash
# ====================================================================
# Continuous Enterprise AI Governance - Control Plane Launcher
# Starts FastAPI Proxy (:8000) and Enterprise Dashboard (:5173)
# ====================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "===================================================================="
echo " Starting Continuous Enterprise AI Governance Control Plane"
echo " (EU AI Act Article 26, GDPR Article 44, ANSSI Compliant)"
echo "===================================================================="

# 1. Start Python FastAPI Backend & Reverse Proxy
echo "[1/2] Launching On-Premise Governance Backend on http://localhost:8000 ..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Start Frontend Dev Server
echo "[2/2] Launching Executive Dashboard & Playground on http://localhost:5173 ..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "--------------------------------------------------------------------"
echo "  🚀 All Services Active!"
echo "  👉 Dashboard & Pitch Deck:  http://localhost:5173"
echo "  👉 Governance Proxy:        http://localhost:8000/v1"
echo "  👉 Interactive API Docs:    http://localhost:8000/docs"
echo "--------------------------------------------------------------------"
echo "Press Ctrl+C to terminate all services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait

#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Launching RideShield full stack..."

"${SCRIPT_DIR}/run_dev.sh" &
BACKEND_PID=$!

sleep 5

"${SCRIPT_DIR}/run_frontend.sh" &
FRONTEND_PID=$!

echo "Backend PID: ${BACKEND_PID}"
echo "Frontend PID: ${FRONTEND_PID}"
echo "Backend:  http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"

wait

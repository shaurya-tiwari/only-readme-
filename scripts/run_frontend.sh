#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

if [ ! -d "${FRONTEND_DIR}" ]; then
    echo "Frontend directory not found at ${FRONTEND_DIR}"
    exit 1
fi

echo "Starting RideShield frontend..."
cd "${FRONTEND_DIR}"

if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting Vite frontend on http://localhost:3000 ..."
exec npm run dev

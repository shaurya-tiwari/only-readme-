#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Starting RideShield development environment..."

if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

echo "Starting PostgreSQL..."
cd "${ROOT_DIR}"
docker-compose up -d db
sleep 3

echo "Waiting for database..."
until docker-compose exec -T db pg_isready -U rideshield -d rideshield_db > /dev/null 2>&1; do
    sleep 1
done
echo "Database ready"

if [ -f "${ROOT_DIR}/venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/venv/bin/activate"
elif [ ! -f "${ROOT_DIR}/venv/Scripts/Activate.ps1" ]; then
    echo "Virtual environment not found at ${ROOT_DIR}/venv."
    exit 1
fi

unset DEBUG
unset DATABASE_URL
unset DATABASE_URL_SYNC

echo "Starting FastAPI backend..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

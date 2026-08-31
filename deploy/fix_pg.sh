#!/bin/bash
echo 9090 | sudo -S -u postgres psql << 'SQL'
DROP USER IF EXISTS eitp;
CREATE USER eitp WITH PASSWORD 'eitp_dev' SUPERUSER;
DROP DATABASE IF EXISTS eitp_dev;
CREATE DATABASE eitp_dev OWNER eitp;
GRANT ALL PRIVILEGES ON DATABASE eitp_dev TO eitp;
SQL
echo "PG fixed"

cd /home/debian/EITP/backend
source .venv/bin/activate
export DB_URL="postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev"
export REDIS_URL="redis://localhost:6379/0"
alembic upgrade head 2>&1 | tail -10
echo "Migrations done"

pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1
export PLACEMENT_MODE="shared_db"
export LOG_LEVEL="info"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /home/debian/eitp-backend.log 2>&1 &
echo "Backend PID: $!"
sleep 3
curl -s http://localhost:8000/health 2>&1
echo ""
echo "Backend started"
#!/bin/bash
echo "=== Creating .env ==="
cat > /home/debian/EITP/backend/.env << 'EOF'
EITP_DEBUG=false
EITP_DATABASE_URL=postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev
EITP_DB_POOL_SIZE=20
EITP_DB_MAX_OVERFLOW=10
EITP_DB_POOL_RECYCLE=3600
EITP_REDIS_URL=redis://localhost:6379/0
EITP_CONTROL_PLANE_URL=http://localhost:8090
EITP_LOG_LEVEL=INFO
EITP_LOG_JSON=true
EOF
echo ".env created"

echo "=== Running migrations ==="
cd /home/debian/EITP/backend
source .venv/bin/activate
alembic upgrade head 2>&1 | tail -10
echo "Migrations done"

echo "=== Restarting backend ==="
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 2
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /home/debian/eitp-backend.log 2>&1 &
echo "Backend PID: $!"
sleep 3

echo "=== Testing API ==="
curl -s http://localhost:8000/health
echo ""
curl -s -H "X-Tenant-Token: 00000000-0000-0000-0000-000000000001" http://localhost:8000/api/v1/tenant/hierarchy/tree 2>&1
echo ""
echo "=== DONE ==="
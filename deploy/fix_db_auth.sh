#!/bin/bash
echo "=== Fixing PostgreSQL authentication ==="

# Find PostgreSQL config directory
PG_CONF=$(echo 9090 | sudo -S -u postgres psql -tAc "SHOW hba_file;" 2>/dev/null)
PG_DIR=$(dirname "$PG_CONF")
echo "PG hba dir: $PG_DIR"

# Set password with proper encryption
echo 9090 | sudo -S -u postgres psql -c "ALTER USER eitp WITH PASSWORD 'eitp_dev';" 2>&1

# Fix pg_hba.conf - allow password auth for all local TCP connections
echo 9090 | sudo -S bash -c "cat > $PG_DIR/pg_hba.conf << 'EOF'
local   all   all   trust
host    all   all   127.0.0.1/32   md5
host    all   all   ::1/128        md5
host    all   all   0.0.0.0/0      md5
EOF"

echo 9090 | sudo -S systemctl restart postgresql
sleep 2

echo "=== Testing DB connection ==="
echo 9090 | sudo -S -u postgres psql -c "SELECT usename FROM pg_user WHERE usename='eitp';" 2>&1
PGPASSWORD=eitp_dev psql -h 127.0.0.1 -U eitp -d eitp_dev -c "SELECT 1 AS test;" 2>&1

echo "=== Restarting backend ==="
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 2
cd /home/debian/EITP/backend
source .venv/bin/activate
export DB_URL="postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev"
export REDIS_URL="redis://localhost:6379/0"
export PLACEMENT_MODE="shared_db"
export LOG_LEVEL="info"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /home/debian/eitp-backend.log 2>&1 &
echo "Backend PID: $!"
sleep 3

echo "=== Testing API ==="
curl -s http://localhost:8000/health
echo ""
curl -s -H "X-Tenant-Token: 00000000-0000-0000-0000-000000000001" http://localhost:8000/api/v1/tenant/hierarchy/tree 2>&1
echo ""
echo "=== DONE ==="
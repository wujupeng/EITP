#!/bin/bash
echo "=== Fixing PostgreSQL auth ==="
echo 9090 | sudo -S bash -c 'cat > /etc/postgresql/17/main/pg_hba.conf << EOF
local   all   all   peer
host    all   all   127.0.0.1/32   scram-sha-256
host    all   all   ::1/128        scram-sha-256
EOF'
echo 9090 | sudo -S systemctl restart postgresql
sleep 2

echo "=== Testing DB connection ==="
cd /home/debian/EITP/backend
source .venv/bin/activate
export DB_URL="postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev"
alembic upgrade head 2>&1 | tail -5
echo "Migrations done"

echo "=== Restarting backend ==="
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1
export REDIS_URL="redis://localhost:6379/0"
export PLACEMENT_MODE="shared_db"
export LOG_LEVEL="info"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /home/debian/eitp-backend.log 2>&1 &
sleep 3
curl -s http://localhost:8000/health
echo ""

echo "=== Building frontend ==="
cd /home/debian/EITP/frontend
npm install @types/node --save-dev 2>&1 | tail -2
npm run build 2>&1 | tail -5
ls dist/ 2>&1 | head -5
echo "Frontend done"

echo "=== Installing Go ==="
if ! command -v go &>/dev/null; then
  wget -q https://go.dev/dl/go1.22.12.linux-amd64.tar.gz -O /tmp/go.tar.gz 2>&1
  echo 9090 | sudo -S tar -C /usr/local -xzf /tmp/go.tar.gz
fi
export PATH=$PATH:/usr/local/go/bin
go version

echo "=== Building control-plane ==="
cd /home/debian/EITP/control-plane
CGO_ENABLED=0 go build -o control-plane ./cmd/server 2>&1
echo "Control-plane built"

pkill -f "control-plane" 2>/dev/null || true
export DB_URL="postgres://eitp:eitp_dev@localhost:5432/eitp_dev"
nohup ./control-plane > /home/debian/eitp-control.log 2>&1 &
echo "Control-plane PID: $!"

echo "=== Restarting nginx ==="
echo 9090 | sudo -S systemctl restart nginx
sleep 1

echo "=== Final verification ==="
curl -s http://localhost:8000/health
echo ""
curl -s -o /dev/null -w "Frontend: %{http_code}" http://localhost:80/
echo ""
echo "=== DONE ==="
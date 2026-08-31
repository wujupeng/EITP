#!/bin/bash
set -e

echo "=== Installing PostgreSQL and Redis ==="
echo 9090 | sudo -S apt-get install -y -qq postgresql postgresql-contrib redis-server 2>&1 | tail -3

echo "=== Configuring PostgreSQL ==="
echo 9090 | sudo -S systemctl start postgresql 2>&1
echo 9090 | sudo -S systemctl enable postgresql 2>&1
sleep 2
echo 9090 | sudo -S -u postgres psql -c "CREATE USER eitp WITH PASSWORD 'eitp_dev' SUPERUSER;" 2>&1 || true
echo 9090 | sudo -S -u postgres psql -c "CREATE DATABASE eitp_dev OWNER eitp;" 2>&1 || true
echo "PostgreSQL configured"

echo "=== Starting Redis ==="
echo 9090 | sudo -S systemctl start redis-server 2>&1
echo 9090 | sudo -S systemctl enable redis-server 2>&1
echo "Redis started"

echo "=== Setting up Python backend ==="
cd /home/debian/EITP/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel -q
pip install fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg alembic pydantic pydantic-settings python-json-logger structlog redis httpx -q 2>&1 | tail -3
echo "Python deps installed"

echo "=== Running migrations ==="
cd /home/debian/EITP/backend
source .venv/bin/activate
export DB_URL="postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev"
export REDIS_URL="redis://localhost:6379/0"
alembic upgrade head 2>&1 | tail -5
echo "Migrations done"

echo "=== Setting up frontend ==="
cd /home/debian/EITP/frontend
npm install @types/node --save-dev 2>&1 | tail -2
npm run build 2>&1 | tail -5
echo "Frontend built: $(ls dist/ 2>&1 | head -5)"

echo "=== Installing Go ==="
if ! command -v go &>/dev/null; then
  wget -q https://go.dev/dl/go1.22.12.linux-amd64.tar.gz -O /tmp/go.tar.gz
  echo 9090 | sudo -S tar -C /usr/local -xzf /tmp/go.tar.gz
fi
export PATH=$PATH:/usr/local/go/bin
go version

echo "=== Building control-plane ==="
cd /home/debian/EITP/control-plane
CGO_ENABLED=0 go build -o control-plane ./cmd/server 2>&1
echo "Control-plane built"

echo "=== Starting backend ==="
pkill -f "uvicorn app.main" 2>/dev/null || true
cd /home/debian/EITP/backend
source .venv/bin/activate
export DB_URL="postgresql+asyncpg://eitp:eitp_dev@localhost:5432/eitp_dev"
export REDIS_URL="redis://localhost:6379/0"
export PLACEMENT_MODE="shared_db"
export LOG_LEVEL="info"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /home/debian/eitp-backend.log 2>&1 &
echo "Backend PID: $!"

echo "=== Starting control-plane ==="
pkill -f "control-plane" 2>/dev/null || true
cd /home/debian/EITP/control-plane
export DB_URL="postgres://eitp:eitp_dev@localhost:5432/eitp_dev"
nohup ./control-plane > /home/debian/eitp-control.log 2>&1 &
echo "Control-plane PID: $!"

sleep 3

echo "=== Setting up nginx ==="
echo 9090 | sudo -S apt-get install -y -qq nginx 2>&1 | tail -1
echo 9090 | sudo -S bash -c 'cat > /etc/nginx/sites-available/eitp << '"'"'EOF'"'"'
server {
    listen 80;
    server_name _;
    root /home/debian/EITP/frontend/dist;
    index index.html;
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Tenant-Token $http_x_tenant_token;
    }
    location /health { proxy_pass http://127.0.0.1:8000; }
    location /docs { proxy_pass http://127.0.0.1:8000; }
    location /openapi.json { proxy_pass http://127.0.0.1:8000; }
    location / { try_files $uri $uri/ /index.html; }
}
EOF'
echo 9090 | sudo -S ln -sf /etc/nginx/sites-available/eitp /etc/nginx/sites-enabled/eitp
echo 9090 | sudo -S rm -f /etc/nginx/sites-enabled/default
echo 9090 | sudo -S nginx -t 2>&1
echo 9090 | sudo -S systemctl restart nginx
echo "Nginx started"

sleep 2
echo "=== Verifying ==="
curl -s http://localhost:8000/health 2>&1
echo ""
curl -s -o /dev/null -w "Frontend HTTP: %{http_code}" http://localhost:80/ 2>&1
echo ""

echo "=== DEPLOYMENT COMPLETE ==="
echo "Backend:    http://192.168.1.70:8000"
echo "Frontend:   http://192.168.1.70"
echo "API Docs:   http://192.168.1.70:8000/docs"
echo "Health:     http://192.168.1.70:8000/health"

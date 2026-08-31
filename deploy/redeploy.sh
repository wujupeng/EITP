#!/bin/bash
echo "=== Rebuilding frontend ==="
cd /home/debian/EITP/frontend
npm run build 2>&1 | tail -5
echo "Frontend rebuilt: $(ls dist/ 2>&1 | head -3)"

echo "=== Restarting backend ==="
pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 2
cd /home/debian/EITP/backend
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /home/debian/eitp-backend.log 2>&1 &
echo "Backend PID: $!"
sleep 3

echo "=== Testing ==="
curl -s http://localhost:8000/health
echo ""
curl -s -o /dev/null -w "Frontend: %{http_code}" http://localhost:80/
echo ""
curl -s -o /dev/null -w "API no token: %{http_code}" http://localhost:80/api/v1/tenant/hierarchy/tree
echo ""
curl -s -H "X-Tenant-Token: 00000000-0000-0000-0000-000000000001" http://localhost:80/api/v1/tenant/hierarchy/tree
echo ""
echo "=== DONE ==="
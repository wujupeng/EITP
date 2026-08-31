#!/bin/bash
export PATH=$PATH:/usr/local/go/bin

echo "=== Building control-plane ==="
cd /home/debian/EITP/control-plane
CGO_ENABLED=0 go build -o control-plane ./cmd/server 2>&1
ls -la control-plane
echo "Control-plane built"

pkill -f "control-plane" 2>/dev/null || true
export DB_URL="postgres://eitp:eitp_dev@localhost:5432/eitp_dev"
nohup ./control-plane > /home/debian/eitp-control.log 2>&1 &
echo "Control-plane PID: $!"
sleep 2

echo "=== Fixing nginx ==="
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
echo 9090 | sudo -S systemctl restart nginx 2>&1
sleep 1

echo "=== Final verification ==="
echo "Backend health:"
curl -s http://localhost:8000/health
echo ""
echo "Frontend:"
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:80/
echo ""
echo "API via nginx:"
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:80/health
echo ""
echo "Control-plane:"
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8081/ 2>&1 || echo "not ready"
echo ""
echo "=== ALL DONE ==="
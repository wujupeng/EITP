#!/bin/bash
echo 9090 | sudo -S tee /etc/nginx/sites-available/eitp > /dev/null << 'EOF'
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
EOF
echo 9090 | sudo -S ln -sf /etc/nginx/sites-available/eitp /etc/nginx/sites-enabled/eitp
echo 9090 | sudo -S rm -f /etc/nginx/sites-enabled/default
echo 9090 | sudo -S nginx -t 2>&1
echo 9090 | sudo -S systemctl restart nginx
sleep 1
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost:80/
curl -s http://localhost:80/health
echo ""
echo "NGINX DONE"
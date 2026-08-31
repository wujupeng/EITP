#!/bin/bash
echo "=== Creating eitp_control DB ==="
echo 9090 | sudo -S -u postgres psql -c "CREATE DATABASE eitp_control OWNER eitp;" 2>&1 || true

echo "=== Killing old processes ==="
pkill -f "control-plane" 2>/dev/null || true
echo 9090 | sudo -S fuser -k 8090/tcp 2>/dev/null || true
sleep 2

echo "=== Starting control-plane ==="
cd /home/debian/EITP/control-plane
export DB_URL="postgres://eitp:eitp_dev@localhost:5432/eitp_control"
nohup ./control-plane > /home/debian/eitp-control.log 2>&1 &
PID=$!
echo "PID: $PID"
sleep 3
if kill -0 $PID 2>/dev/null; then
  echo "RUNNING"
else
  echo "FAILED"
fi
tail -3 /home/debian/eitp-control.log 2>&1
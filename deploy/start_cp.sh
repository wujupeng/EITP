#!/bin/bash
cd /home/debian/EITP/control-plane
chmod +x control-plane
pkill -f "control-plane" 2>/dev/null || true
sleep 1
export DB_URL="postgres://eitp:eitp_dev@localhost:5432/eitp_dev"
nohup ./control-plane > /home/debian/eitp-control.log 2>&1 &
PID=$!
echo "Started PID: $PID"
sleep 2
if kill -0 $PID 2>/dev/null; then
  echo "Control-plane is running"
else
  echo "Control-plane failed to start"
fi
cat /home/debian/eitp-control.log 2>&1
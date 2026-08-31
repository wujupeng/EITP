#!/bin/bash
export PATH=$PATH:/usr/local/go/bin
cd /home/debian/EITP/control-plane
echo "Building control-plane..."
CGO_ENABLED=0 go build -o control-plane ./cmd/server 2>&1
echo "Build exit: $?"
ls -la control-plane 2>&1
if [ -f control-plane ]; then
  pkill -f "control-plane" 2>/dev/null || true
  export DB_URL="postgres://eitp:eitp_dev@localhost:5432/eitp_dev"
  nohup ./control-plane > /home/debian/eitp-control.log 2>&1 &
  echo "Control-plane PID: $!"
  sleep 2
  tail -3 /home/debian/eitp-control.log 2>&1
fi
echo "CONTROL PLANE DONE"
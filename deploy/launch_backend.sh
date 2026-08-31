#!/bin/bash
pkill -f uvicorn 2>/dev/null
sleep 1
nohup bash /home/debian/EITP/start_backend.sh > /home/debian/eitp-backend.log 2>&1 &
echo $!
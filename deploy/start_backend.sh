#!/bin/bash
cd /home/debian/EITP/backend
export EITP_JWT_PRIVATE_KEY_FILE=/home/debian/EITP/backend/jwt_private_key.pem
export EITP_JWT_PUBLIC_KEY_FILE=/home/debian/EITP/backend/jwt_public_key.pem
export EITP_JWT_KEY_ID=iam-key-v1
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
#!/bin/bash
# EITP-PUR-001 部署脚本 - 在服务器 192.168.1.70 上执行
# 用法: ssh debian@192.168.1.70 'bash -s' < deploy_pur_001.sh

set -e
cd /home/debian/EITP

echo "=== EITP-PUR-001 部署开始 ==="

# 1. 拉取最新代码
echo "[1/6] 拉取最新代码..."
git pull origin main

# 2. 安装后端依赖
echo "[2/6] 安装后端依赖..."
cd backend
pip install -e ".[dev]" 2>/dev/null || pip install -e .

# 3. 运行数据库迁移
echo "[3/6] 运行数据库迁移 036-037..."
alembic upgrade head

# 4. 运行单元测试
echo "[4/6] 运行 PUR 单元测试..."
python -m pytest tests/unit/test_pur_*.py -v --tb=short

# 5. 重启 FastAPI 服务
echo "[5/6] 重启 FastAPI 服务..."
cd /home/debian/EITP
if systemctl is-active --quiet eitp-backend; then
    sudo systemctl restart eitp-backend
    echo "  systemd 服务已重启"
else
    # 杀掉旧进程并重启
    pkill -f "uvicorn app.main:app" || true
    sleep 2
    cd backend
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/eitp-backend.log 2>&1 &
    echo "  uvicorn#uvicorn 进程已重启 (PID: $!)"
fi

# 6. 验证 PUR API 端点
echo "[6/6] 验证 PUR API 端点..."
sleep 3
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
echo "  Health check: $HEALTH"

# 验证 PUR 路由已注册
PUR_SUPPLIERS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/pur/suppliers)
echo "  PUR suppliers endpoint: $PUR_SUPPLIERS"

PUR_ORDERS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/pur/orders)
echo "  PUR orders endpoint: $PUR_ORDERS"

echo ""
echo "=== EITP-PUR-001 部署完成 ==="
echo ""
echo "下一步: 运行 E2E 测试"
echo "  cd backend"
echo "  python -m pytest tests/e2e/golden_path/test_pur_golden_path.py -v"
echo "  python -m pytest tests/e2e/test_pur_tenant_isolation.py -v"
"""P0 Evidence: 启动 FastAPI + 运行 E2E + 验证失败场景。"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.70', username='debian', password='9090', timeout=10)

def run_cmd(cmd, timeout=120):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err and len(err) > 5:
        print(f"[STDERR] {err[-500:]}")
    return out, err

print("=" * 60)
print("P0-1: 启动 FastAPI 服务")
print("=" * 60)

# 先杀掉可能存在的旧进程
run_cmd("pkill -f 'uvicorn app.main' 2>/dev/null; sleep 1; echo 'killed old process'")

# 启动 FastAPI 服务（后台）
run_cmd("cd /home/debian/EITP/backend && nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/wms_e2e_server.log 2>&1 & echo 'Server starting...'")
time.sleep(5)

# 验证服务已启动
run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/health 2>/dev/null || echo 'health check failed'")
run_cmd("curl -s http://localhost:8000/api/v1/health 2>/dev/null | head -5")
run_cmd("tail -5 /tmp/wms_e2e_server.log 2>/dev/null")

print("\n" + "=" * 60)
print("P0-2: 运行 WMS Golden Path E2E")
print("=" * 60)

# 运行 E2E 黄金链路测试
run_cmd("cd /home/debian/EITP/backend && .venv/bin/python -m pytest tests/e2e/golden_path/test_wms_golden_path.py -v --tb=long 2>&1 | tail -40", timeout=120)

ssh.close()
print("\n=== P0-1 & P0-2 Done ===")
"""查看完整启动错误日志并修复。"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.70', username='debian', password='9090', timeout=10)

def run_cmd(cmd, timeout=30):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    return out, err

run_cmd("cat /tmp/wms_e2e_server.log 2>/dev/null | head -50")
run_cmd("cd /home/debian/EITP/backend && grep -rn 'error=' app/logging_config.py 2>/dev/null | head -10")
run_cmd("cd /home/debian/EITP/backend && grep -rn '\\.warning.*error=' app/ 2>/dev/null | head -10")
run_cmd("cd /home/debian/EITP/backend && grep -rn '\\.error.*error=' app/ 2>/dev/null | head -10")
run_cmd("cd /home/debian/EITP/backend && grep -rn '\\.info.*error=' app/ 2>/dev/null | head -10")

ssh.close()
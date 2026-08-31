"""SSH 远程执行辅助脚本 - 使用 paramiko 提供密码认证。

用法: python deploy/ssh_exec.py "remote command"
"""
import sys
import paramiko

HOST = "192.168.1.70"
USER = "debian"
PASSWORD = "9090"

def run(cmd: str, timeout: int = 30) -> None:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=HOST,
        username=USER,
        password=PASSWORD,
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if out:
        print(out, end="")
    if err:
        print(f"[STDERR] {err}", end="", file=sys.stderr)
    client.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy/ssh_exec.py 'command'", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1])
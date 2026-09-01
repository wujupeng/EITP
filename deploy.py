import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.70', username='debian', password='9090', timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    print(f'CMD: {cmd[:80]}')
    if out.strip(): print(f'OUT: {out.strip()[-500:]}')
    if err.strip(): print(f'ERR: {err.strip()[-500:]}')
    print(f'EXIT: {code}')
    print('---')
    return code

sftp = ssh.open_sftp()
with sftp.file('/home/debian/EITP/start.sh', 'w') as f:
    f.write('#!/bin/bash\ncd /home/debian/EITP/backend\nset -a\nsource .env\nset +a\nexec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000\n')
sftp.chmod('/home/debian/EITP/start.sh', 0o755)
sftp.close()
print('start.sh created')

run('pkill -f uvicorn; sleep 2; echo killed', timeout=10)
run('nohup /home/debian/EITP/start.sh > /tmp/eitp.log 2>&1 & disown; echo launched', timeout=10)
time.sleep(8)
run('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health', timeout=15)
run('pgrep -f uvicorn', timeout=10)
run('tail -3 /tmp/eitp.log', timeout=10)

ssh.close()
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.70', username='debian', password='9090', timeout=15)

def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    print(f'CMD: {cmd[:80]}')
    if out.strip(): print(f'OUT: {out.strip()[-800:]}')
    if err.strip(): print(f'ERR: {err.strip()[-800:]}')
    print(f'EXIT: {code}')
    print('---')
    return code

print('=== Building frontend ===')
run('cd /home/debian/EITP/frontend && npm run build 2>&1', timeout=180)

print('=== Verifying build ===')
run('ls -la /home/debian/EITP/frontend/dist/ 2>&1')

print('=== Verifying app still running ===')
run('pgrep -f uvicorn 2>&1')
run('curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>&1')

print('=== Checking SEC tables in database ===')
run('cd /home/debian/EITP/backend && source .venv/bin/activate && set -a && source .env && set +a && python -c "import asyncio; from sqlalchemy import text; from sqlalchemy.ext.asyncio import create_async_engine; async def main(): e=create_async_engine(__import__(\"os\").environ[\"EITP_DATABASE_URL\"]); r=await e.execute(text(\"SELECT tablename FROM pg_tables WHERE tablename LIKE \'sec_%\' ORDER BY tablename\")); print([row[0] for row in r]); await e.dispose(); asyncio.run(main())" 2>&1', timeout=30)

ssh.close()
print('=== Deployment complete ===')
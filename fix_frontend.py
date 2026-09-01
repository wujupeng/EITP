import paramiko, time, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.70', username='debian', password='9090', timeout=15)

sftp = ssh.open_sftp()

files = [
    'frontend/src/pages/sec/attack_chain.tsx',
    'frontend/src/pages/sec/config.tsx',
    'frontend/src/pages/sec/execute.tsx',
    'frontend/src/pages/sec/report_detail.tsx',
    'frontend/src/pages/sec/reports.tsx',
]

for f in files:
    local = os.path.join('C:\\Users\\DELL\\Documents\\dev\\EITP', f).replace('\\', '/')
    remote = f'/home/debian/EITP/{f}'
    sftp.put(local, remote)
    print(f'Uploaded: {f}')

sftp.close()
print('All files uploaded')

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

print('=== Rebuilding frontend ===')
run('cd /home/debian/EITP/frontend && npm run build 2>&1', timeout=180)

print('=== Verifying build ===')
run('ls -la /home/debian/EITP/frontend/dist/assets/ 2>&1')

ssh.close()
print('=== Done ===')
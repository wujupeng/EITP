"""SFTP 文件传输辅助脚本 - 使用 paramiko 上传文件到服务器。

用法: python deploy/ssh_upload.py <local_path> <remote_path>
"""
import sys
import os
import paramiko

HOST = "192.168.1.70"
USER = "debian"
PASSWORD = "9090"

def upload(local_path: str, remote_path: str) -> None:
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
    sftp = client.open_sftp()

    if os.path.isdir(local_path):
        _upload_dir(sftp, local_path, remote_path)
    else:
        _ensure_remote_dir(sftp, remote_path)
        sftp.put(local_path, remote_path)
        print(f"  uploaded: {local_path} -> {remote_path}")

    sftp.close()
    client.close()

def _ensure_remote_dir(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    remote_dir = os.path.dirname(remote_path).replace("\\", "/")
    parts = remote_dir.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current = current + "/" + part if current else "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)

def _upload_dir(sftp: paramiko.SFTPClient, local_dir: str, remote_dir: str) -> None:
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        _mkdirs(sftp, remote_dir)

    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = remote_dir + "/" + item
        if os.path.isdir(local_path):
            _upload_dir(sftp, local_path, remote_path)
        else:
            sftp.put(local_path, remote_path)
            print(f"  uploaded: {local_path} -> {remote_path}")

def _mkdirs(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current = current + "/" + part if current else "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python deploy/ssh_upload.py <local_path> <remote_path>", file=sys.stderr)
        sys.exit(1)
    upload(sys.argv[1], sys.argv[2])
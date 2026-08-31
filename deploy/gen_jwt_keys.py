"""生成 JWT RS256 密钥对并写入文件。"""
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

priv_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

pub_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

with open("/home/debian/EITP/backend/jwt_private_key.pem", "wb") as f:
    f.write(priv_pem)

with open("/home/debian/EITP/backend/jwt_public_key.pem", "wb") as f:
    f.write(pub_pem)

print("JWT keys written to:")
print("  /home/debian/EITP/backend/jwt_private_key.pem")
print("  /home/debian/EITP/backend/jwt_public_key.pem")

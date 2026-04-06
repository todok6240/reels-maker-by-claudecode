"""
AES-256-GCM 암호화/복호화 유틸리티
환경변수 DB_ENCRYPT_KEY (32바이트 hex) 필요
"""

import os
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def _get_key() -> bytes:
    raw = os.environ.get("DB_ENCRYPT_KEY", "")
    if len(raw) == 64:
        return bytes.fromhex(raw)
    # fallback: FLASK_SECRET_KEY 앞 32바이트 sha256
    import hashlib
    secret = os.environ.get("FLASK_SECRET_KEY", "default-insecure-key")
    return hashlib.sha256(secret.encode()).digest()


def encrypt(plaintext: str) -> str:
    """평문 문자열 → base64 암호문 (nonce:tag:ciphertext)"""
    if not plaintext:
        return ""
    key = _get_key()
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    blob = nonce + tag + ciphertext
    return base64.b64encode(blob).decode("ascii")


def decrypt(token: str) -> str:
    """base64 암호문 → 평문 문자열"""
    if not token:
        return ""
    try:
        key = _get_key()
        blob = base64.b64decode(token.encode("ascii"))
        nonce, tag, ciphertext = blob[:12], blob[12:28], blob[28:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
    except Exception:
        return ""

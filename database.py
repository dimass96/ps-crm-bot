import os
import json
from cryptography.fernet import Fernet
from datetime import datetime

DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "clients_db.json")
KEY_FILE = os.path.join(DATA_DIR, "secret.key")

def generate_key():
    if not os.path.exists(KEY_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)

def load_key():
    with open(KEY_FILE, "rb") as f:
        return f.read()

def encrypt_data(data: str, key: bytes) -> bytes:
    return Fernet(key).encrypt(data.encode())

def decrypt_data(token: bytes, key: bytes) -> str:
    return Fernet(key).decrypt(token).decode()

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "rb") as f:
        encrypted = f.read()
        if not encrypted:
            return []
        key = load_key()
        try:
            decrypted = decrypt_data(encrypted, key)
            return json.loads(decrypted)
        except Exception:
            return []

def save_db(data):
    key = load_key()
    encrypted = encrypt_data(json.dumps(data, ensure_ascii=False, indent=2), key)
    with open(DB_FILE, "wb") as f:
        f.write(encrypted)
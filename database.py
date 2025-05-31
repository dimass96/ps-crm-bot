import os
import json
from datetime import datetime
from cryptography.fernet import Fernet

DB_FILE = "/data/clients_db.json"
KEY_FILE = "/data/secret.key"
BACKUP_DIR = "/data/backups"
MAX_BACKUPS = 5

def generate_key():
    if not os.path.exists(KEY_FILE):
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True) if os.path.dirname(KEY_FILE) else None
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

generate_key()
ENCRYPT_KEY = load_key()

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "rb") as f:
        try:
            encrypted = f.read()
            if not encrypted:
                return []
            decrypted = decrypt_data(encrypted, ENCRYPT_KEY)
            return json.loads(decrypted)
        except Exception:
            return []

def save_db(data):
    if os.path.exists(DB_FILE):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"{BACKUP_DIR}/backup_{now_str}.json"
        shutil.copyfile(DB_FILE, backup_name)
        backups = sorted(os.listdir(BACKUP_DIR))
        while len(backups) > MAX_BACKUPS:
            os.remove(os.path.join(BACKUP_DIR, backups[0]))
            backups.pop(0)
    encrypted = encrypt_data(json.dumps(data, ensure_ascii=False, indent=2), ENCRYPT_KEY)
    with open(DB_FILE, "wb") as f:
        f.write(encrypted)
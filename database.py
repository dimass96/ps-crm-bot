import os
import json
from cryptography.fernet import Fernet

DB_FILE = "/data/clients_db.json"
KEY_FILE = "/data/secret.key"

def generate_key():
    if not os.path.exists(KEY_FILE):
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
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
    try:
        with open(DB_FILE, "rb") as f:
            encrypted = f.read()
        if not encrypted:
            return []
        decrypted = decrypt_data(encrypted, ENCRYPT_KEY)
        return json.loads(decrypted)
    except Exception:
        return []

def save_db(data):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    encrypted = encrypt_data(json.dumps(data, ensure_ascii=False, indent=2), ENCRYPT_KEY)
    with open(DB_FILE, "wb") as f:
        f.write(encrypted)

def backup_db():
    if os.path.exists(DB_FILE):
        import shutil
        backup_name = DB_FILE + ".backup_" + datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy(DB_FILE, backup_name)
        return backup_name
    return None

def restore_db(backup_path):
    import shutil
    if os.path.exists(backup_path):
        shutil.copy(backup_path, DB_FILE)
        return True
    return False

def add_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == client["id"]:
            clients[i] = client
            save_db(clients)
            return
    clients.append(client)
    save_db(clients)

def delete_client(client_id):
    clients = load_db()
    clients = [c for c in clients if c["id"] != client_id]
    save_db(clients)
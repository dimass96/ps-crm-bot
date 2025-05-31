import os
import json
from cryptography.fernet import Fernet

DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "clients.json.enc")
KEY_FILE = os.path.join(DATA_DIR, "key.key")

def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return key

KEY = load_key()
fernet = Fernet(KEY)

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "rb") as f:
        encrypted = f.read()
    try:
        decrypted = fernet.decrypt(encrypted)
        data = json.loads(decrypted.decode())
        return data
    except Exception:
        return []

def save_db(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    json_data = json.dumps(data, ensure_ascii=False).encode()
    encrypted = fernet.encrypt(json_data)
    with open(DB_FILE, "wb") as f:
        f.write(encrypted)

def add_client(client):
    data = load_db()
    data.append(client)
    save_db(data)

def update_client(client):
    data = load_db()
    for i, c in enumerate(data):
        if c.get("id") == client.get("id"):
            data[i] = client
            break
    else:
        data.append(client)
    save_db(data)

def delete_client(client_id):
    data = load_db()
    data = [c for c in data if c.get("id") != client_id]
    save_db(data)
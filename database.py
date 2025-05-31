import os
import json
from cryptography.fernet import Fernet

DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "clients.json")
KEY_FILE = os.path.join(DATA_DIR, "key.key")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def load_key():
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, "rb") as f:
        return f.read()

fernet = Fernet(load_key())

def encrypt_data(data: bytes) -> bytes:
    return fernet.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    return fernet.decrypt(data)

def load_db():
    ensure_data_dir()
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "rb") as f:
            encrypted = f.read()
        decrypted = decrypt_data(encrypted)
        return json.loads(decrypted)
    except Exception:
        # Если не удалось расшифровать или прочесть - вернуть пустой список
        return []

def save_db(data):
    ensure_data_dir()
    try:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        encrypted = encrypt_data(raw)
        with open(DB_FILE, "wb") as f:
            f.write(encrypted)
        return True
    except Exception:
        return False

def get_next_client_id(clients):
    if not clients:
        return 1
    return max(c.get("id", 0) for c in clients) + 1

def save_new_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client(updated_client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c.get("id") == updated_client.get("id"):
            clients[i] = updated_client
            break
    save_db(clients)

def find_clients(query):
    clients = load_db()
    query = query.lower()
    results = []
    for c in clients:
        contact = c.get("contact", "").lower()
        if query in contact:
            results.append(c)
    return results
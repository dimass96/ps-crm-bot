import json
import os
import pyAesCrypt

DB_FILE = "clients.json"
ENCRYPTED_DB_FILE = "clients_encrypted.db"
BUFFER_SIZE = 64 * 1024
PASSWORD = "pscrm2024"

def save_client(client):
    clients = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                clients = json.load(f)
            except Exception:
                clients = []
    # удаляем старого клиента по id, если такой уже есть
    clients = [c for c in clients if c.get("id") != client.get("id")]
    clients.append(client)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    encrypt_db()

def load_clients():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def encrypt_db():
    if os.path.exists(DB_FILE):
        pyAesCrypt.encryptFile(DB_FILE, ENCRYPTED_DB_FILE, PASSWORD, BUFFER_SIZE)

def decrypt_db():
    if os.path.exists(ENCRYPTED_DB_FILE):
        pyAesCrypt.decryptFile(ENCRYPTED_DB_FILE, DB_FILE, PASSWORD, BUFFER_SIZE)

def get_client_by_id(client_id):
    clients = load_clients()
    for c in clients:
        if c.get("id") == client_id:
            return c
    return None

def update_client(client):
    clients = load_clients()
    for i, c in enumerate(clients):
        if c.get("id") == client.get("id"):
            clients[i] = client
            break
    else:
        clients.append(client)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    encrypt_db()

def delete_client(client_id):
    clients = load_clients()
    clients = [c for c in clients if c.get("id") != client_id]
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    encrypt_db()
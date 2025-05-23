import json
import os
from cryptography.fernet import Fernet

DB_FILE = 'clients.json'
KEY_FILE = 'secret.key'

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)

def load_key():
    if not os.path.exists(KEY_FILE):
        generate_key()
    with open(KEY_FILE, 'rb') as f:
        return f.read()

def encrypt_db():
    key = load_key()
    fernet = Fernet(key)
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'rb') as file:
            original = file.read()
        encrypted = fernet.encrypt(original)
        with open(DB_FILE + '.enc', 'wb') as encrypted_file:
            encrypted_file.write(encrypted)
        os.remove(DB_FILE)

def decrypt_db():
    key = load_key()
    fernet = Fernet(key)
    if os.path.exists(DB_FILE + '.enc'):
        with open(DB_FILE + '.enc', 'rb') as enc_file:
            encrypted = enc_file.read()
        decrypted = fernet.decrypt(encrypted)
        with open(DB_FILE, 'wb') as dec_file:
            dec_file.write(decrypted)

def load_clients():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_client(client):
    clients = load_clients()
    clients.append(client)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def find_client_by_id(client_id):
    clients = load_clients()
    for c in clients:
        if c.get('id') == client_id:
            return c
    return None

def update_client(client_id, new_data):
    clients = load_clients()
    for i, c in enumerate(clients):
        if c.get('id') == client_id:
            clients[i] = new_data
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(clients, f, ensure_ascii=False, indent=2)
            return True
    return False
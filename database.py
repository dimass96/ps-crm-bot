import json
import os

DB_FILE = 'clients.json'

def load_clients():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

def save_client(client):
    clients = load_clients()
    for i, c in enumerate(clients):
        if c.get("id") == client.get("id"):
            clients[i] = client
            break
    else:
        clients.append(client)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def find_client_by_id(client_id):
    clients = load_clients()
    for c in clients:
        if c.get('id') == client_id:
            return c
    return None

def update_client(client_id, updated_data):
    clients = load_clients()
    for i, c in enumerate(clients):
        if c.get('id') == client_id:
            clients[i].update(updated_data)
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(clients, f, ensure_ascii=False, indent=2)
            return True
    return False

def delete_client(client_id):
    clients = load_clients()
    clients = [c for c in clients if c.get('id') != client_id]
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def encrypt_db():
    pass
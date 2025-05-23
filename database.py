import json
import os

DB_FILE = 'clients.json'

def load_clients():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_clients(clients):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def save_client(client):
    clients = load_clients()
    for i, c in enumerate(clients):
        if c['phone'] == client['phone']:
            clients[i] = client
            save_clients(clients)
            return
    clients.append(client)
    save_clients(clients)

def get_clients():
    return load_clients()

def get_client_by_id(identifier):
    clients = load_clients()
    for c in clients:
        if c['phone'] == identifier:
            return c
    return None

def update_client(identifier, new_data):
    clients = load_clients()
    for i, c in enumerate(clients):
        if c['phone'] == identifier:
            clients[i].update(new_data)
            save_clients(clients)
            return True
    return False

def delete_client(identifier):
    clients = load_clients()
    clients = [c for c in clients if c['phone'] != identifier]
    save_clients(clients)
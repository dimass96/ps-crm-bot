import json
import os

DB_FILE = "clients_db.json"

def _load():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def _save(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_clients():
    return _load()

def get_next_id():
    clients = _load()
    if not clients:
        return 1
    return max(int(c.get("id", 0)) for c in clients) + 1

def add_client(client):
    clients = _load()
    clients.append(client)
    _save(clients)

def update_client(client):
    clients = _load()
    for i, c in enumerate(clients):
        if str(c.get("id")) == str(client.get("id")):
            clients[i] = client
            break
    _save(clients)

def delete_client(client_id):
    clients = _load()
    clients = [c for c in clients if str(c.get("id")) != str(client_id)]
    _save(clients)

def find_client(query):
    clients = _load()
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            return c
    return None

def get_client_by_id(client_id):
    clients = _load()
    for c in clients:
        if str(c.get("id")) == str(client_id):
            return c
    return None

def export_db():
    fname = "clients_export.json"
    clients = _load()
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    return fname
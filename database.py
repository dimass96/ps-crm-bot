import json
import os

DB_FILE = "clients_db.json"

def _read_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = []
    return data

def _write_db(clients):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def get_clients():
    return _read_db()

def get_next_id():
    clients = get_clients()
    if not clients:
        return 1
    return max(client.get("id", 0) for client in clients) + 1

def add_client(client):
    clients = _read_db()
    clients.append(client)
    _write_db(clients)

def update_client(client):
    clients = _read_db()
    for idx, c in enumerate(clients):
        if c.get("id") == client.get("id"):
            clients[idx] = client
            break
    _write_db(clients)

def delete_client(client_id):
    clients = _read_db()
    clients = [c for c in clients if c.get("id") != client_id]
    _write_db(clients)

def find_client(query):
    clients = _read_db()
    for c in clients:
        if str(c.get("number", "")).strip() == str(query).strip():
            return c
        if str(c.get("telegram", "")).strip() == str(query).strip():
            return c
    return None

def get_client_by_id(client_id):
    clients = _read_db()
    for c in clients:
        if c.get("id") == client_id:
            return c
    return None

def export_db():
    return DB_FILE
import json
import os

DB_FILE = "clients_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(clients):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def get_next_client_id(clients):
    return max([c.get("id", 0) for c in clients], default=0) + 1

def find_client(query):
    clients = load_db()
    query = query.lower().strip()
    for client in clients:
        if str(client.get("contact", "")).lower() == query:
            return client
    return None

def update_client(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == client["id"]:
            clients[i] = client
            save_db(clients)
            return

def save_new_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def delete_client(client_id):
    clients = load_db()
    clients = [c for c in clients if c["id"] != client_id]
    save_db(clients)
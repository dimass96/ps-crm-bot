import json
import os
from copy import deepcopy

DB_FILE = "clients_db.json"

def read_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_db(clients):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def get_clients():
    return read_db()

def get_next_id():
    clients = read_db()
    if not clients:
        return 1
    return max([c.get("id", 0) for c in clients]) + 1

def add_client(client):
    clients = read_db()
    clients.append(deepcopy(client))
    save_db(clients)

def update_client(client):
    clients = read_db()
    for i, c in enumerate(clients):
        if c.get("id") == client.get("id"):
            clients[i] = deepcopy(client)
            break
    save_db(clients)

def delete_client(client_id):
    clients = read_db()
    clients = [c for c in clients if c.get("id") != client_id]
    save_db(clients)

def find_client(key):
    clients = read_db()
    for c in clients:
        if key == c.get("number") or key == c.get("telegram"):
            return deepcopy(c)
    return None

def get_client_by_id(client_id):
    clients = read_db()
    for c in clients:
        if c.get("id") == client_id:
            return deepcopy(c)
    return None

def export_db():
    clients = read_db()
    filename = "clients_export.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    return filename

# Фоновые проверки (заглушки, сама логика реализуется в bot.py)
def check_birthdays():
    pass

def check_subscriptions():
    pass
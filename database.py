import json
import os

DB_FILE = "clients_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(clients):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def get_clients():
    return load_db()

def add_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == client["id"]:
            clients[i] = client
            break
    save_db(clients)

def delete_client(client_id):
    clients = load_db()
    clients = [c for c in clients if c["id"] != client_id]
    save_db(clients)

def find_client(query):
    clients = load_db()
    for c in clients:
        if (str(c.get("number", "")).strip() == query.strip()) or (str(c.get("telegram", "")).strip() == query.strip()):
            return c
    return None

def get_client_by_id(client_id):
    clients = load_db()
    for c in clients:
        if c["id"] == client_id:
            return c
    return None

def get_next_id():
    clients = load_db()
    if not clients:
        return 1
    ids = [c["id"] for c in clients if "id" in c]
    return max(ids) + 1 if ids else 1

def export_db():
    clients = load_db()
    text = ""
    for c in clients:
        text += f"ID: {c.get('id', '')}\n"
        text += f"Номер: {c.get('number', '')}\n"
        text += f"Telegram: {c.get('telegram', '')}\n"
        text += f"ДР: {c.get('birthdate', '')}\n"
        text += f"Регион: {c.get('region', '')}\n"
        text += f"Консоль: {c.get('console', '')}\n"
        text += f"Аккаунт: {c.get('account', '')}\n"
        text += f"Пароль: {c.get('password', '')}\n"
        text += f"Почта/пароль: {c.get('emailpass', '')}\n"
        subs = c.get("subscriptions", [])
        for s in subs:
            text += f"Подписка: {s.get('name', '')}, срок: {s.get('term', '')}, c {s.get('date_start', '')} по {s.get('date_end', '')}\n"
        games = c.get("games", [])
        if games:
            text += "Игры: " + ", ".join(games) + "\n"
        text += "-"*24 + "\n"
    return text if text else "База пуста."
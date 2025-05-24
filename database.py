import json
import os

DB_PATH = "clients_db.json"

def load_db():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_db(clients):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def add_client_to_db(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client_in_db(index, client):
    clients = load_db()
    if 0 <= index < len(clients):
        clients[index] = client
        save_db(clients)

def find_client(query):
    clients = load_db()
    for i, c in enumerate(clients):
        if c.get("number") == query or c.get("telegram") == query:
            return i, c
    return None, None

def find_client_partial(query):
    clients = load_db()
    for i, c in enumerate(clients):
        if query in (c.get("number") or "") or query in (c.get("telegram") or ""):
            return i, c
    return None, None

def delete_client(query):
    clients = load_db()
    new_clients = []
    deleted = False
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            deleted = True
            continue
        new_clients.append(c)
    save_db(new_clients)
    return deleted

def export_all():
    clients = load_db()
    result = []
    for c in clients:
        number = c.get("number") or c.get("telegram") or ""
        birth = c.get("birthdate", "отсутствует")
        acc = c.get("account", "")
        acc_mail = c.get("mailpass", "")
        region = c.get("region", "отсутствует")
        subs = c.get("subscriptions", [])
        games = c.get("games", [])
        text = f"Клиент: {number} | {birth}\nАккаунт: {acc} ({region})\n"
        if acc_mail:
            text += f"Почта-пароль: {acc_mail}\n"
        if subs and subs[0].get("name") != "отсутствует":
            for s in subs:
                text += f"Подписка: {s['name']} {s['term']} ({region}) с {s['start']} по {s['end']}\n"
        else:
            text += "Подписки: отсутствует\n"
        text += f"Регион: {region}\n"
        if games:
            text += "Игры:\n"
            for g in games:
                text += f"- {g}\n"
        text += "\n"
        result.append(text)
    return "\n".join(result)
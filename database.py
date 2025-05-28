import json
import os

DB_FILE = "clients.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_clients():
    return load_db()

def add_client(client):
    db = load_db()
    db.append(client)
    save_db(db)

def update_client(client):
    db = load_db()
    for idx, c in enumerate(db):
        if c.get("id") == client.get("id"):
            db[idx] = client
            break
    save_db(db)

def delete_client(client_id):
    db = load_db()
    db = [c for c in db if c.get("id") != client_id]
    save_db(db)

def find_client(query):
    db = load_db()
    q = query.strip().lower()
    for c in db:
        if c.get("number", "").lower() == q or c.get("telegram", "").lower() == q:
            return c
    return None

def get_client_by_id(client_id):
    db = load_db()
    for c in db:
        if c.get("id") == client_id:
            return c
    return None

def get_next_id():
    db = load_db()
    ids = [c.get("id", 0) for c in db]
    return max(ids, default=0) + 1

def export_db():
    db = load_db()
    out = []
    for c in db:
        block = []
        block.append(f"ID: {c.get('id')}")
        block.append(f"Номер: {c.get('number', '')}")
        block.append(f"Telegram: {c.get('telegram', '')}")
        block.append(f"Дата рождения: {c.get('birthdate', '')}")
        block.append(f"Консоль: {c.get('console', '')}")
        block.append(f"Логин: {c.get('account', '')}")
        block.append(f"Пароль: {c.get('password', '')}")
        block.append(f"Почта: {c.get('emailpass', '')}")
        block.append(f"Регион: {c.get('region', '')}")
        subs = c.get('subscriptions', [])
        if subs:
            for s in subs:
                line = f"{s.get('name','')} {s.get('term','')} с {s.get('date_start','')} по {s.get('date_end','')}"
                block.append("Подписка: " + line)
        block.append("Игры: " + ", ".join(c.get("games", [])))
        block.append(f"Резерв фото: {c.get('reserve_photo_id','')}")
        block.append("—" * 10)
        out.append("\n".join(block))
    return "\n\n".join(out)
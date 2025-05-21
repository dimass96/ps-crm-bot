import sqlite3

def init_db():
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            birth_date TEXT,
            email TEXT,
            account_password TEXT,
            mail_password TEXT,
            subscription_name TEXT,
            subscription_start TEXT,
            subscription_end TEXT,
            region TEXT,
            games TEXT,
            reserve_photo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_client(data):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO clients (
            username, birth_date, email, account_password,
            mail_password, subscription_name, subscription_start,
            subscription_end, region, games, reserve_photo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()

def get_client_by_identifier(identifier):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE username = ?", (identifier,))
    result = c.fetchone()
    conn.close()
    return result

def update_client_field(client_id, field, new_value):
    allowed_fields = [
        "username", "birth_date", "email", "account_password",
        "mail_password", "subscription_name", "subscription_start",
        "subscription_end", "region", "games", "reserve_photo"
    ]
    if field not in allowed_fields:
        raise ValueError("Недопустимое поле для обновления")
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute(f"UPDATE clients SET {field} = ? WHERE id = ?", (new_value, client_id))
    conn.commit()
    conn.close()

def delete_client_by_id(client_id):
    conn = sqlite3.connect("clients.db")
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()

import sqlite3
import pyAesCrypt
import os

DB_FILE = "clients.db"
ENCRYPTED_FILE = "clients_encrypted.db"
BUFFER_SIZE = 64 * 1024
PASSWORD = "pscrm2024"

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
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
        """)
        conn.commit()
        conn.close()

def add_client(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clients (
            username, birth_date, email, account_password, mail_password,
            subscription_name, subscription_start, subscription_end,
            region, games, reserve_photo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()
    encrypt_db()

def get_client_by_identifier(identifier):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE username LIKE ?", (f"%{identifier}%",))
    result = cursor.fetchone()
    conn.close()
    return result

def update_client_field(client_id, field, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE clients SET {field} = ? WHERE id = ?", (value, client_id))
    conn.commit()
    conn.close()
    encrypt_db()

def delete_client_by_id(client_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()
    encrypt_db()

def encrypt_db():
    with open(DB_FILE, "rb") as f_in:
        with open(ENCRYPTED_FILE, "wb") as f_out:
            pyAesCrypt.encryptStream(f_in, f_out, PASSWORD, BUFFER_SIZE)
            
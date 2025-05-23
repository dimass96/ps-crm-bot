import sqlite3
import pyAesCrypt
from datetime import datetime, timedelta
import os

BUFFER_SIZE = 64 * 1024
DB_FILE = "clients.db"
ENCRYPTED_FILE = "clients_encrypted.db"
PASSWORD = "57131702"

def init_db():
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier_type TEXT,
            identifier_value TEXT,
            birth_date TEXT,
            email TEXT,
            password TEXT,
            mailpass_mail TEXT,
            console TEXT,
            region TEXT,
            reserve_codes TEXT,
            first_sub_type TEXT,
            first_sub_term TEXT,
            first_sub_start TEXT,
            first_sub_end TEXT,
            second_sub_type TEXT,
            second_sub_term TEXT,
            second_sub_start TEXT,
            second_sub_end TEXT,
            games TEXT
        )
    ''')
    conn.commit()
    conn.close()
    encrypt_db()

def encrypt_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as fIn:
            with open(ENCRYPTED_FILE, "wb") as fOut:
                pyAesCrypt.encryptStream(fIn, fOut, PASSWORD, BUFFER_SIZE)
        os.remove(DB_FILE)

def decrypt_db():
    if os.path.exists(ENCRYPTED_FILE):
        with open(ENCRYPTED_FILE, "rb") as fIn:
            with open(DB_FILE, "wb") as fOut:
                pyAesCrypt.decryptStream(fIn, fOut, PASSWORD, BUFFER_SIZE, len(fIn.read()))

def calculate_end_date(start_date_str, term):
    try:
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
    except:
        return None
    if term == "1м":
        end_date = start_date + timedelta(days=30)
    elif term == "3м":
        end_date = start_date + timedelta(days=90)
    elif term == "12м":
        end_date = start_date + timedelta(days=365)
    else:
        return None
    return end_date.strftime("%d.%m.%Y")

def add_client(data):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    first_end = calculate_end_date(data.get("first_sub_start"), data.get("first_sub_term"))
    second_end = calculate_end_date(data.get("second_sub_start"), data.get("second_sub_term"))

    cursor.execute('''
        INSERT INTO clients (
            identifier_type, identifier_value, birth_date,
            email, password, mailpass_mail, console, region, reserve_codes,
            first_sub_type, first_sub_term, first_sub_start, first_sub_end,
            second_sub_type, second_sub_term, second_sub_start, second_sub_end,
            games
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("identifier_type"),
        data.get("identifier_value"),
        data.get("birth_date"),
        data.get("email"),
        data.get("password"),
        data.get("mailpass_mail"),
        data.get("console"),
        data.get("region"),
        data.get("reserve_codes"),
        data.get("first_sub_type"),
        data.get("first_sub_term"),
        data.get("first_sub_start"),
        first_end,
        data.get("second_sub_type"),
        data.get("second_sub_term"),
        data.get("second_sub_start"),
        second_end,
        " —— ".join(data.get("games") or [])
    ))

    conn.commit()
    conn.close()
    encrypt_db()

def get_client(identifier):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE identifier_value = ?", (identifier,))
    result = cursor.fetchone()
    conn.close()
    encrypt_db()
    return result

def update_client_field(identifier, field, value):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE clients SET {field} = ? WHERE identifier_value = ?", (value, identifier))
    conn.commit()
    conn.close()
    encrypt_db()

def delete_client(identifier):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE identifier_value = ?", (identifier,))
    conn.commit()
    conn.close()
    encrypt_db()
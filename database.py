# database.py (полный, для ТЗ)

import os
import sqlite3
import pyAesCrypt

DB_FILENAME = 'clients.db'
ENC_DB_FILENAME = 'clients_encrypted.db'
PASSWORD = 'pscrm2024'

def encrypt_db():
    if os.path.exists(DB_FILENAME):
        pyAesCrypt.encryptFile(DB_FILENAME, ENC_DB_FILENAME, PASSWORD)

def decrypt_db():
    if os.path.exists(ENC_DB_FILENAME):
        pyAesCrypt.decryptFile(ENC_DB_FILENAME, DB_FILENAME, PASSWORD)

def init_db():
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT,
            identifier_type TEXT,
            birthday TEXT,
            email TEXT,
            account_pass TEXT,
            mail_pass TEXT,
            console TEXT,
            region TEXT,
            reserve_codes_path TEXT,
            sub1_name TEXT,
            sub1_duration TEXT,
            sub1_start TEXT,
            sub1_end TEXT,
            sub2_name TEXT,
            sub2_duration TEXT,
            sub2_start TEXT,
            sub2_end TEXT,
            games TEXT
        )
    ''')
    conn.commit()
    conn.close()
    encrypt_db()

def add_client(client):
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clients (
            identifier, identifier_type, birthday, email, account_pass, mail_pass,
            console, region, reserve_codes_path,
            sub1_name, sub1_duration, sub1_start, sub1_end,
            sub2_name, sub2_duration, sub2_start, sub2_end,
            games
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        client['identifier'],
        client['identifier_type'],
        client['birthday'],
        client['email'],
        client['account_pass'],
        client['mail_pass'],
        client['console'],
        client['region'],
        client['reserve_codes_path'],
        client.get('sub1_name', ''),
        client.get('sub1_duration', ''),
        client.get('sub1_start', ''),
        client.get('sub1_end', ''),
        client.get('sub2_name', ''),
        client.get('sub2_duration', ''),
        client.get('sub2_start', ''),
        client.get('sub2_end', ''),
        client.get('games', '')
    ))
    conn.commit()
    conn.close()
    encrypt_db()

def update_client(client_id, field, value):
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        UPDATE clients SET {field} = ? WHERE id = ?
    ''', (value, client_id))
    conn.commit()
    conn.close()
    encrypt_db()

def update_client_multi(client_id, data: dict):
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    for field, value in data.items():
        cursor.execute(f'UPDATE clients SET {field} = ? WHERE id = ?', (value, client_id))
    conn.commit()
    conn.close()
    encrypt_db()

def get_client_by_identifier(identifier):
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM clients WHERE identifier = ?
    ''', (identifier,))
    row = cursor.fetchone()
    conn.close()
    encrypt_db()
    return row

def get_client_by_id(client_id):
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM clients WHERE id = ?
    ''', (client_id,))
    row = cursor.fetchone()
    conn.close()
    encrypt_db()
    return row

def delete_client(client_id):
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    encrypt_db()

def get_all_clients():
    decrypt_db()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients')
    rows = cursor.fetchall()
    conn.close()
    encrypt_db()
    return rows

def save_reserve_codes(client_id, file_path):
    update_client(client_id, 'reserve_codes_path', file_path)

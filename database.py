import sqlite3
import pyAesCrypt
import os

DB_FILE = 'clients.db'
ENC_DB_FILE = 'clients_encrypted.db'
DB_PASS = 'pscrm2024'
BUFFER_SIZE = 64 * 1024

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT,
            identifier_type TEXT,
            birth_date TEXT,
            email TEXT,
            acc_pass TEXT,
            mail_pass TEXT,
            consoles TEXT,
            region TEXT,
            reserve_codes_path TEXT,
            subs_data TEXT,
            games TEXT
        )
        ''')
        conn.commit()
        conn.close()
        with open(DB_FILE, 'rb') as fIn:
            with open(ENC_DB_FILE, 'wb') as fOut:
                pyAesCrypt.encryptStream(fIn, fOut, DB_PASS, BUFFER_SIZE)
    else:
        if not os.path.exists(DB_FILE) and os.path.exists(ENC_DB_FILE):
            with open(ENC_DB_FILE, 'rb') as fIn:
                with open(DB_FILE, 'wb') as fOut:
                    pyAesCrypt.decryptStream(fIn, fOut, DB_PASS, BUFFER_SIZE, os.path.getsize(ENC_DB_FILE))

def save_and_encrypt_db():
    with open(DB_FILE, 'rb') as fIn:
        with open(ENC_DB_FILE, 'wb') as fOut:
            pyAesCrypt.encryptStream(fIn, fOut, DB_PASS, BUFFER_SIZE)

def decrypt_db():
    with open(ENC_DB_FILE, 'rb') as fIn:
        with open(DB_FILE, 'wb') as fOut:
            pyAesCrypt.decryptStream(fIn, fOut, DB_PASS, BUFFER_SIZE, os.path.getsize(ENC_DB_FILE))

def add_client(data):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO clients (identifier, identifier_type, birth_date, email, acc_pass, mail_pass, consoles, region, reserve_codes_path, subs_data, games)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['identifier'], data['identifier_type'], data['birth_date'],
        data['email'], data['acc_pass'], data['mail_pass'],
        data['consoles'], data['region'], data.get('reserve_codes_path', None),
        data['subs_data'], data['games']
    ))
    conn.commit()
    conn.close()
    save_and_encrypt_db()

def update_client(client_id, data):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE clients SET identifier=?, identifier_type=?, birth_date=?, email=?, acc_pass=?, mail_pass=?, consoles=?, region=?, reserve_codes_path=?, subs_data=?, games=?
    WHERE id=?
    ''', (
        data['identifier'], data['identifier_type'], data['birth_date'],
        data['email'], data['acc_pass'], data['mail_pass'],
        data['consoles'], data['region'], data.get('reserve_codes_path', None),
        data['subs_data'], data['games'], client_id
    ))
    conn.commit()
    conn.close()
    save_and_encrypt_db()

def get_client_by_identifier(identifier):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE identifier=?", (identifier,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_client_by_id(client_id):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def delete_client(client_id):
    decrypt_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()
    save_and_encrypt_db()


import logging
import sqlite3
import pyAesCrypt
import os
import io
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460
DB_FILE = 'clients.db'
ENC_DB_FILE = 'clients_encrypted.db'
DB_PASS = 'pscrm2024'
BUFFER_SIZE = 64 * 1024

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

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

def calc_end_date(date_start, months):
    dt = datetime.strptime(date_start, "%d.%m.%Y")
    m = dt.month - 1 + months
    y = dt.year + m // 12
    m = m % 12 + 1
    d = min(dt.day, [31, 29 if y%4==0 and not y%100==0 or y%400==0 else 28, 31,30,31,30,31,31,30,31,30,31][m-1])
    new_date = datetime(y, m, d)
    return new_date.strftime("%d.%m.%Y")

def subs_to_str(subs_data):
    if subs_data == "не оформлена":
        return "Подписка: не оформлена"
    subs = eval(subs_data) if isinstance(subs_data, str) else subs_data
    if type(subs) is dict and len(subs) == 1:
        k = list(subs.keys())[0]
        v = subs[k]
        return f"{k} {v['type']} {v['months']}м\nСрок: {v['date_start']} — {v['date_end']}"
    elif type(subs) is dict and len(subs) == 2:
        lines = []
        for sub_name, v in subs.items():
            lines.append(f"{sub_name} {v['type']} {v['months']}м\nСрок: {v['date_start']} — {v['date_end']}")
        return "\n\n".join(lines)
    else:
        return "Подписка: не оформлена"

def games_to_str(games):
    if not games or games == 'нет':
        return 'Игры: отсутствуют'
    return 'Игры:\n' + '\n'.join(g.strip() for g in games.split(' —— ') if g.strip())

def get_reserve_photo_path(reserve_codes_path):
    return reserve_codes_path if reserve_codes_path else None

def format_client_info(client):
    identifier = f"Телефон: {client[1]}" if client[2] == "Телефон" else f"Telegram: {client[1]}"
    birth = f"Дата рождения: {client[3]}"
    email = client[4]
    acc_pass = client[5]
    mail_pass = client[6] if client[6] else "-"
    consoles = client[7]
    region = client[8]
    reserve_codes_path = client[9]
    subs_data = client[10]
    games = client[11]
    acc_line = f"Данные аккаунта:\n{email} ({consoles})\n{acc_pass}\nПочта: {mail_pass}"
    region_line = f"Регион: {region}"
    subs_line = subs_to_str(subs_data)
    games_line = games_to_str(games)
    result = f"{identifier}\n{birth}\n{acc_line}\n{region_line}\n{subs_line}\n{games_line}"
    return result

def format_subs_for_edit(subs_data):
    if subs_data == "не оформлена":
        return []
    subs = eval(subs_data) if isinstance(subs_data, str) else subs_data
    if type(subs) is dict and len(subs) == 1:
        return [list(subs.keys())[0]]
    elif type(subs) is dict and len(subs) == 2:
        return list(subs.keys())
    else:
        return []

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("➕ Добавить клиента", callback_data="add"),
           InlineKeyboardButton("🔍 Найти клиента", callback_data="find"))
    return kb

def edit_menu(client_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📱 Изменить номер", callback_data=f"edit_phone_{client_id}"),
        InlineKeyboardButton("📅 Изменить дату рождения", callback_data=f"edit_birth_{client_id}"),
        InlineKeyboardButton("🔐 Изменить данные", callback_data=f"edit_acc_{client_id}"),
        InlineKeyboardButton("🎮 Изменить консоль", callback_data=f"edit_console_{client_id}"),
        InlineKeyboardButton("🌍 Изменить регион", callback_data=f"edit_region_{client_id}"),
        InlineKeyboardButton("🖼 Изменить резерв коды", callback_data=f"edit_reserve_{client_id}"),
        InlineKeyboardButton("💳 Изменить подписку", callback_data=f"edit_sub_{client_id}"),
        InlineKeyboardButton("🎮 Изменить игры", callback_data=f"edit_games_{client_id}"),
    )
    kb.add(
        InlineKeyboardButton("✅ Сохранить", callback_data=f"save_{client_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{client_id}"),
    )
    return kb

def remove_message_safe(chat_id, msg_id):
    try:
        return bot.delete_message(chat_id, msg_id)
    except:
        return

class AddClient(StatesGroup):
    choose_ident = State()
    get_ident = State()
    get_birth_question = State()
    get_birth = State()
    get_email_pass = State()
    get_console = State()
    get_region = State()
    get_reserve_codes = State()
    upload_reserve_codes = State()
    get_subs_question = State()
    get_subs_count = State()
    get_subs_type = State()
    get_subs_months = State()
    get_subs_date = State()
    get_second_subs_type = State()
    get_second_subs_months = State()
    get_second_subs_date = State()
    get_games_question = State()
    get_games = State()
    finish = State()

class EditClient(StatesGroup):
    choose_field = State()
    edit_phone = State()
    edit_birth = State()
    edit_acc = State()
    edit_console = State()
    edit_region = State()
    edit_reserve = State()
    upload_reserve_codes = State()
    edit_subs = State()
    edit_subs_choice = State()
    edit_subs_type = State()
    edit_subs_months = State()
    edit_subs_date = State()
    edit_second_subs_type = State()
    edit_second_subs_months = State()
    edit_second_subs_date = State()
    edit_games = State()
    finish = State()

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Главное меню", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "add")
async def add_client_start(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await state.update_data(new_client={})
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Телефон", callback_data="ident_phone"),
           InlineKeyboardButton("Telegram", callback_data="ident_tg"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await call.message.answer("Выберите способ идентификации:", reply_markup=kb)
    await AddClient.choose_ident.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data.startswith("ident_"), state=AddClient.choose_ident)
async def add_client_choose_ident(call: types.CallbackQuery, state: FSMContext):
    ident_type = "Телефон" if call.data == "ident_phone" else "Telegram"
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['identifier_type'] = ident_type
    await state.update_data(new_client=new_client)
    await call.message.delete()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await call.message.answer(f"Введите {ident_type.lower()} клиента:", reply_markup=kb)
    await AddClient.get_ident.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(state=AddClient.get_ident)
async def add_client_get_ident(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['identifier'] = message.text.strip()
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Да", callback_data="birth_yes"),
           InlineKeyboardButton("Нет", callback_data="birth_no"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await message.answer("Есть ли дата рождения?", reply_markup=kb)
    await AddClient.get_birth_question.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data in ["birth_yes", "birth_no"], state=AddClient.get_birth_question)
async def add_client_birth_question(call: types.CallbackQuery, state: FSMContext):
    if call.data == "birth_no":
        data = await state.get_data()
        new_client = data.get('new_client', {})
        new_client['birth_date'] = "отсутствует"
        await state.update_data(new_client=new_client)
        await call.message.delete()
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Введите email, пароль от аккаунта и пароль от почты (три строки):", reply_markup=kb)
        await AddClient.get_email_pass.set()
        await state.update_data(prev_msgs=[msg.message_id])
    else:
        await call.message.delete()
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=kb)
        await AddClient.get_birth.set()
        await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(state=AddClient.get_birth)
async def add_client_get_birth(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
        birth_date = message.text.strip()
    except:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        await message.answer("Некорректный формат даты! Введите в формате дд.мм.гггг:", reply_markup=kb)
        return
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['birth_date'] = birth_date
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await message.answer("Введите email, пароль от аккаунта и пароль от почты (три строки):", reply_markup=kb)
    await AddClient.get_email_pass.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(state=AddClient.get_email_pass)
async def add_client_get_email_pass(message: types.Message, state: FSMContext):
    lines = message.text.strip().split('\n')
    if len(lines) < 2:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        await message.answer("Введите email, пароль от аккаунта и пароль от почты (три строки):", reply_markup=kb)
        return
    email = lines[0]
    acc_pass = lines[1]
    mail_pass = lines[2] if len(lines) > 2 else ""
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['email'] = email
    new_client['acc_pass'] = acc_pass
    new_client['mail_pass'] = mail_pass
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(InlineKeyboardButton("PS4", callback_data="console_PS4"),
           InlineKeyboardButton("PS5", callback_data="console_PS5"),
           InlineKeyboardButton("PS4/PS5", callback_data="console_PS4/PS5"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await message.answer("Какие консоли?", reply_markup=kb)
    await AddClient.get_console.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data.startswith("console_"), state=AddClient.get_console)
async def add_client_get_console(call: types.CallbackQuery, state: FSMContext):
    consoles = call.data.split("_", 1)[1]
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['consoles'] = consoles
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(InlineKeyboardButton("укр", callback_data="region_укр"),
           InlineKeyboardButton("тур", callback_data="region_тур"),
           InlineKeyboardButton("другое", callback_data="region_другое"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    await call.message.delete()
    msg = await call.message.answer("Выберите регион аккаунта:", reply_markup=kb)
    await AddClient.get_region.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data.startswith("region_"), state=AddClient.get_region)
async def add_client_get_region(call: types.CallbackQuery, state: FSMContext):
    region = call.data.split("_", 1)[1]
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['region'] = region
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Да", callback_data="reserve_yes"),
           InlineKeyboardButton("Нет", callback_data="reserve_no"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    await call.message.delete()
    msg = await call.message.answer("Есть резерв коды?", reply_markup=kb)
    await AddClient.get_reserve_codes.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data in ["reserve_yes", "reserve_no"], state=AddClient.get_reserve_codes)
async def add_client_reserve_codes(call: types.CallbackQuery, state: FSMContext):
    if call.data == "reserve_no":
        data = await state.get_data()
        new_client = data.get('new_client', {})
        new_client['reserve_codes_path'] = None
        await state.update_data(new_client=new_client)
        await call.message.delete()
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("Да", callback_data="subs_yes"),
               InlineKeyboardButton("Нет", callback_data="subs_no"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Оформлена ли подписка?", reply_markup=kb)
        await AddClient.get_subs_question.set()
        await state.update_data(prev_msgs=[msg.message_id])
    else:
        await call.message.delete()
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Загрузите скриншот с резерв кодами:", reply_markup=kb)
        await AddClient.upload_reserve_codes.set()
        await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddClient.upload_reserve_codes)
async def add_client_upload_reserve_codes(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    path = f"reserve_{file.file_unique_id}.jpg"
    await bot.download_file(file.file_path, path)
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['reserve_codes_path'] = path
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Да", callback_data="subs_yes"),
           InlineKeyboardButton("Нет", callback_data="subs_no"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await message.answer("Оформлена ли подписка?", reply_markup=kb)
    await AddClient.get_subs_question.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data in ["subs_yes", "subs_no"], state=AddClient.get_subs_question)
async def add_client_subs_question(call: types.CallbackQuery, state: FSMContext):
    if call.data == "subs_no":
        data = await state.get_data()
        new_client = data.get('new_client', {})
        new_client['subs_data'] = "не оформлена"
        await state.update_data(new_client=new_client)
        await call.message.delete()
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("Да", callback_data="games_yes"),
               InlineKeyboardButton("Нет", callback_data="games_no"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Есть ли игры?", reply_markup=kb)
        await AddClient.get_games_question.set()
        await state.update_data(prev_msgs=[msg.message_id])
    else:
        await call.message.delete()
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("Одна", callback_data="subs_count_1"),
               InlineKeyboardButton("Две", callback_data="subs_count_2"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Сколько подписок?", reply_markup=kb)
        await AddClient.get_subs_count.set()
        await state.update_data(prev_msgs=[msg.message_id])
@dp.callback_query_handler(lambda c: c.data.startswith("subs_count_"), state=AddClient.get_subs_count)
async def add_client_subs_count(call: types.CallbackQuery, state: FSMContext):
    count = int(call.data.split("_")[2])
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['subs_count'] = count
    await state.update_data(new_client=new_client)
    await call.message.delete()
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("PS Plus Deluxe", callback_data="subs_type_Deluxe"),
           InlineKeyboardButton("PS Plus Extra", callback_data="subs_type_Extra"),
           InlineKeyboardButton("PS Plus Essential", callback_data="subs_type_Essential"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await call.message.answer("Выберите первую подписку (PS Plus):", reply_markup=kb)
    await AddClient.get_subs_type.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data.startswith("subs_type_"), state=AddClient.get_subs_type)
async def add_client_subs_type(call: types.CallbackQuery, state: FSMContext):
    subs_type = call.data.split("_")[2]
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(InlineKeyboardButton("1м", callback_data="subs_months_1"),
           InlineKeyboardButton("3м", callback_data="subs_months_3"),
           InlineKeyboardButton("12м", callback_data="subs_months_12"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    await call.message.delete()
    await state.update_data(first_subs_type=subs_type)
    msg = await call.message.answer("Срок первой подписки:", reply_markup=kb)
    await AddClient.get_subs_months.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data.startswith("subs_months_"), state=AddClient.get_subs_months)
async def add_client_subs_months(call: types.CallbackQuery, state: FSMContext):
    months = int(call.data.split("_")[2])
    await state.update_data(first_subs_months=months)
    await call.message.delete()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await call.message.answer("Введите дату оформления первой подписки (дд.мм.гггг):", reply_markup=kb)
    await AddClient.get_subs_date.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(state=AddClient.get_subs_date)
async def add_client_subs_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
        date_start = message.text.strip()
    except:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        await message.answer("Некорректный формат даты! Введите в формате дд.мм.гггг:", reply_markup=kb)
        return
    data = await state.get_data()
    new_client = data.get('new_client', {})
    first_subs_type = data.get('first_subs_type')
    first_subs_months = data.get('first_subs_months')
    subs = {
        'PS Plus': {
            'type': first_subs_type,
            'months': first_subs_months,
            'date_start': date_start,
            'date_end': calc_end_date(date_start, first_subs_months)
        }
    }
    new_client['subs_data_temp'] = subs
    await state.update_data(new_client=new_client)
    if new_client.get('subs_count') == 2:
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("EA Play", callback_data="second_subs_type_EA"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
        await AddClient.get_second_subs_type.set()
    else:
        new_client['subs_data'] = str(subs)
        await state.update_data(new_client=new_client)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("Да", callback_data="games_yes"),
               InlineKeyboardButton("Нет", callback_data="games_no"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        await message.answer("Есть ли игры?", reply_markup=kb)
        await AddClient.get_games_question.set()

@dp.callback_query_handler(lambda c: c.data.startswith("second_subs_type_"), state=AddClient.get_second_subs_type)
async def add_client_second_subs_type(call: types.CallbackQuery, state: FSMContext):
    subs_type = "EA Play"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("1м", callback_data="second_subs_months_1"),
           InlineKeyboardButton("12м", callback_data="second_subs_months_12"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    await call.message.delete()
    await state.update_data(second_subs_type=subs_type)
    msg = await call.message.answer("Срок второй подписки:", reply_markup=kb)
    await AddClient.get_second_subs_months.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.callback_query_handler(lambda c: c.data.startswith("second_subs_months_"), state=AddClient.get_second_subs_months)
async def add_client_second_subs_months(call: types.CallbackQuery, state: FSMContext):
    months = int(call.data.split("_")[3])
    await state.update_data(second_subs_months=months)
    await call.message.delete()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    msg = await call.message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=kb)
    await AddClient.get_second_subs_date.set()
    await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(state=AddClient.get_second_subs_date)
async def add_client_second_subs_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
        date_start = message.text.strip()
    except:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        await message.answer("Некорректный формат даты! Введите в формате дд.мм.гггг:", reply_markup=kb)
        return
    data = await state.get_data()
    new_client = data.get('new_client', {})
    subs = new_client.get('subs_data_temp', {})
    second_subs_type = "EA Play"
    second_subs_months = data.get('second_subs_months')
    subs[second_subs_type] = {
        'type': "EA Play",
        'months': second_subs_months,
        'date_start': date_start,
        'date_end': calc_end_date(date_start, second_subs_months)
    }
    new_client['subs_data'] = str(subs)
    await state.update_data(new_client=new_client)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Да", callback_data="games_yes"),
           InlineKeyboardButton("Нет", callback_data="games_no"))
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
    await message.answer("Есть ли игры?", reply_markup=kb)
    await AddClient.get_games_question.set()

@dp.callback_query_handler(lambda c: c.data in ["games_yes", "games_no"], state=AddClient.get_games_question)
async def add_client_games_question(call: types.CallbackQuery, state: FSMContext):
    if call.data == "games_no":
        data = await state.get_data()
        new_client = data.get('new_client', {})
        new_client['games'] = "нет"
        await state.update_data(new_client=new_client)
        await call.message.delete()
        await finish_add_client(call.message, state)
    else:
        await call.message.delete()
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_add"))
        msg = await call.message.answer("Введите список игр (каждая с новой строки):", reply_markup=kb)
        await AddClient.get_games.set()
        await state.update_data(prev_msgs=[msg.message_id])

@dp.message_handler(state=AddClient.get_games)
async def add_client_get_games(message: types.Message, state: FSMContext):
    games = [line.strip() for line in message.text.strip().split('\n') if line.strip()]
    games_str = ' —— '.join(games) if games else "нет"
    data = await state.get_data()
    new_client = data.get('new_client', {})
    new_client['games'] = games_str
    await state.update_data(new_client=new_client)
    await finish_add_client(message, state)

async def finish_add_client(message, state):
    data = await state.get_data()
    new_client = data.get('new_client', {})
    add_client({
        'identifier': new_client['identifier'],
        'identifier_type': new_client['identifier_type'],
        'birth_date': new_client['birth_date'],
        'email': new_client['email'],
        'acc_pass': new_client['acc_pass'],
        'mail_pass': new_client['mail_pass'],
        'consoles': new_client['consoles'],
        'region': new_client['region'],
        'reserve_codes_path': new_client.get('reserve_codes_path'),
        'subs_data': new_client['subs_data'],
        'games': new_client['games']
    })
    client_row = get_client_by_identifier(new_client['identifier'])
    text = f"✅ {new_client['identifier']} добавлен!\n\n" + format_client_info(client_row)
    kb = edit_menu(client_row[0])
    if client_row[9]:
        with open(client_row[9], 'rb') as photo:
            msg = await message.answer_photo(photo=photo, caption=text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.finish()
    await delete_prev_msgs(message.chat.id, state)
    await schedule_delete_message(msg.chat.id, msg.message_id)
    
async def schedule_delete_message(chat_id, message_id):
    await bot.delete_message(chat_id, message_id)

async def delete_prev_msgs(chat_id, state):
    data = await state.get_data()
    prev_msgs = data.get('prev_msgs', [])
    for mid in prev_msgs:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass

@dp.callback_query_handler(lambda c: c.data == "find")
async def find_client_start(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_find"))
    msg = await call.message.answer("Введите номер телефона или Telegram:", reply_markup=kb)
    await state.update_data(prev_msgs=[msg.message_id])
    await state.set_state("find_client")

@dp.message_handler(state="find_client")
async def find_client_input(message: types.Message, state: FSMContext):
    identifier = message.text.strip()
    client = get_client_by_identifier(identifier)
    if not client:
        await message.answer("Клиент не найден")
        await state.finish()
        await message.answer("Главное меню", reply_markup=main_menu())
        return
    kb = edit_menu(client[0])
    text = format_client_info(client)
    if client[9]:
        with open(client[9], 'rb') as photo:
            msg = await message.answer_photo(photo=photo, caption=text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.finish()
    await schedule_delete_message(msg.chat.id, msg.message_id)

@dp.callback_query_handler(lambda c: c.data.startswith("cancel_"))
async def cancel_any(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer("Главное меню", reply_markup=main_menu())
    try:
        await call.message.delete()
    except:
        pass

@dp.callback_query_handler(lambda c: c.data.startswith("save_"))
async def save_edit(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Изменения сохранены")
    await call.message.delete()
    await call.message.answer("Главное меню", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith("edit_"))
async def edit_field(call: types.CallbackQuery, state: FSMContext):
    field, client_id = call.data.split("_")[1], int(call.data.split("_")[2])
    client = get_client_by_id(client_id)
    if field == "phone":
        await call.message.answer("Введите новый номер телефона или Telegram:")
        await state.set_state("edit_phone")
        await state.update_data(edit_client_id=client_id)
    elif field == "birth":
        await call.message.answer("Введите новую дату рождения (дд.мм.гггг) или \"отсутствует\":")
        await state.set_state("edit_birth")
        await state.update_data(edit_client_id=client_id)
    elif field == "acc":
        await call.message.answer("Введите email, пароль от аккаунта и пароль от почты (три строки):")
        await state.set_state("edit_acc")
        await state.update_data(edit_client_id=client_id)
    elif field == "console":
        kb = InlineKeyboardMarkup(row_width=3)
        kb.add(InlineKeyboardButton("PS4", callback_data=f"edit_console_PS4_{client_id}"),
               InlineKeyboardButton("PS5", callback_data=f"edit_console_PS5_{client_id}"),
               InlineKeyboardButton("PS4/PS5", callback_data=f"edit_console_PS4/PS5_{client_id}"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit"))
        await call.message.answer("Какие консоли?", reply_markup=kb)
    elif field == "region":
        kb = InlineKeyboardMarkup(row_width=3)
        kb.add(InlineKeyboardButton("укр", callback_data=f"edit_region_укр_{client_id}"),
               InlineKeyboardButton("тур", callback_data=f"edit_region_тур_{client_id}"),
               InlineKeyboardButton("другое", callback_data=f"edit_region_другое_{client_id}"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit"))
        await call.message.answer("Выберите регион аккаунта:", reply_markup=kb)
    elif field == "reserve":
        await call.message.answer("Загрузите новый скриншот с резерв кодами:")
        await state.set_state("edit_reserve")
        await state.update_data(edit_client_id=client_id)
    elif field == "games":
        await call.message.answer("Введите новый список игр (каждая с новой строки):")
        await state.set_state("edit_games")
        await state.update_data(edit_client_id=client_id)
    elif field == "sub":
        await call.message.answer("Введите новые данные по подписке. Пока реализована только замена вручную.")
        await state.set_state("edit_sub")
        await state.update_data(edit_client_id=client_id)

@dp.message_handler(state="edit_phone")
async def edit_phone(message: types.Message, state: FSMContext):
    client_id = (await state.get_data()).get('edit_client_id')
    client = get_client_by_id(client_id)
    updated = dict(zip(['id', 'identifier', 'identifier_type', 'birth_date', 'email', 'acc_pass', 'mail_pass', 'consoles', 'region', 'reserve_codes_path', 'subs_data', 'games'], client))
    updated['identifier'] = message.text.strip()
    update_client(client_id, updated)
    await message.answer("Изменения обновлены")
    await message.answer(format_client_info(get_client_by_id(client_id)), reply_markup=edit_menu(client_id))
    await state.finish()

@dp.message_handler(state="edit_birth")
async def edit_birth(message: types.Message, state: FSMContext):
    client_id = (await state.get_data()).get('edit_client_id')
    value = message.text.strip()
    client = get_client_by_id(client_id)
    updated = dict(zip(['id', 'identifier', 'identifier_type', 'birth_date', 'email', 'acc_pass', 'mail_pass', 'consoles', 'region', 'reserve_codes_path', 'subs_data', 'games'], client))
    updated['birth_date'] = value
    update_client(client_id, updated)
    await message.answer("Изменения обновлены")
    await message.answer(format_client_info(get_client_by_id(client_id)), reply_markup=edit_menu(client_id))
    await state.finish()

@dp.message_handler(state="edit_acc")
async def edit_acc(message: types.Message, state: FSMContext):
    lines = message.text.strip().split('\n')
    if len(lines) < 2:
        await message.answer("Введите email, пароль от аккаунта и пароль от почты (три строки):")
        return
    email = lines[0]
    acc_pass = lines[1]
    mail_pass = lines[2] if len(lines) > 2 else ""
    client_id = (await state.get_data()).get('edit_client_id')
    client = get_client_by_id(client_id)
    updated = dict(zip(['id', 'identifier', 'identifier_type', 'birth_date', 'email', 'acc_pass', 'mail_pass', 'consoles', 'region', 'reserve_codes_path', 'subs_data', 'games'], client))
    updated['email'] = email
    updated['acc_pass'] = acc_pass
    updated['mail_pass'] = mail_pass
    update_client(client_id, updated)
    await message.answer("Изменения обновлены")
    await message.answer(format_client_info(get_client_by_id(client_id)), reply_markup=edit_menu(client_id))
    await state.finish()

@dp.message_handler(state="edit_games")
async def edit_games(message: types.Message, state: FSMContext):
    games = [line.strip() for line in message.text.strip().split('\n') if line.strip()]
    games_str = ' —— '.join(games) if games else "нет"
    client_id = (await state.get_data()).get('edit_client_id')
    client = get_client_by_id(client_id)
    updated = dict(zip(['id', 'identifier', 'identifier_type', 'birth_date', 'email', 'acc_pass', 'mail_pass', 'consoles', 'region', 'reserve_codes_path', 'subs_data', 'games'], client))
    updated['games'] = games_str
    update_client(client_id, updated)
    await message.answer("Изменения обновлены")
    await message.answer(format_client_info(get_client_by_id(client_id)), reply_markup=edit_menu(client_id))
    await state.finish()

@dp.message_handler(state="edit_reserve", content_types=types.ContentType.PHOTO)
async def edit_reserve_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    path = f"reserve_{file.file_unique_id}.jpg"
    await bot.download_file(file.file_path, path)
    client_id = (await state.get_data()).get('edit_client_id')
    client = get_client_by_id(client_id)
    updated = dict(zip(['id', 'identifier', 'identifier_type', 'birth_date', 'email', 'acc_pass', 'mail_pass', 'consoles', 'region', 'reserve_codes_path', 'subs_data', 'games'], client))
    updated['reserve_codes_path'] = path
    update_client(client_id, updated)
    await message.answer("Изменения обновлены")
    await message.answer(format_client_info(get_client_by_id(client_id)), reply_markup=edit_menu(client_id))
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

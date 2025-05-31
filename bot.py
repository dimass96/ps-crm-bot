# bot.py — полный, актуальный под aiogram 3.x, со всеми твоими правками и сохранением базы в /data

import asyncio
import os
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cryptography.fernet import Fernet

# Файлы базы и ключа — путь /data для volume
DATA_DIR = "/data"
DB_FILE = os.path.join(DATA_DIR, "clients_db.json")
KEY_FILE = os.path.join(DATA_DIR, "secret.key")

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

def generate_key():
    if not os.path.exists(KEY_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)

def load_key():
    with open(KEY_FILE, "rb") as f:
        return f.read()

def encrypt_data(data: str, key: bytes) -> bytes:
    return Fernet(key).encrypt(data.encode())

def decrypt_data(token: bytes, key: bytes) -> str:
    return Fernet(key).decrypt(token).decode()

generate_key()
ENCRYPT_KEY = load_key()

def load_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "rb") as f:
        encrypted = f.read()
        if not encrypted:
            return []
        try:
            decrypted = decrypt_data(encrypted, ENCRYPT_KEY)
            return json.loads(decrypted)
        except Exception:
            return []

def save_db(data):
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as orig, open(DB_FILE + "_backup", "wb") as backup:
            backup.write(orig.read())
    encrypted = encrypt_data(json.dumps(data, ensure_ascii=False, indent=2), ENCRYPT_KEY)
    with open(DB_FILE, "wb") as f:
        f.write(encrypted)

def get_next_client_id(clients):
    if not clients:
        return 1
    return max(c["id"] for c in clients) + 1

def find_clients(query):
    clients = load_db()
    results = []
    q = query.lower()
    for c in clients:
        if (q in str(c.get("contact", "")).lower() or
            q in str(c.get("birth_date", "")).lower() or
            q in str(c.get("region", "")).lower() or
            q in str(c.get("console", "")).lower() or
            any(q in str(val).lower() for val in c.get("games", [])) or
            q in str(c.get("account", {}).get("login", "")).lower() or
            q in str(c.get("account", {}).get("password", "")).lower() or
            q in str(c.get("account", {}).get("mail_pass", "")).lower() or
            any(q in str(sub.get("name", "")).lower() or q in str(sub.get("duration", "")).lower() for sub in c.get("subscriptions", []))
        ):
            results.append(c)
    return results

def save_new_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == client["id"]:
            clients[i] = client
            save_db(clients)
            return
    clients.append(client)
    save_db(clients)

def delete_client(client_id):
    clients = load_db()
    clients = [c for c in clients if c["id"] != client_id]
    save_db(clients)

class AddEditClient(StatesGroup):
    contact = State()
    birthdate_yesno = State()
    birthdate = State()
    account = State()
    region = State()
    console = State()
    subscriptions_yesno = State()
    subscriptions_count = State()
    sub_1_type = State()
    sub_1_duration = State()
    sub_1_start = State()
    sub_2_type = State()
    sub_2_duration = State()
    sub_2_start = State()
    games_yesno = State()
    games_input = State()
    reserve_yesno = State()
    reserve_photo = State()
    final_card = State()
    edit_choose = State()
    edit_input = State()
    edit_games = State()
    edit_subs = State()
    edit_reserve = State()
    awaiting_confirm = State()
    edit_subs_master = State()
    edit_subs_total = State()
    edit_sub_1_type = State()
    edit_sub_1_duration = State()
    edit_sub_1_start = State()
    edit_sub_2_type = State()
    edit_sub_2_duration = State()
    edit_sub_2_start = State()
    awaiting_backup_choice = State()
    awaiting_confirm_clear = State()
    awaiting_confirm_restore = State()

def region_btns():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="(укр)")],
            [KeyboardButton(text="(тур)")],
            [KeyboardButton(text="(польша)")],
            [KeyboardButton(text="(британия)")],
            [KeyboardButton(text="(другой)")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def console_btns():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS4"), KeyboardButton(text="PS5")],
            [KeyboardButton(text="PS4/PS5")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def edit_keyboard(client):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Номер/TG", callback_data=f"edit_contact_{client['id']}"),
            InlineKeyboardButton(text="🔐 Данные", callback_data=f"edit_account_{client['id']}"),
        ],
        [
            InlineKeyboardButton(text="💳 Подписка", callback_data=f"edit_sub_{client['id']}"),
            InlineKeyboardButton(text="🎲 Игры", callback_data=f"edit_games_{client['id']}"),
        ],
        [
            InlineKeyboardButton(text="🖼 Рез. коды", callback_data=f"edit_reserve_{client['id']}"),
            InlineKeyboardButton(text="🎮 Консоль", callback_data=f"edit_console_{client['id']}"),
        ],
        [
            InlineKeyboardButton(text="📅 Дата рожд.", callback_data=f"edit_birth_{client['id']}"),
            InlineKeyboardButton(text="🌍 Регион", callback_data=f"edit_region_{client['id']}"),
        ],
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_{client['id']}")
        ]
    ])

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔍 Найти клиента")],
            [KeyboardButton(text="📦 База")],
            [KeyboardButton(text="📊 Статистика")]
        ], resize_keyboard=True
    )

def base_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Выгрузить всю базу в чат")],
            [KeyboardButton(text="🔄 Заканчивается подписка (7д)")],
            [KeyboardButton(text="🎉 Скоро ДР (7д)")],
            [KeyboardButton(text="⚠️ Без подписки")],
            [KeyboardButton(text="⏯️ Сделать бэкап базы")],
            [KeyboardButton(text="▶️ Восстановить из бэкапа")],
            [KeyboardButton(text="🗑️ Очистить базу")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def format_card(client, show_photo_id=False):
    lines = []
    contact = client.get("contact", "—")
    bdate = client.get("birth_date", "отсутствует")
    console = client.get("console", "—")
    lines.append(f"<b>{contact}</b> | {bdate} ({console})")
    acc = client.get("account", {})
    login = acc.get("login", "")
    password = acc.get("password", "")
    mail_pass = acc.get("mail_pass", "")
    if login:
        lines.append(f"🔐 <b>{login}</b>; {password}")
    if mail_pass:
        lines.append(f"✉️ Почта-пароль: {mail_pass}")
    else:
        lines.append(f"✉️ Почта-пароль:")
    subs = client.get("subscriptions", [])
    if subs and subs[0].get("name") != "отсутствует":
        for sub in subs:
            lines.append(f"\n<b>🗓 {sub.get('name', '')} {sub.get('duration', '')}</b>")
            lines.append(f"📅 {sub.get('start', '')} → {sub.get('end', '')}")
    else:
        lines.append(f"\n<b>Без подписки</b>")
    region = client.get("region", "—")
    lines.append(f"\n🌍 Регион: {region}")
    games = client.get("games", [])
    if games:
        lines.append("\n🎮 Игры:")
        for game in games:
            lines.append(f"• {game}")
    reserve_photo_id = client.get("reserve_photo_id")
    return "\n".join(lines), reserve_photo_id if show_photo_id else None

async def clear_chat(message: types.Message):
    try:
        chat = message.chat.id
        async for msg in bot.get_chat_history(chat, limit=100):
            try:
                await bot.delete_message(chat, msg.message_id)
            except Exception:
                continue
    except Exception:
        pass

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await clear_chat(message)
    await message.answer("Главное меню", reply_markup=main_menu())

# --- ДОБАВЛЕНИЕ КЛИЕНТА ---
@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите номер телефона или Telegram (@username):",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.contact)

@dp.message(AddEditClient.contact)
async def step_contact(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    await state.update_data(contact=message.text.strip())
    await message.answer("Дата рождения есть?",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                                       [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.birthdate_yesno)

@dp.message(AddEditClient.birthdate_yesno)
async def step_birthdate_ask(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(birth_date="отсутствует")
        await ask_account(message, state)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.birthdate)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.birthdate)
async def step_birthdate(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except Exception:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    await state.update_data(birth_date=message.text.strip())
    await ask_account(message, state)

async def ask_account(message, state: FSMContext):
    await message.answer("Введи:\n1. Логин\n2. Пароль\n3. Почта-пароль (можно пропустить)\n\nКаждый пункт с новой строки.",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.account)

@dp.message(AddEditClient.account)
async def step_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    rows = message.text.strip().split("\n")
    login = rows[0].strip() if len(rows) > 0 else ""
    password = rows[1].strip() if len(rows) > 1 else ""
    mail_pass = rows[2].strip() if len(rows) > 2 else ""
    await state.update_data(account={"login": login, "password": password, "mail_pass": mail_pass})
    await message.answer("Выбери регион аккаунта:", reply_markup=region_btns())
    await state.set_state(AddEditClient.region)

@dp.message(AddEditClient.region)
async def step_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text not in ("(укр)", "(тур)", "(польша)", "(британия)", "(другой)"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(region=message.text)
    await message.answer("Какая консоль?", reply_markup=console_btns())
    await state.set_state(AddEditClient.console)

@dp.message(AddEditClient.console)
async def step_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text not in ("PS4", "PS5", "PS4/PS5"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(console=message.text)
    await message.answer("Есть подписки?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                  [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.subscriptions_yesno)

@dp.message(AddEditClient.subscriptions_yesno)
async def step_subs_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await ask_games(message, state)
        return
    if message.text == "Да":
        await message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                      [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.subscriptions_count)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.subscriptions_count)
async def step_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Одна":
        await state.update_data(subs_total=1)
        await sub_select(message, state, sub_num=1, only_one=True)
        return
    if message.text == "Две":
        await state.update_data(subs_total=2)
        await sub_select(message, state, sub_num=1, only_one=False)
        return
    await message.answer("Нажмите кнопку!")

async def sub_select(message, state: FSMContext, sub_num=1, only_one=False):
    if sub_num == 1:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
                [KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
        await message.answer("Выберите тип подписки:", reply_markup=kb)
        await state.set_state(AddEditClient.sub_1_type)
    else:
        data = await state.get_data()
        prev = data.get("sub_1_type")
        if prev == "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="Нет подписки")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="Нет подписки")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
        await state.set_state(AddEditClient.sub_2_type)

@dp.message(AddEditClient.sub_1_type)
async def sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет подписки":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await ask_games(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(sub_1_type=message.text)
    # Сроки подписки зависят от типа
    if message.text.startswith("PS Plus"):
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    await message.answer("Выберите срок подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_1_duration)

@dp.message(AddEditClient.sub_1_duration)
async def sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text not in ("1м", "3м", "12м"):
        # для EA Play - 1м или 12м
        if message.text not in ("1м", "12м"):
            await message.answer("Нажмите кнопку!")
            return
    await state.update_data(sub_1_duration=message.text)
    await message.answer("Введите дату оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.sub_1_start)

@dp.message(AddEditClient.sub_1_start)
async def sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except Exception:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    await state.update_data(sub_1_start=message.text.strip())
    data = await state.get_data()
    if data.get("subs_total") == 1:
        # Собираем подписки
        subs = [{
            "name": data.get("sub_1_type"),
            "duration": data.get("sub_1_duration"),
            "start": data.get("sub_1_start"),
            "end": calc_end_date(data.get("sub_1_start"), data.get("sub_1_duration"))
        }]
        await state.update_data(subscriptions=subs)
        await ask_games(message, state)
        return
    else:
        await sub_select(message, state, sub_num=2, only_one=False)

@dp.message(AddEditClient.sub_2_type)
async def sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        subs = [{
            "name": data.get("sub_1_type"),
            "duration": data.get("sub_1_duration"),
            "start": data.get("sub_1_start"),
            "end": calc_end_date(data.get("sub_1_start"), data.get("sub_1_duration"))
        }]
        await state.update_data(subscriptions=subs)
        await ask_games(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(sub_2_type=message.text)
    if message.text.startswith("PS Plus"):
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    await message.answer("Выберите срок подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_2_duration)

@dp.message(AddEditClient.sub_2_duration)
async def sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text not in ("1м", "3м", "12м"):
        if message.text not in ("1м", "12м"):
            await message.answer("Нажмите кнопку!")
            return
    await state.update_data(sub_2_duration=message.text)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.sub_2_start)

@dp.message(AddEditClient.sub_2_start)
async def sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except Exception:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    await state.update_data(sub_2_start=message.text.strip())
    data = await state.get_data()
    subs = [
        {
            "name": data.get("sub_1_type"),
            "duration": data.get("sub_1_duration"),
            "start": data.get("sub_1_start"),
            "end": calc_end_date(data.get("sub_1_start"), data.get("sub_1_duration"))
        },
        {
            "name": data.get("sub_2_type"),
            "duration": data.get("sub_2_duration"),
            "start": data.get("sub_2_start"),
            "end": calc_end_date(data.get("sub_2_start"), data.get("sub_2_duration"))
        }
    ]
    await state.update_data(subscriptions=subs)
    await ask_games(message, state)

def calc_end_date(start_str, duration_str):
    dt = datetime.strptime(start_str, "%d.%m.%Y")
    months = {"1м": 1, "3м": 3, "12м": 12}
    months_add = months.get(duration_str, 0)
    year = dt.year + (dt.month + months_add - 1) // 12
    month = (dt.month + months_add - 1) % 12 + 1
    day = dt.day
    try:
        end_date = datetime(year, month, day)
    except:
        # например, 31 февраля - берем последний день месяца
        end_date = datetime(year, month+1, 1) - timedelta(days=1)
    return end_date.strftime("%d.%m.%Y")

async def ask_games(message, state: FSMContext):
    await message.answer("Есть оформленные игры?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                  [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.games_yesno)

@dp.message(AddEditClient.games_yesno)
async def step_games_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(games=[])
        await ask_reserve(message, state)
        return
    if message.text == "Да":
        await message.answer("Введите игры по одной в строке. По окончании отправьте пустое сообщение.",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(games=[])
        await state.set_state(AddEditClient.games_input)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.games_input)
async def step_games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if not message.text.strip():
        # Пустое сообщение — конец ввода игр
        data = await state.get_data()
        await state.update_data(games=data.get("games", []))
        await ask_reserve(message, state)
        return
    data = await state.get_data()
    games = data.get("games", [])
    games.append(message.text.strip())
    await state.update_data(games=games)
    await message.answer("Добавлено: " + message.text.strip())

async def ask_reserve(message, state: FSMContext):
    await message.answer("Есть резервные коды?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                  [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.reserve_yesno)

@dp.message(AddEditClient.reserve_yesno)
async def step_reserve_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(reserve_photo_id=None)
        await finish_add(message, state)
        return
    if message.text == "Да":
        await message.answer("Пришлите скриншот с резервными кодами:",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.reserve_photo)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.reserve_photo, F.content_type == ContentType.PHOTO)
async def step_reserve_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    photo_id = photo.file_id
    await state.update_data(reserve_photo_id=photo_id)
    await finish_add(message, state)

@dp.message(AddEditClient.reserve_photo)
async def reserve_photo_wrong_type(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, пришлите именно фото.")

async def finish_add(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_id = get_next_client_id(load_db())
    client = {
        "id": new_id,
        "contact": data.get("contact"),
        "birth_date": data.get("birth_date"),
        "account": data.get("account"),
        "region": data.get("region"),
        "console": data.get("console"),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id"),
        "added_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    }
    save_new_client(client)
    await clear_chat(message)
    card_text, photo_id = format_card(client, show_photo_id=True)
    if photo_id:
        await message.answer_photo(photo_id, caption=card_text, reply_markup=edit_keyboard(client))
    else:
        await message.answer(card_text, reply_markup=edit_keyboard(client))
    await state.clear()

# --- ПОИСК ---
@dp.message(F.text == "🔍 Найти клиента")
async def search_start(message: types.Message):
    await message.answer("Введите номер телефона или Telegram для поиска:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message()
async def search_handle(message: types.Message):
    if message.text == "❌ Отмена":
        await clear_chat(message)
        await message.answer("Отмена.", reply_markup=main_menu())
        return
    results = find_clients(message.text)
    if not results:
        await message.answer("Клиент не найден.", reply_markup=main_menu())
        return
    for client in results:
        card_text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=card_text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(card_text, reply_markup=edit_keyboard(client))

# --- ОБРАБОТКА НАЖАТИЙ ИЗМЕНЕНИЯ ---
@dp.callback_query()
async def callbacks_handler(callback: types.CallbackQuery):
    data = callback.data
    parts = data.split("_")
    if len(parts) < 2:
        await callback.answer("Ошибка команды.")
        return
    cmd = parts[0]
    client_id = int(parts[-1])
    clients = load_db()
    client = next((c for c in clients if c["id"] == client_id), None)
    if not client:
        await callback.answer("Клиент не найден.")
        return

    if cmd == "edit":
        field = parts[1]
        await callback.message.answer(f"Введите новое значение для {field}:",
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        state = dp.current_state(user=callback.from_user.id)
        await state.update_data(edit_field=field, edit_client_id=client_id)
        await state.set_state(AddEditClient.edit_input)
        await callback.answer()
    elif cmd == "save":
        await callback.message.answer("Данные сохранены.", reply_markup=main_menu())
        await callback.answer()
    else:
        await callback.answer("Неизвестная команда.")

@dp.message(AddEditClient.edit_input)
async def edit_input_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await message.answer("Отмена.", reply_markup=main_menu())
        return
    data = await state.get_data()
    field = data.get("edit_field")
    client_id = data.get("edit_client_id")
    clients = load_db()
    client = next((c for c in clients if c["id"] == client_id), None)
    if not client:
        await message.answer("Клиент не найден.")
        await state.clear()
        return
    # Пример простой замены поля
    if field == "contact":
        client["contact"] = message.text.strip()
    elif field == "birth":
        client["birth_date"] = message.text.strip()
    elif field == "region":
        client["region"] = message.text.strip()
    elif field == "console":
        client["console"] = message.text.strip()
    elif field == "account":
        client["account"] = {"login": message.text.strip()}  # упростил для примера
    else:
        await message.answer("Изменение данного поля пока не реализовано.")
        return
    update_client(client)
    await message.answer("Изменения сохранены.", reply_markup=edit_keyboard(client))
    await state.clear()

# --- БАЗА ---
@dp.message(F.text == "📦 База")
async def base_menu_handler(message: types.Message):
    await message.answer("Меню базы:", reply_markup=base_menu())

@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Отмена.", reply_markup=main_menu())

# --- ДЕЙСТВИЯ В БАЗЕ ---
@dp.message(F.text == "📩 Выгрузить всю базу в чат")
async def dump_db(message: types.Message):
    clients = load_db()
    if not clients:
        await message.answer("База пуста.")
        return
    for client in clients:
        card_text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=card_text)
        else:
            await message.answer(card_text)
    await message.answer("Выгрузка базы завершена.", reply_markup=base_menu())

@dp.message(F.text == "🔄 Заканчивается подписка (7д)")
async def subs_ending(message: types.Message):
    clients = load_db()
    soon = datetime.now() + timedelta(days=7)
    filtered = []
    for c in clients:
        for sub in c.get("subscriptions", []):
            try:
                end_date = datetime.strptime(sub.get("end", "01.01.1900"), "%d.%m.%Y")
                if datetime.now() <= end_date <= soon:
                    filtered.append(c)
                    break
            except Exception:
                continue
    if not filtered:
        await message.answer("Нет подписок, заканчивающихся в ближайшие 7 дней.")
        return
    for client in filtered:
        card_text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=card_text)
        else:
            await message.answer(card_text)
    await message.answer("Отбор подписок завершён.", reply_markup=base_menu())

@dp.message(F.text == "🎉 Скоро ДР (7д)")
async def bday_soon(message: types.Message):
    clients = load_db()
    soon = datetime.now() + timedelta(days=7)
    filtered = []
    for c in clients:
        bd = c.get("birth_date")
        if not bd or bd == "отсутствует":
            continue
        try:
            bd_dt = datetime.strptime(bd, "%d.%m.%Y")
            bd_this_year = bd_dt.replace(year=datetime.now().year)
            if datetime.now() <= bd_this_year <= soon:
                filtered.append(c)
        except Exception:
            continue
    if not filtered:
        await message.answer("Нет клиентов с ДР в ближайшие 7 дней.")
        return
    for client in filtered:
        card_text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=card_text)
        else:
            await message.answer(card_text)
    await message.answer("Отбор по ДР завершён.", reply_markup=base_menu())

@dp.message(F.text == "⚠️ Без подписки")
async def no_subs(message: types.Message):
    clients = load_db()
    filtered = []
    for c in clients:
        subs = c.get("subscriptions", [])
        if not subs or (len(subs) == 1 and subs[0].get("name") == "отсутствует"):
            filtered.append(c)
    if not filtered:
        await message.answer("Все клиенты с подписками.")
        return
    for client in filtered:
        card_text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=card_text)
        else:
            await message.answer(card_text)
    await message.answer("Отбор без подписок завершён.", reply_markup=base_menu())

@dp.message(F.text == "⏯️ Сделать бэкап базы")
async def backup_db(message: types.Message):
    if os.path.exists(DB_FILE):
        backup_path = DB_FILE + ".bak"
        with open(DB_FILE, "rb") as fsrc, open(backup_path, "wb") as fdst:
            fdst.write(fsrc.read())
        await message.answer("Бэкап базы сделан.", reply_markup=main_menu())
    else:
        await message.answer("Базы нет.", reply_markup=base_menu())

@dp.message(F.text == "▶️ Восстановить из бэкапа")
async def restore_db(message: types.Message):
    backup_path = DB_FILE + ".bak"
    if os.path.exists(backup_path):
        with open(backup_path, "rb") as fsrc, open(DB_FILE, "wb") as fdst:
            fdst.write(fsrc.read())
        await message.answer("База восстановлена из бэкапа.", reply_markup=main_menu())
    else:
        await message.answer("Бэкап не найден.", reply_markup=base_menu())

@dp.message(F.text == "🗑️ Очистить базу")
async def clear_db_prompt(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]], resize_keyboard=True)
    await message.answer("Вы уверены, что хотите очистить базу?", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm_clear)

@dp.message(AddEditClient.awaiting_confirm_clear)
async def clear_db_confirm(message: types.Message, state: FSMContext):
    if message.text == "Да":
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        await message.answer("База очищена.", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("Отмена.", reply_markup=main_menu())
        await state.clear()

# --- СТАТИСТИКА ---
@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    clients = load_db()
    n_clients = len(clients)
    n_no_subs = 0
    n_with_subs = 0
    subs_types = {}
    two_subs = 0
    region_map = {"(укр)":0, "(тур)":0, "(польша)":0, "(британия)":0, "(другой)":0}
    n_games = 0
    soon_subs = 0
    soon_bd = 0

    now = datetime.now()
    soon_limit = now + timedelta(days=7)

    for c in clients:
        subs = c.get("subscriptions", [])
        if not subs or (len(subs) == 1 and subs[0].get("name") == "отсутствует"):
            n_no_subs += 1
        else:
            n_with_subs += 1
            if len(subs) == 2:
                two_subs += 1
            for sub in subs:
                nm = sub.get("name", "Неизвестно")
                subs_types[nm] = subs_types.get(nm, 0) + 1
                try:
                    end = datetime.strptime(sub.get("end", "01.01.1900"), "%d.%m.%Y")
                    if now <= end <= soon_limit:
                        soon_subs += 1
                except Exception:
                    pass
        region = c.get("region", "(другой)")
        if region in region_map:
            region_map[region] += 1
        else:
            region_map["(другой)"] += 1
        games = c.get("games", [])
        n_games += len(games)
        bd = c.get("birth_date")
        if bd and bd != "отсутствует":
            try:
                bd_dt = datetime.strptime(bd, "%d.%m.%Y")
                bd_this_year = bd_dt.replace(year=now.year)
                if now <= bd_this_year <= soon_limit:
                    soon_bd += 1
            except Exception:
                pass
    txt = f"<b>Статистика CRM</b>\n\n"
    txt += f"👤 Клиентов: {n_clients}\n"
    txt += f"✉️ Без подписки: {n_no_subs}\n"
    txt += f"💳 С подписками: {n_with_subs}\n"
    for k, v in subs_types.items():
        txt += f"— {k}: {v}\n"
    txt += f"🔁 Две подписки: {two_subs}\n\n"
    txt += f"🌍 Регионы:\n"
    for reg in ["(укр)", "(тур)", "(польша)", "(британия)", "(другой)"]:
        txt += f"{reg}: {region_map[reg]}\n"
    txt += f"\n🎮 Оформлено игр: {n_games}\n"
    txt += f"⏳ Подписки истекают (7 дней): {soon_subs}\n"
    txt += f"🎂 День рождения скоро: {soon_bd}\n"
    await message.answer(txt)

# --- ОСНОВНОЙ ЗАПУСК ---
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
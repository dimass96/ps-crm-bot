import asyncio
import os
import json
import shutil
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cryptography.fernet import Fernet

DB_FILE = "/data/clients_db.json"
KEY_FILE = "/data/secret.key"
API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

def generate_key():
    if not os.path.exists(KEY_FILE):
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True) if os.path.dirname(KEY_FILE) else None
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
        try:
            encrypted = f.read()
            if not encrypted:
                return []
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
    if not clients: return 1
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
    awaiting_clear_confirm = State()
    awaiting_clear_final = State()
    awaiting_confirm_restore = State()

def region_btns():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр")],
            [KeyboardButton(text="тур")],
            [KeyboardButton(text="(польша)")],
            [KeyboardButton(text="(британия)")],
            [KeyboardButton(text="другой")],
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
            except:
                continue
    except:
        pass

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
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

# --- Добавление клиента ---

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
            keyboard=[
                [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
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
    except:
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
    if message.text not in ("укр", "тур", "другой", "(польша)", "(британия)"):
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
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
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
            keyboard=[
                [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
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
            ], resize_keyboard=True
        )
        await message.answer("Выберите тип подписки:", reply_markup=kb)
        await state.set_state(AddEditClient.sub_1_type)
    else:
        data = await state.get_data()
        prev = data.get("sub_1_type")
        kb = None
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
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(sub_1_type=message.text)
    kb = None
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_1_duration)

@dp.message(AddEditClient.sub_1_duration)
async def sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    sub_1_type = data.get("sub_1_type")
    if (sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
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
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("sub_1_duration")
    months = int(duration.replace("м", ""))
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months*30)
    sub = {
        "name": data.get("sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end.strftime("%d.%m.%Y")
    }
    await state.update_data(sub_1=sub)
    subs_total = data.get("subs_total", 1)
    if subs_total == 2:
        await sub_select(message, state, sub_num=2)
    else:
        await state.update_data(subscriptions=[sub])
        await ask_games(message, state)

@dp.message(AddEditClient.sub_2_type)
async def sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        await state.update_data(subscriptions=[data.get("sub_1")])
        await ask_games(message, state)
        return
    data = await state.get_data()
    prev = data.get("sub_1_type")
    if prev == "EA Play":
        if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
            await message.answer("Выберите PS Plus!")
            return
    else:
        if message.text != "EA Play":
            await message.answer("Выберите EA Play!")
            return
    await state.update_data(sub_2_type=message.text)
    kb = None
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_2_duration)

@dp.message(AddEditClient.sub_2_duration)
async def sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    sub_2_type = data.get("sub_2_type")
    if (sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
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
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("sub_2_duration")
    months = int(duration.replace("м", ""))
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months*30)
    sub = {
        "name": data.get("sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end.strftime("%d.%m.%Y")
    }
    subs = [data.get("sub_1"), sub]
    await state.update_data(sub_2=sub, subscriptions=subs)
    await ask_games(message, state)

# --- Игры и резервные коды, финал ---

async def ask_games(message, state: FSMContext):
    await message.answer("Оформлены игры?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddEditClient.games_yesno)

@dp.message(AddEditClient.games_yesno)
async def games_yesno(message: types.Message, state: FSMContext):
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
        await message.answer("Введи список игр (каждая с новой строки):", 
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.games_input)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.games_input)
async def games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    await state.update_data(games=games)
    await ask_reserve(message, state)

async def ask_reserve(message, state: FSMContext):
    await message.answer("Есть ли резервные коды?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddEditClient.reserve_yesno)

@dp.message(AddEditClient.reserve_yesno)
async def reserve_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(reserve_photo_id=None)
        await finish_client(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот (фото):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.reserve_photo)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.reserve_photo)
async def reserve_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if not message.photo:
        await message.answer("Отправьте фото!")
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(reserve_photo_id=photo_id)
    await finish_client(message, state)

async def finish_client(message, state: FSMContext):
    data = await state.get_data()
    client = {
        "id": get_next_client_id(load_db()),
        "contact": data.get("contact", ""),
        "birth_date": data.get("birth_date", "отсутствует"),
        "account": data.get("account", {}),
        "region": data.get("region", ""),
        "console": data.get("console", ""),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id")
    }
    save_new_client(client)
    await state.clear()
    await clear_chat(message)
    text, photo_id = format_card(client, show_photo_id=True)
    if photo_id:
        await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
    else:
        await message.answer(text, reply_markup=edit_keyboard(client))

# --- Поиск клиента ---

@dp.message(F.text == "🔍 Найти клиента")
async def find_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer(
        "Введите любой поисковый запрос (номер/TG, имя, регион, логин, игра и т.д.):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(AddEditClient.edit_input)

@dp.message(AddEditClient.edit_input)
async def do_find(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    # Если редактируем
    if data.get("edit_id") and data.get("edit_field"):
        cid = data.get("edit_id")
        field = data.get("edit_field")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                if field == "contact":
                    c["contact"] = message.text.strip()
                elif field == "birth_date":
                    c["birth_date"] = message.text.strip()
                elif field == "account":
                    rows = message.text.strip().split("\n")
                    login = rows[0].strip() if len(rows) > 0 else ""
                    password = rows[1].strip() if len(rows) > 1 else ""
                    mail_pass = rows[2].strip() if len(rows) > 2 else ""
                    c["account"] = {"login": login, "password": password, "mail_pass": mail_pass}
                elif field == "console":
                    c["console"] = message.text.strip()
                elif field == "region":
                    c["region"] = message.text.strip()
                clients[i] = c
                save_db(clients)
                await state.clear()
                await clear_chat(message)
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    await message.answer(text, reply_markup=edit_keyboard(c))
                return
        await message.answer("Ошибка при обновлении.")
        await state.clear()
        return
    # Обычный поиск
    results = find_clients(message.text.strip())
    if not results:
        await message.answer("Клиентов не найдено.")
        await start_cmd(message, state)
        return
    for client in results:
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(text, reply_markup=edit_keyboard(client))

# --- Обработка inline кнопок редактирования ---

@dp.callback_query(F.data.startswith("edit_"))
async def edit_fields(callback: types.CallbackQuery, state: FSMContext):
    act, field, cid = callback.data.split("_", 2)
    cid = int(cid)
    clients = load_db()
    client = next((c for c in clients if c["id"] == cid), None)
    if not client:
        await callback.message.answer("Клиент не найден!")
        return
    await state.clear()
    await state.update_data(edit_id=cid)
    if field == "contact":
        await callback.message.answer(
            "Введите новый номер телефона или Telegram:",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="contact")
        return
    if field == "birth":
        await callback.message.answer(
            "Введите новую дату рождения (дд.мм.гггг) или 'отсутствует':",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="birth_date")
        return
    if field == "account":
        await callback.message.answer(
            "Введи:\n1. Логин\n2. Пароль\n3. Почта-пароль (можно пропустить)\n\nКаждый пункт с новой строки.",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="account")
        return
    if field == "console":
        await callback.message.answer("Выбери консоль:", reply_markup=console_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="console")
        return
    if field == "region":
        await callback.message.answer("Выбери регион аккаунта:", reply_markup=region_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="region")
        return
    if field == "reserve":
        await callback.message.answer(
            "Загрузите новое фото резерв-кодов:",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(AddEditClient.edit_reserve)
        return
    if field == "sub":
        await callback.message.answer(
            "Сколько подписок?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                    [KeyboardButton(text="Нет подписки")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True
            )
        )
        await state.set_state(AddEditClient.edit_subs_total)
        return
    if field == "games":
        await callback.message.answer(
            "Введи список игр (каждая с новой строки):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(AddEditClient.edit_games)
        return

# (Обработчики редактирования игр, резервных кодов, подписок, сохранения изменений и остальные идут дальше...)

# --- Отмена в любом месте ---

@dp.message(F.text == "❌ Отмена")
async def cancel_any(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Главное меню", reply_markup=main_menu())

# --- Меню базы и подтверждения очистки ---

@dp.message(F.text == "📦 База")
async def base_menu_handler(message: types.Message, state: FSMContext):
    await clear_chat(message)
    await message.answer("Меню базы данных:", reply_markup=base_menu())

@dp.message(F.text == "🗑️ Очистить базу")
async def base_clear_request(message: types.Message, state: FSMContext):
    await message.answer("Вы уверены, что хотите очистить базу? Выберите действие:",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[[KeyboardButton(text="Да")], [KeyboardButton(text="Нет")]], resize_keyboard=True))
    await state.set_state(AddEditClient.awaiting_clear_confirm)

@dp.message(AddEditClient.awaiting_clear_confirm)
async def base_clear_confirm(message: types.Message, state: FSMContext):
    if message.text == "Нет" or message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await message.answer("Действие отменено.", reply_markup=base_menu())
        return
    if message.text == "Да":
        await message.answer("Это действие необратимо! Подтвердите очистку базы кнопкой ниже:",
                             reply_markup=ReplyKeyboardMarkup(
                                 keyboard=[[KeyboardButton(text="Подтверждаю")], [KeyboardButton(text="Нет")]], resize_keyboard=True))
        await state.set_state(AddEditClient.awaiting_clear_final)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.awaiting_clear_final)
async def base_clear_final(message: types.Message, state: FSMContext):
    if message.text == "Подтверждаю":
        save_db([])
        await state.clear()
        await clear_chat(message)
        await message.answer("База успешно очищена.", reply_markup=base_menu())
        return
    else:
        await state.clear()
        await clear_chat(message)
        await message.answer("Очистка базы отменена.", reply_markup=base_menu())

# --- Статистика ---

@dp.message(F.text == "📊 Статистика")
async def stats_handler(message: types.Message):
    clients = load_db()
    n_clients = len(clients)
    n_no_subs = sum(1 for c in clients if c.get("subscriptions", [{}])[0].get("name") == "отсутствует")
    n_with_subs = n_clients - n_no_subs
    subs_types = {}
    two_subs = 0
    region_map = {"укр": 0, "тур": 0, "(польша)": 0, "(британия)": 0, "другой": 0}
    n_games = 0
    soon_subs = 0
    soon_bd = 0
    now = datetime.now()
    for c in clients:
        subs = c.get("subscriptions", [])
        if len(subs) > 1:
            two_subs += 1
        for sub in subs:
            name = sub.get("name", "")
            if name and name != "отсутствует":
                subs_types[name] = subs_types.get(name, 0) + 1
                end_str = sub.get("end", "")
                try:
                    end_date = datetime.strptime(end_str, "%d.%m.%Y")
                    if 0 <= (end_date - now).days <= 7:
                        soon_subs += 1
                except:
                    pass
        reg = c.get("region", "другой")
        if reg not in region_map:
            reg = "другой"
        region_map[reg] += 1
        if c.get("games"):
            n_games += 1
        bd_str = c.get("birth_date", "")
        try:
            bd_date = datetime.strptime(bd_str, "%d.%m.%Y")
            bd_this_year = bd_date.replace(year=now.year)
            delta_days = (bd_this_year - now).days
            if 0 <= delta_days <= 7:
                soon_bd += 1
        except:
            pass
    txt = f"<b>Статистика CRM</b>\n\n"
    txt += f"👤 Клиентов: {n_clients}\n"
    txt += f"✉️ Без подписки: {n_no_subs}\n"
    txt += f"💳 С подписками: {n_with_subs}\n"
    for k, v in subs_types.items():
        txt += f"— {k}: {v}\n"
    txt += f"🔁 Две подписки: {two_subs}\n\n"
    txt += f"🌍 Регионы:\n"
    for reg in ["укр", "тур", "(польша)", "(британия)", "другой"]:
        txt += f"{reg}: {region_map[reg]}\n"
    txt += f"\n🎮 Оформлено игр: {n_games}\n"
    txt += f"⏳ Подписки истекают (7 дней): {soon_subs}\n"
    txt += f"🎂 День рождения скоро: {soon_bd}\n"
    await message.answer(txt)

# --- Выгрузка базы ---

@dp.message(F.text == "📩 Выгрузить всю базу в чат")
async def base_dump_chat(message: types.Message):
    clients = load_db()
    if not clients:
        await message.answer("База пуста.")
        return
    for c in clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "🔄 Заканчивается подписка (7д)")
async def base_expiring_subs(message: types.Message):
    clients = load_db()
    now = datetime.now()
    soon_clients = []
    for c in clients:
        subs = c.get("subscriptions", [])
        for sub in subs:
            end_str = sub.get("end", "")
            try:
                end_date = datetime.strptime(end_str, "%d.%m.%Y")
                if 0 <= (end_date - now).days <= 7:
                    soon_clients.append(c)
                    break
            except:
                pass
    if not soon_clients:
        await message.answer("Клиентов с истекающими подписками нет.")
        return
    for c in soon_clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "🎉 Скоро ДР (7д)")
async def base_soon_birthdays(message: types.Message):
    clients = load_db()
    now = datetime.now()
    soon_clients = []
    for c in clients:
        bd_str = c.get("birth_date", "")
        try:
            bd_date = datetime.strptime(bd_str, "%d.%m.%Y")
            bd_this_year = bd_date.replace(year=now.year)
            delta_days = (bd_this_year - now).days
            if 0 <= delta_days <= 7:
                soon_clients.append(c)
        except:
            pass
    if not soon_clients:
        await message.answer("Клиентов с днем рождения в ближайшие 7 дней нет.")
        return
    for c in soon_clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "⚠️ Без подписки")
async def base_no_subs(message: types.Message):
    clients = load_db()
    no_subs_clients = [c for c in clients if c.get("subscriptions", [{}])[0].get("name") == "отсутствует"]
    if not no_subs_clients:
        await message.answer("Все клиенты имеют подписку.")
        return
    for c in no_subs_clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "⏯️ Сделать бэкап базы")
async def base_backup(message: types.Message):
    try:
        backup_path = DB_FILE + "_backup_" + datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy(DB_FILE, backup_path)
        await message.answer(f"Бэкап базы создан:\n{backup_path}")
    except Exception as e:
        await message.answer(f"Ошибка при создании бэкапа: {e}")

@dp.message(F.text == "▶️ Восстановить из бэкапа")
async def base_restore_request(message: types.Message, state: FSMContext):
    await message.answer("Вы уверены, что хотите восстановить базу из последнего бэкапа? Это перезапишет текущую базу.",
                         reply_markup=ReplyKeyboardMarkup(
                             keyboard=[[KeyboardButton(text="Да")], [KeyboardButton(text="Нет")]], resize_keyboard=True))
    await state.set_state(AddEditClient.awaiting_confirm_restore)

@dp.message(AddEditClient.awaiting_confirm_restore)
async def base_restore_confirm(message: types.Message, state: FSMContext):
    if message.text == "Да":
        backups = sorted([f for f in os.listdir("/data") if f.startswith("clients_db.json_backup")], reverse=True)
        if not backups:
            await message.answer("Бэкапы не найдены.")
            await state.clear()
            return
        latest_backup = os.path.join("/data", backups[0])
        try:
            shutil.copy(latest_backup, DB_FILE)
            await message.answer("База восстановлена из последнего бэкапа.")
        except Exception as e:
            await message.answer(f"Ошибка при восстановлении: {e}")
    else:
        await message.answer("Восстановление отменено.")
    await state.clear()

# --- Сохранение изменений после редактирования ---

@dp.callback_query(F.data.startswith("save_"))
async def save_client(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await clear_chat(callback.message)
    await callback.message.answer("Изменения сохранены! Возврат в главное меню.", reply_markup=main_menu())

# --- Основной цикл запуска бота ---

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
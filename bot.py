import asyncio
import os
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cryptography.fernet import Fernet

DB_FILE = "/data/clients_db.json"
KEY_FILE = "/data/secret.key"
BACKUP_DIR = "/data/backups"
os.makedirs(BACKUP_DIR, exist_ok=True)
API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

# --- ШИФРОВАНИЕ БД И БЭКАП ---
def generate_key():
    if not os.path.exists(KEY_FILE):
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

def backup_db():
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"clients_db_{now}.json")
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())
    return backup_path

def list_backups():
    return sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("clients_db_") and f.endswith(".json")])

def restore_db(backup_name):
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if os.path.exists(backup_path):
        with open(backup_path, "rb") as src, open(DB_FILE, "wb") as dst:
            dst.write(src.read())
        return True
    return False

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

def find_clients_no_subscription():
    clients = load_db()
    results = []
    for c in clients:
        subs = c.get("subscriptions", [])
        if not subs or (len(subs) == 1 and subs[0].get("name") == "отсутствует"):
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

# --- FSM STATES ---
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
    awaiting_confirm_restore = State()
    edit_subs_master = State()
    edit_subs_total = State()
    edit_sub_1_type = State()
    edit_sub_1_duration = State()
    edit_sub_1_start = State()
    edit_sub_2_type = State()
    edit_sub_2_duration = State()
    edit_sub_2_start = State()
    awaiting_db_confirm = State()

# --- КНОПКИ ---
def region_btns():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур")],
            [KeyboardButton(text="(польша)"), KeyboardButton(text="(британия)")],
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
            [KeyboardButton(text="📊 База")]
        ], resize_keyboard=True
    )

def base_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Заканчивается подписка (7д)"), KeyboardButton(text="Скоро ДР (7д)")],
            [KeyboardButton(text="Без подписки"), KeyboardButton(text="Выгрузить всю базу в чат")],
            [KeyboardButton(text="Сделать бэкап базы"), KeyboardButton(text="Восстановить из бэкапа")],
            [KeyboardButton(text="Очистить базу"), KeyboardButton(text="❌ Отмена")]
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
    for sub in subs:
        if sub.get("name") != "отсутствует":
            lines.append(f"\n<b>🗓 {sub.get('name', '')} {sub.get('duration', '')}</b>")
            lines.append(f"📅 {sub.get('start', '')} → {sub.get('end', '')}")
    if subs and subs[0].get("name") == "отсутствует":
        lines.append(f"\n<b>Подписка:</b> отсутствует")
    region = client.get("region", "—")
    lines.append(f"\n🌍 Регион: {region}")
    games = client.get("games", [])
    if games:
        lines.append("\n🎮 Игры:")
        for game in games:
            lines.append(f"• {game}")
    reserve_photo_id = client.get("reserve_photo_id")
    return "\n".join(lines), reserve_photo_id if show_photo_id else None

def stats_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Заканчивается подписка (7д)", callback_data="expiring_subs"),
            InlineKeyboardButton(text="Скоро ДР (7д)", callback_data="upcoming_birthdays"),
        ],
        [
            InlineKeyboardButton(text="Без подписки", callback_data="no_subscription"),
            InlineKeyboardButton(text="Выгрузить всю базу в чат", callback_data="dump_all"),
        ],
        [
            InlineKeyboardButton(text="Сделать бэкап базы", callback_data="do_backup"),
            InlineKeyboardButton(text="Восстановить из бэкапа", callback_data="restore_backup"),
        ],
        [
            InlineKeyboardButton(text="Очистить базу", callback_data="clear_db"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_base"),
        ]
    ])

# --- ЧИСТКА ЧАТА ---
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

# --- СТАРТ ---
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

# --- ДОБАВЛЕНИЕ: ИГРЫ, РЕЗЕРВНЫЕ КОДЫ, ФИНАЛ ---

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
    if message.photo:
        file_id = message.photo[-1].file_id
        await state.update_data(reserve_photo_id=file_id)
        await finish_client(message, state)
    else:
        await message.answer("Отправьте именно фото!")

async def finish_client(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = {
        "id": get_next_client_id(load_db()),
        "contact": data.get("contact", ""),
        "birth_date": data.get("birth_date", "отсутствует"),
        "account": data.get("account", {}),
        "region": data.get("region", ""),
        "console": data.get("console", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id", None),
    }
    save_new_client(client)
    await state.clear()
    await clear_chat(message)
    if client.get("reserve_photo_id"):
        await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
    else:
        await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))
    # Оставляем сообщение в чате (не удаляем через 5 минут, как просил!)

# --- ПОИСК КЛИЕНТА ---
@dp.message(F.text == "🔍 Найти клиента")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите запрос для поиска (номер, логин, игра и т.д.):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_choose)

@dp.message(AddEditClient.edit_choose)
async def search_choose(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    query = message.text.strip()
    clients = find_clients(query)
    if not clients:
        await message.answer("Клиентов не найдено.")
        await start_cmd(message, state)
        return
    await state.clear()
    await clear_chat(message)
    for client in clients:
        if client.get("reserve_photo_id"):
            await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
        else:
            await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))

# --- ИНЛАЙН-КНОПКИ РЕДАКТИРОВАНИЯ ---
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
        await callback.message.answer("Введите новый номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="contact")
        return
    if field == "birth":
        await callback.message.answer("Введите новую дату рождения (дд.мм.гггг) или 'отсутствует':", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="birth_date")
        return
    if field == "account":
        await callback.message.answer("Введи:\n1. Логин\n2. Пароль\n3. Почта-пароль (можно пропустить)\n\nКаждый пункт с новой строки.",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
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
        await callback.message.answer("Загрузите новое фото резерв-кодов:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_reserve)
        return
    if field == "sub":
        await callback.message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                [KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_subs_total)
        return
    if field == "games":
        await callback.message.answer("Введи список игр (каждая с новой строки):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_games)
        return

# --- РЕДАКТИРОВАНИЕ ПОЛЕЙ ---
@dp.message(AddEditClient.edit_input)
async def edit_input_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
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
            if c.get("reserve_photo_id"):
                await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
            else:
                await message.answer(format_card(c)[0], reply_markup=edit_keyboard(c))
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

@dp.message(AddEditClient.edit_games)
async def edit_games_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    data = await state.get_data()
    cid = data.get("edit_id")
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == cid:
            c["games"] = games
            clients[i] = c
            save_db(clients)
            await state.clear()
            await clear_chat(message)
            if c.get("reserve_photo_id"):
                await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
            else:
                await message.answer(format_card(c)[0], reply_markup=edit_keyboard(c))
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

@dp.message(AddEditClient.edit_reserve)
async def edit_reserve_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.photo:
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["reserve_photo_id"] = photo_id
                clients[i] = c
                save_db(clients)
                await state.clear()
                await clear_chat(message)
                await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
                return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

# --- МАСТЕР РЕДАКТИРОВАНИЯ ПОДПИСКИ (аналогично добавлению) ---

@dp.message(AddEditClient.edit_subs_total)
async def edit_subs_total(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["subscriptions"] = [{"name": "отсутствует"}]
                clients[i] = c
                save_db(clients)
                await state.clear()
                await clear_chat(message)
                if c.get("reserve_photo_id"):
                    await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
                else:
                    await message.answer(format_card(c)[0], reply_markup=edit_keyboard(c))
                return
        await message.answer("Ошибка при обновлении.")
        await state.clear()
        return
    if message.text not in ("Одна", "Две"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(edit_subs_total=1 if message.text == "Одна" else 2)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
            [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
    await message.answer("Выберите тип подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_type)

@dp.message(AddEditClient.edit_sub_1_type)
async def edit_sub_1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(edit_sub_1_type=message.text)
    kb = None
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_duration)

@dp.message(AddEditClient.edit_sub_1_duration)
async def edit_sub_1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    sub_1_type = data.get("edit_sub_1_type")
    if (sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_1_start)

@dp.message(AddEditClient.edit_sub_1_start)
async def edit_sub_1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_1_duration")
    months = int(duration.replace("м", ""))
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months*30)
    sub = {
        "name": data.get("edit_sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end.strftime("%d.%m.%Y")
    }
    await state.update_data(edit_sub_1=sub)
    subs_total = data.get("edit_subs_total", 1)
    if subs_total == 2:
        prev = data.get("edit_sub_1_type")
        if prev == "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
        await state.set_state(AddEditClient.edit_sub_2_type)
    else:
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        idx = next((i for i, c in enumerate(clients) if c["id"] == cid), None)
        clients[idx]["subscriptions"] = [sub]
        save_db(clients)
        await state.clear()
        await clear_chat(message)
        if clients[idx].get("reserve_photo_id"):
            await message.answer_photo(clients[idx]["reserve_photo_id"], caption=format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
        else:
            await message.answer(format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
        return

@dp.message(AddEditClient.edit_sub_2_type)
async def edit_sub_2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    prev = data.get("edit_sub_1_type")
    if prev == "EA Play":
        if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
            await message.answer("Выберите PS Plus!")
            return
    else:
        if message.text != "EA Play":
            await message.answer("Выберите EA Play!")
            return
    await state.update_data(edit_sub_2_type=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_2_duration)

@dp.message(AddEditClient.edit_sub_2_duration)
async def edit_sub_2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    sub_2_type = data.get("edit_sub_2_type")
    if (sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_2_start)

@dp.message(AddEditClient.edit_sub_2_start)
async def edit_sub_2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_2_duration")
    months = int(duration.replace("м", ""))
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months*30)
    sub1 = data.get("edit_sub_1")
    sub2 = {
        "name": data.get("edit_sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end.strftime("%d.%m.%Y")
    }
    subs = [sub1, sub2]
    cid = data.get("edit_id")
    clients = load_db()
    idx = next((i for i, c in enumerate(clients) if c["id"] == cid), None)
    clients[idx]["subscriptions"] = subs
    save_db(clients)
    await state.clear()
    await clear_chat(message)
    if clients[idx].get("reserve_photo_id"):
        await message.answer_photo(clients[idx]["reserve_photo_id"], caption=format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
    else:
        await message.answer(format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
    return

# --- СОХРАНИТЬ ---

@dp.callback_query(F.data.startswith("save_"))
async def save_client(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await clear_chat(callback.message)
    await callback.message.answer("Изменения сохранены! Возврат в главное меню.", reply_markup=main_menu())

# --- ГЛАВНОЕ МЕНЮ "БАЗА" ---
@dp.message(F.text.in_({"База", "база"}))
async def db_menu(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Заканчивается подписка (7д)"), KeyboardButton(text="Скоро ДР")],
            [KeyboardButton(text="Без подписки"), KeyboardButton(text="Выгрузить всю базу в чат")],
            [KeyboardButton(text="Выгрузить базу в файл"), KeyboardButton(text="Сделать бэкап базы")],
            [KeyboardButton(text="Восстановить из бэкапа"), KeyboardButton(text="Очистить базу")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await state.clear()
    await clear_chat(message)
    await message.answer("Раздел «База» — выберите действие:", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm)

# --- ВЫГРУЗИТЬ ВСЮ БАЗУ В ЧАТ ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Выгрузить всю базу в чат")
async def db_dump_chat(message: types.Message, state: FSMContext):
    clients = load_db()
    if not clients:
        await message.answer("База пуста!")
    else:
        for client in clients:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
    await db_menu(message, state)

# --- ВЫГРУЗИТЬ БАЗУ В ФАЙЛ ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Выгрузить базу в файл")
async def db_dump_file(message: types.Message, state: FSMContext):
    clients = load_db()
    tmp_path = f"clients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    await bot.send_document(message.chat.id, InputFile(tmp_path))
    os.remove(tmp_path)
    await db_menu(message, state)

# --- СДЕЛАТЬ БЭКАП ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Сделать бэкап базы")
async def make_backup(message: types.Message, state: FSMContext):
    clients = load_db()
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    fname = f"{backup_dir}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    await message.answer(f"Бэкап сохранён: {fname.split('/')[-1]}")
    await db_menu(message, state)

# --- ВОССТАНОВИТЬ ИЗ БЭКАПА ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Восстановить из бэкапа")
async def choose_backup(message: types.Message, state: FSMContext):
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        await message.answer("Нет сохранённых бэкапов.")
        await db_menu(message, state)
        return
    files = sorted([f for f in os.listdir(backup_dir) if f.endswith(".json")])
    if not files:
        await message.answer("Нет сохранённых бэкапов.")
        await db_menu(message, state)
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=fn)] for fn in files] + [[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    await message.answer("Выберите бэкап для восстановления:", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm_restore)

@dp.message(AddEditClient.awaiting_confirm_restore)
async def restore_backup(message: types.Message, state: FSMContext):
    fname = message.text.strip()
    if fname == "❌ Отмена":
        await db_menu(message, state)
        return
    backup_path = f"backups/{fname}"
    if not os.path.exists(backup_path):
        await message.answer("Бэкап не найден.")
        await db_menu(message, state)
        return
    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    save_db(data)
    await message.answer("База восстановлена из бэкапа.")
    await db_menu(message, state)

# --- ОЧИСТИТЬ БАЗУ ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Очистить базу")
async def ask_clear_db(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да, удалить всё"), KeyboardButton(text="Нет, отмена")],
        ], resize_keyboard=True
    )
    await message.answer("Вы уверены, что хотите удалить ВСЮ базу клиентов?", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm_clear)

@dp.message(AddEditClient.awaiting_confirm_clear)
async def clear_db_confirm(message: types.Message, state: FSMContext):
    if message.text == "Да, удалить всё":
        save_db([])
        await message.answer("База удалена полностью.")
    else:
        await message.answer("Действие отменено.")
    await db_menu(message, state)

# --- КЛИЕНТЫ БЕЗ ПОДПИСКИ ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Без подписки")
async def dump_no_subs(message: types.Message, state: FSMContext):
    clients = load_db()
    found = []
    for c in clients:
        if not c.get("subscriptions") or (c.get("subscriptions")[0] and c["subscriptions"][0].get("name") == "отсутствует"):
            found.append(c)
    if not found:
        await message.answer("Нет клиентов без подписки!")
    else:
        for client in found:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
    await db_menu(message, state)

# --- КЛИЕНТЫ С ПОДПИСКОЙ ЗАКАНЧИВАЮТСЯ 7 ДНЕЙ ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Заканчивается подписка (7д)")
async def dump_expiring_subs(message: types.Message, state: FSMContext):
    clients = load_db()
    now = datetime.now()
    week = timedelta(days=7)
    found = []
    for c in clients:
        for sub in c.get("subscriptions", []):
            try:
                end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                if 0 <= (end - now).days <= 7:
                    found.append(c)
                    break
            except: continue
    if not found:
        await message.answer("Нет клиентов с истекающей подпиской в течение 7 дней!")
    else:
        for client in found:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
    await db_menu(message, state)

# --- КЛИЕНТЫ С ДР В ТЕЧЕНИЕ 7 ДНЕЙ ---
@dp.message(AddEditClient.awaiting_confirm, F.text == "Скоро ДР")
async def dump_soon_birthdays(message: types.Message, state: FSMContext):
    clients = load_db()
    now = datetime.now()
    week = timedelta(days=7)
    found = []
    for c in clients:
        bdate = c.get("birth_date", "отсутствует")
        if bdate and bdate != "отсутствует":
            try:
                bd = datetime.strptime(bdate, "%d.%m.%Y").replace(year=now.year)
                days_to_bd = (bd - now).days
                if 0 <= days_to_bd <= 7:
                    found.append(c)
            except: continue
    if not found:
        await message.answer("Нет клиентов, у которых день рождения в течение 7 дней!")
    else:
        for client in found:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
    await db_menu(message, state)

# --- СТАТИСТИКА ---
@dp.message(F.text.in_({"Статистика", "статистика"}))
async def stat_menu(message: types.Message, state: FSMContext):
    clients = load_db()
    total = len(clients)
    with_subs = 0
    two_subs = 0
    deluxe = extra = essential = ea = 0
    no_sub = 0
    games_count = 0
    regions = {"укр": 0, "тур": 0, "(польша)": 0, "(британия)": 0, "другой": 0}
    expiring = 0
    soon_bd = 0
    now = datetime.now()
    for c in clients:
        if c.get("games"):
            games_count += len(c["games"])
        reg = c.get("region", "другой")
        if reg in regions:
            regions[reg] += 1
        else:
            regions["другой"] += 1
        subs = c.get("subscriptions", [])
        if not subs or (subs[0].get("name") == "отсутствует"):
            no_sub += 1
        else:
            with_subs += 1
            if len(subs) == 2:
                two_subs += 1
            for sub in subs:
                n = sub.get("name")
                if n == "PS Plus Deluxe":
                    deluxe += 1
                elif n == "PS Plus Extra":
                    extra += 1
                elif n == "PS Plus Essential":
                    essential += 1
                elif n == "EA Play":
                    ea += 1
                try:
                    end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                    if 0 <= (end - now).days <= 7:
                        expiring += 1
                except: pass
        bdate = c.get("birth_date", "отсутствует")
        if bdate and bdate != "отсутствует":
            try:
                bd = datetime.strptime(bdate, "%d.%m.%Y").replace(year=now.year)
                if 0 <= (bd - now).days <= 7:
                    soon_bd += 1
            except: pass
    stat_text = (
        f"<b>Статистика CRM</b>\n\n"
        f"👤 Клиентов: {total}\n"
        f"✉️ Без подписки: {no_sub}\n"
        f"💳 С подписками: {with_subs}\n"
        f"— PS Plus Deluxe: {deluxe}\n"
        f"— PS Plus Extra: {extra}\n"
        f"— PS Plus Essential: {essential}\n"
        f"— EA Play: {ea}\n"
        f"🔁 Две подписки: {two_subs}\n\n"
        f"🌍 Регионы:\n"
        f"укр: {regions['укр']}\n"
        f"тур: {regions['тур']}\n"
        f"(польша): {regions['(польша)']}\n"
        f"(британия): {regions['(британия)']}\n"
        f"другой: {regions['другой']}\n\n"
        f"🎮 Оформлено игр: {games_count}\n"
        f"⏳ Подписки истекают (7 дней): {expiring}\n"
        f"🎂 День рождения скоро: {soon_bd}\n"
    )
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Заканчивается подписка (7д)"), KeyboardButton(text="Скоро ДР")],
            [KeyboardButton(text="Без подписки"), KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await state.clear()
    await clear_chat(message)
    await message.answer(stat_text, reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm)

# --- ОТМЕНА В ЛЮБОМ МЕСТЕ ---
@dp.message(F.text == "❌ Отмена")
async def cancel_anywhere(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await start_cmd(message, state)

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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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

# --- ДОБАВЛЕНИЕ: ИГРЫ, РЕЗЕРВНЫЕ КОДЫ, ФИНАЛ ---

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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
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
        await cancel_anywhere(message, state)
        return
    if message.photo:
        file_id = message.photo[-1].file_id
        await state.update_data(reserve_photo_id=file_id)
        await finish_client(message, state)
    else:
        await message.answer("Отправьте именно фото!")

async def finish_client(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = {
        "id": get_next_client_id(load_db()),
        "contact": data.get("contact", ""),
        "birth_date": data.get("birth_date", "отсутствует"),
        "account": data.get("account", {}),
        "region": data.get("region", ""),
        "console": data.get("console", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id", None),
    }
    save_new_client(client)
    await state.clear()
    await clear_chat(message)
    if client.get("reserve_photo_id"):
        await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
    else:
        await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))

# --- ПОИСК КЛИЕНТА ---
@dp.message(F.text == "🔍 Найти клиента")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите запрос для поиска (номер, логин, игра и т.д.):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_choose)

@dp.message(AddEditClient.edit_choose)
async def search_choose(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    query = message.text.strip()
    clients = find_clients(query)
    if not clients:
        await message.answer("Клиентов не найдено.")
        await start_cmd(message, state)
        return
    await state.clear()
    await clear_chat(message)
    for client in clients:
        if client.get("reserve_photo_id"):
            await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
        else:
            await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))

# --- ИНЛАЙН-КНОПКИ РЕДАКТИРОВАНИЯ ---
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
        await callback.message.answer("Введите новый номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="contact")
        return
    if field == "birth":
        await callback.message.answer("Введите новую дату рождения (дд.мм.гггг) или 'отсутствует':", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="birth_date")
        return
    if field == "account":
        await callback.message.answer("Введи:\n1. Логин\n2. Пароль\n3. Почта-пароль (можно пропустить)\n\nКаждый пункт с новой строки.",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
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
        await callback.message.answer("Загрузите новое фото резерв-кодов:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_reserve)
        return
    if field == "sub":
        await callback.message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                [KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_subs_total)
        return
    if field == "games":
        await callback.message.answer("Введи список игр (каждая с новой строки):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_games)
        return

# --- РЕДАКТИРОВАНИЕ ПОЛЕЙ ---
@dp.message(AddEditClient.edit_input)
async def edit_input_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    data = await state.get_data()
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
            if c.get("reserve_photo_id"):
                await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
            else:
                await message.answer(format_card(c)[0], reply_markup=edit_keyboard(c))
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

@dp.message(AddEditClient.edit_games)
async def edit_games_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    data = await state.get_data()
    cid = data.get("edit_id")
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == cid:
            c["games"] = games
            clients[i] = c
            save_db(clients)
            await state.clear()
            await clear_chat(message)
            if c.get("reserve_photo_id"):
                await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
            else:
                await message.answer(format_card(c)[0], reply_markup=edit_keyboard(c))
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

@dp.message(AddEditClient.edit_reserve)
async def edit_reserve_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    if message.photo:
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["reserve_photo_id"] = photo_id
                clients[i] = c
                save_db(clients)
                await state.clear()
                await clear_chat(message)
                await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
                return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

# --- МАСТЕР ПОДПИСКИ (редактирование подписок) ---
@dp.message(AddEditClient.edit_subs_total)
async def edit_subs_total(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["subscriptions"] = [{"name": "отсутствует"}]
                clients[i] = c
                save_db(clients)
                await state.clear()
                await clear_chat(message)
                if c.get("reserve_photo_id"):
                    await message.answer_photo(c["reserve_photo_id"], caption=format_card(c)[0], reply_markup=edit_keyboard(c))
                else:
                    await message.answer(format_card(c)[0], reply_markup=edit_keyboard(c))
                return
        await message.answer("Ошибка при обновлении.")
        await state.clear()
        return
    if message.text not in ("Одна", "Две"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(edit_subs_total=1 if message.text == "Одна" else 2)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
            [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
    await message.answer("Выберите тип подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_type)

@dp.message(AddEditClient.edit_sub_1_type)
async def edit_sub_1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(edit_sub_1_type=message.text)
    kb = None
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_duration)

@dp.message(AddEditClient.edit_sub_1_duration)
async def edit_sub_1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    data = await state.get_data()
    sub_1_type = data.get("edit_sub_1_type")
    if (sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_1_start)

@dp.message(AddEditClient.edit_sub_1_start)
async def edit_sub_1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_1_duration")
    months = int(duration.replace("м", ""))
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months*30)
    sub = {
        "name": data.get("edit_sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end.strftime("%d.%m.%Y")
    }
    await state.update_data(edit_sub_1=sub)
    subs_total = data.get("edit_subs_total", 1)
    if subs_total == 2:
        prev = data.get("edit_sub_1_type")
        if prev == "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
        await state.set_state(AddEditClient.edit_sub_2_type)
    else:
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        idx = next((i for i, c in enumerate(clients) if c["id"] == cid), None)
        clients[idx]["subscriptions"] = [sub]
        save_db(clients)
        await state.clear()
        await clear_chat(message)
        if clients[idx].get("reserve_photo_id"):
            await message.answer_photo(clients[idx]["reserve_photo_id"], caption=format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
        else:
            await message.answer(format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
        return

@dp.message(AddEditClient.edit_sub_2_type)
async def edit_sub_2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    data = await state.get_data()
    prev = data.get("edit_sub_1_type")
    if prev == "EA Play":
        if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
            await message.answer("Выберите PS Plus!")
            return
    else:
        if message.text != "EA Play":
            await message.answer("Выберите EA Play!")
            return
    await state.update_data(edit_sub_2_type=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_2_duration)

@dp.message(AddEditClient.edit_sub_2_duration)
async def edit_sub_2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    data = await state.get_data()
    sub_2_type = data.get("edit_sub_2_type")
    if (sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_2_start)

@dp.message(AddEditClient.edit_sub_2_start)
async def edit_sub_2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_2_duration")
    months = int(duration.replace("м", ""))
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months*30)
    sub1 = data.get("edit_sub_1")
    sub2 = {
        "name": data.get("edit_sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end.strftime("%d.%m.%Y")
    }
    subs = [sub1, sub2]
    cid = data.get("edit_id")
    clients = load_db()
    idx = next((i for i, c in enumerate(clients) if c["id"] == cid), None)
    clients[idx]["subscriptions"] = subs
    save_db(clients)
    await state.clear()
    await clear_chat(message)
    if clients[idx].get("reserve_photo_id"):
        await message.answer_photo(clients[idx]["reserve_photo_id"], caption=format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
    else:
        await message.answer(format_card(clients[idx])[0], reply_markup=edit_keyboard(clients[idx]))
    return

# --- СОХРАНИТЬ ---
@dp.callback_query(F.data.startswith("save_"))
async def save_client(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await clear_chat(callback.message)
    await callback.message.answer("Изменения сохранены! Возврат в главное меню.", reply_markup=main_menu())

# --- ФУНКЦИЯ ОТМЕНЫ ---
async def cancel_anywhere(message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await start_cmd(message, state)

# --- РАЗДЕЛ "БАЗА", СТАТИСТИКА, БЭКАПЫ, ОЧИСТКА ---

from glob import glob

def get_backups():
    return sorted(glob("clients_db_*.json"), reverse=True)

@dp.message(F.text.in_({"База", "база"}))
async def base_menu(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Заканчивается подписка (7д)"),
                KeyboardButton(text="Скоро ДР (7д)")
            ],
            [
                KeyboardButton(text="Без подписки"),
                KeyboardButton(text="Выгрузить всю базу в чат")
            ],
            [
                KeyboardButton(text="Сделать бэкап базы"),
                KeyboardButton(text="Восстановить из бэкапа")
            ],
            [
                KeyboardButton(text="Очистить базу"),
                KeyboardButton(text="❌ Отмена")
            ]
        ],
        resize_keyboard=True
    )
    stat_text = make_statistics()
    await message.answer(stat_text, reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm)

def make_statistics():
    clients = load_db()
    n_clients = len(clients)
    n_no_subs = sum(1 for c in clients if not c.get("subscriptions") or c["subscriptions"][0].get("name") == "отсутствует")
    n_with_subs = n_clients - n_no_subs

    subs_types = {
        "PS Plus Deluxe": 0,
        "PS Plus Extra": 0,
        "PS Plus Essential": 0,
        "EA Play": 0
    }
    two_subs = 0
    for c in clients:
        subs = c.get("subscriptions", [])
        if len(subs) > 1:
            two_subs += 1
        for sub in subs:
            if sub.get("name") in subs_types:
                subs_types[sub["name"]] += 1

    region_map = {"укр": 0, "тур": 0, "(польша)": 0, "(британия)": 0, "другой": 0}
    for c in clients:
        reg = c.get("region", "").lower()
        if reg in region_map:
            region_map[reg] += 1
        else:
            region_map["другой"] += 1

    n_games = sum(1 for c in clients if c.get("games"))

    # подписки кончаются в 7 дней
    soon_subs = 0
    now = datetime.now()
    for c in clients:
        for sub in c.get("subscriptions", []):
            try:
                end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                if 0 <= (end - now).days <= 7:
                    soon_subs += 1
            except: continue

    # ДР в 7 дней
    soon_bd = 0
    for c in clients:
        bdate = c.get("birth_date")
        if bdate and bdate != "отсутствует":
            try:
                bd = datetime.strptime(bdate, "%d.%m.%Y")
                bd_this_year = bd.replace(year=now.year)
                days = (bd_this_year - now).days
                if 0 <= days <= 7:
                    soon_bd += 1
            except: continue

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
    return txt

@dp.message(AddEditClient.awaiting_confirm)
async def base_buttons(message: types.Message, state: FSMContext):
    text = message.text
    if text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return

    if text == "Выгрузить всю базу в чат":
        clients = load_db()
        if not clients:
            await message.answer("База пуста!")
            return
        for client in clients:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
        return

    if text == "Сделать бэкап базы":
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        clients = load_db()
        fname = f"clients_db_{now_str}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(clients, f, ensure_ascii=False, indent=2)
        await message.answer(f"Бэкап сохранён: {fname}")
        return

    if text == "Восстановить из бэкапа":
        backups = get_backups()
        if not backups:
            await message.answer("Нет сохранённых бэкапов.")
            return
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=os.path.basename(bf))] for bf in backups] + [[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
        await message.answer("Выберите бэкап для восстановления:", reply_markup=kb)
        await state.set_state(AddEditClient.awaiting_confirm_restore)
        return

    if text == "Очистить базу":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
            ], resize_keyboard=True
        )
        await message.answer("Вы уверены, что хотите удалить всю базу?", reply_markup=kb)
        await state.set_state(AddEditClient.awaiting_confirm_delete)
        return

    if text == "Без подписки":
        clients = load_db()
        filtered = [c for c in clients if not c.get("subscriptions") or c["subscriptions"][0].get("name") == "отсутствует"]
        if not filtered:
            await message.answer("Нет клиентов без подписки.")
            return
        for client in filtered:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
        return

    if text == "Заканчивается подписка (7д)":
        clients = load_db()
        now = datetime.now()
        res = []
        for c in clients:
            for sub in c.get("subscriptions", []):
                try:
                    end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                    if 0 <= (end - now).days <= 7:
                        res.append(c)
                except: continue
        if not res:
            await message.answer("Нет клиентов с истекающей подпиской в течение 7 дней.")
            return
        for client in res:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
        return

    if text == "Скоро ДР (7д)":
        clients = load_db()
        now = datetime.now()
        res = []
        for c in clients:
            bdate = c.get("birth_date")
            if bdate and bdate != "отсутствует":
                try:
                    bd = datetime.strptime(bdate, "%d.%m.%Y")
                    bd_this_year = bd.replace(year=now.year)
                    days = (bd_this_year - now).days
                    if 0 <= days <= 7:
                        res.append(c)
                except: continue
        if not res:
            await message.answer("Нет клиентов с ДР в течение 7 дней.")
            return
        for client in res:
            if client.get("reserve_photo_id"):
                await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0])
            else:
                await message.answer(format_card(client)[0])
        return

@dp.message(AddEditClient.awaiting_confirm_delete)
async def confirm_delete(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена" or message.text == "Нет":
        await cancel_anywhere(message, state)
        return
    if message.text == "Да":
        save_db([])
        await message.answer("База удалена.")
        await start_cmd(message, state)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.awaiting_confirm_restore)
async def confirm_restore(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_anywhere(message, state)
        return
    fname = message.text
    if not os.path.exists(fname):
        await message.answer("Такого файла не найдено.")
        await start_cmd(message, state)
        return
    with open(fname, "r", encoding="utf-8") as f:
        try:
            clients = json.load(f)
            save_db(clients)
            await message.answer("Восстановление завершено.")
        except:
            await message.answer("Ошибка восстановления из бэкапа.")
    await start_cmd(message, state)

# --- НАПОМИНАНИЯ О КОНЦЕ ПОДПИСКИ И ДНЯХ РОЖДЕНИЯ ---

async def notify_soon_subs_and_bd():
    clients = load_db()
    now = datetime.now()
    soon_subs = []
    soon_bd = []
    for c in clients:
        # подписки за день до конца
        for sub in c.get("subscriptions", []):
            try:
                end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                if (end - now).days == 1:
                    soon_subs.append((c, sub))
            except:
                continue
        # ДР сегодня
        bdate = c.get("birth_date")
        if bdate and bdate != "отсутствует":
            try:
                bd = datetime.strptime(bdate, "%d.%m.%Y")
                bd_this_year = bd.replace(year=now.year)
                if (bd_this_year - now).days == 0:
                    soon_bd.append(c)
            except:
                continue

    if soon_subs:
        for c, sub in soon_subs:
            txt, _ = format_card(c)
            await bot.send_message(
                ADMIN_ID, f"⚠️ <b>Завтра истекает подписка:</b>\n{sub['name']} ({sub['end']})\n\n{txt}",
                reply_markup=edit_keyboard(c)
            )
    if soon_bd:
        for c in soon_bd:
            txt, _ = format_card(c)
            await bot.send_message(
                ADMIN_ID, f"🎉 <b>Сегодня день рождения у клиента:</b>\n\n{txt}",
                reply_markup=edit_keyboard(c)
            )

# --- АВТОМАТИЧЕСКИЙ БЭКАП (раз в сутки) ---
def auto_backup():
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    clients = load_db()
    fname = f"clients_db_{now_str}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def start_scheduler():
    scheduler.add_job(notify_soon_subs_and_bd, "cron", hour=9, minute=0)  # 9:00 по серверу
    scheduler.add_job(auto_backup, "cron", hour=3, minute=0)  # каждый день 3:00

# --- ГЛОБАЛЬНАЯ ОТМЕНА НА ЛЮБОЙ КНОПКЕ "ОТМЕНА" ---
async def cancel_anywhere(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await start_cmd(message, state)

# --- ЗАПУСК БОТА ---
async def main():
    start_scheduler()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
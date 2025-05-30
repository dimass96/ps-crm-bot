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
import shutil
import glob

DB_FILE = "clients_db.json"
KEY_FILE = "secret.key"
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

async def clear_chat(message: types.Message):
    try:
        chat = message.chat.id
        async for msg in message.bot.get_chat_history(chat, limit=100):
            try:
                await message.bot.delete_message(chat, msg.message_id)
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

# -------- (следующий большой блок: продолжение FSM добавления клиента, мастер подписки, игры, резервные коды, сохранение) --------

@dp.message(F.text == "🔍 Найти клиента")
async def find_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите любой поисковый запрос (номер/TG, имя, регион, логин, игра и т.д.):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_input)

@dp.message(AddEditClient.edit_input)
async def do_find(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    # Только поиск — НЕ обработка редактирования!
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
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
            else:
                await message.answer(text, reply_markup=edit_keyboard(c))
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
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
            else:
                await message.answer(text, reply_markup=edit_keyboard(c))
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
    if not message.photo:
        await message.answer("Отправьте фото!")
        return
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
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
            else:
                await message.answer(text, reply_markup=edit_keyboard(c))
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

# --- МАСТЕР РЕДАКТИРОВАНИЯ ПОДПИСКИ ---

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
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    await message.answer(text, reply_markup=edit_keyboard(c))
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
        text, photo_id = format_card(clients[idx], show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(clients[idx]))
        else:
            await message.answer(text, reply_markup=edit_keyboard(clients[idx]))
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
    kb = None
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
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
    text, photo_id = format_card(clients[idx], show_photo_id=True)
    if photo_id:
        await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(clients[idx]))
    else:
        await message.answer(text, reply_markup=edit_keyboard(clients[idx]))
    return

# --- СОХРАНИТЬ ИЗМЕНЕНИЯ ---

@dp.callback_query(F.data.startswith("save_"))
async def save_client(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await clear_chat(callback.message)
    await callback.message.answer("Изменения сохранены! Возврат в главное меню.", reply_markup=main_menu())

# --- КНОПКИ РАЗДЕЛА "БАЗА", СТАТИСТИКА, ВЫГРУЗКА, ОЧИСТКА, БЭКАПЫ, ВОССТАНОВЛЕНИЕ ---

def db_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Заканчивается подписка (7д)"), KeyboardButton(text="Скоро ДР (7д)")],
            [KeyboardButton(text="Без подписки"), KeyboardButton(text="Выгрузить всю базу в чат")],
            [KeyboardButton(text="Выгрузить всю базу в файл"), KeyboardButton(text="Сделать бэкап базы")],
            [KeyboardButton(text="Восстановить из бэкапа"), KeyboardButton(text="Очистить базу")],
            [KeyboardButton(text="Статистика"), KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

@dp.message(F.text.in_({"Выгрузить базу", "База", "база"}))
async def db_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("<b>Меню базы</b>\nВыберите действие:", reply_markup=db_menu_keyboard())

@dp.message(F.text == "Статистика")
async def db_stats(message: types.Message, state: FSMContext):
    clients = load_db()
    stats = {
        "total": len(clients),
        "no_sub": 0,
        "with_sub": 0,
        "deluxe": 0, "extra": 0, "essential": 0, "ea": 0, "double": 0,
        "regions": {"укр": 0, "тур": 0, "(польша)": 0, "(британия)": 0, "другой": 0},
        "games": 0,
        "expire_7d": 0,
        "birthday_7d": 0,
    }
    from datetime import date
    now = datetime.now()
    for c in clients:
        # Подписки
        subs = c.get("subscriptions", [])
        if not subs or (len(subs) == 1 and subs[0].get("name") == "отсутствует"):
            stats["no_sub"] += 1
        else:
            stats["with_sub"] += 1
            names = [sub.get("name", "") for sub in subs]
            for n in names:
                if n == "PS Plus Deluxe":
                    stats["deluxe"] += 1
                if n == "PS Plus Extra":
                    stats["extra"] += 1
                if n == "PS Plus Essential":
                    stats["essential"] += 1
                if n == "EA Play":
                    stats["ea"] += 1
            if len(subs) == 2:
                stats["double"] += 1
        # Регионы
        reg = str(c.get("region", "")).lower()
        for key in stats["regions"]:
            if reg == key:
                stats["regions"][key] += 1
        # Игры
        games = c.get("games", [])
        if games:
            stats["games"] += len(games)
        # Подписки истекают (7д)
        for sub in subs:
            try:
                end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                if 0 <= (end - now).days <= 7:
                    stats["expire_7d"] += 1
                    break
            except: continue
        # ДР (7д)
        bdate = c.get("birth_date", "")
        try:
            bd = datetime.strptime(bdate, "%d.%m.%Y").replace(year=now.year)
            if 0 <= (bd - now).days <= 7:
                stats["birthday_7d"] += 1
        except: continue

    stats_text = "<b>Статистика CRM</b>\n\n"
    stats_text += f"👤 Клиентов: {stats['total']}\n"
    stats_text += f"✉️ Без подписки: {stats['no_sub']}\n"
    stats_text += f"💳 С подписками: {stats['with_sub']}\n"
    stats_text += f"— PS Plus Deluxe: {stats['deluxe']}\n"
    stats_text += f"— PS Plus Extra: {stats['extra']}\n"
    stats_text += f"— PS Plus Essential: {stats['essential']}\n"
    stats_text += f"— EA Play: {stats['ea']}\n"
    stats_text += f"🔁 Две подписки: {stats['double']}\n\n"
    stats_text += "🌍 Регионы:\n"
    for k in ("укр", "тур", "(польша)", "(британия)", "другой"):
        stats_text += f"{k}: {stats['regions'][k]}\n"
    stats_text += f"\n🎮 Оформлено игр: {stats['games']}\n"
    stats_text += f"⏳ Подписки истекают (7 дней): {stats['expire_7d']}\n"
    stats_text += f"🎂 День рождения скоро: {stats['birthday_7d']}\n"

    # Контекстные кнопки статистики
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Заканчивается подписка (7д)"), KeyboardButton(text="Скоро ДР (7д)")],
            [KeyboardButton(text="Без подписки"), KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
    await message.answer(stats_text, reply_markup=kb)

@dp.message(F.text == "Без подписки")
async def clients_no_sub(message: types.Message, state: FSMContext):
    clients = load_db()
    found = False
    for c in clients:
        subs = c.get("subscriptions", [])
        if not subs or (len(subs) == 1 and subs[0].get("name") == "отсутствует"):
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                await message.answer_photo(photo_id, caption=text)
            else:
                await message.answer(text)
            found = True
    if not found:
        await message.answer("Нет клиентов без подписки.", reply_markup=db_menu_keyboard())
    else:
        await message.answer("Готово.", reply_markup=db_menu_keyboard())

@dp.message(F.text == "Заканчивается подписка (7д)")
async def clients_expire_7d(message: types.Message, state: FSMContext):
    clients = load_db()
    now = datetime.now()
    out = []
    for c in clients:
        subs = c.get("subscriptions", [])
        for sub in subs:
            try:
                end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                if 0 <= (end - now).days <= 7:
                    out.append(c)
                    break
            except: continue
    if not out:
        await message.answer("Нет клиентов с истекающей подпиской в течение 7 дней.", reply_markup=db_menu_keyboard())
    else:
        for c in out:
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                await message.answer_photo(photo_id, caption=text)
            else:
                await message.answer(text)
        await message.answer("Готово.", reply_markup=db_menu_keyboard())

@dp.message(F.text == "Скоро ДР (7д)")
async def clients_birthday_7d(message: types.Message, state: FSMContext):
    clients = load_db()
    now = datetime.now()
    out = []
    for c in clients:
        bdate = c.get("birth_date", "")
        try:
            bd = datetime.strptime(bdate, "%d.%m.%Y").replace(year=now.year)
            if 0 <= (bd - now).days <= 7:
                out.append(c)
        except: continue
    if not out:
        await message.answer("Нет клиентов с ближайшими днями рождения.", reply_markup=db_menu_keyboard())
    else:
        for c in out:
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                await message.answer_photo(photo_id, caption=text)
            else:
                await message.answer(text)
        await message.answer("Готово.", reply_markup=db_menu_keyboard())

@dp.message(F.text == "Выгрузить всю базу в чат")
async def dump_db_chat(message: types.Message, state: FSMContext):
    clients = load_db()
    if not clients:
        await message.answer("База пуста!")
        return
    for c in clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)
    await message.answer("Выгрузка завершена.", reply_markup=db_menu_keyboard())

@dp.message(F.text == "Выгрузить всю базу в файл")
async def dump_db_file(message: types.Message, state: FSMContext):
    clients = load_db()
    tmp_path = "clients_export.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    await bot.send_document(message.chat.id, InputFile(tmp_path))
    os.remove(tmp_path)
    await message.answer("Выгрузка завершена.", reply_markup=db_menu_keyboard())

import shutil
import glob

@dp.message(F.text == "Сделать бэкап базы")
async def backup_db_handler(message: types.Message, state: FSMContext):
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"clients_db_{date_str}.json"
    shutil.copyfile(DB_FILE, backup_name)
    await message.answer(f"Бэкап сохранён как {backup_name}.", reply_markup=db_menu_keyboard())

@dp.message(F.text == "Восстановить из бэкапа")
async def restore_backup_select(message: types.Message, state: FSMContext):
    files = sorted(glob.glob("clients_db_*.json"), reverse=True)
    if not files:
        await message.answer("Нет доступных бэкапов.", reply_markup=db_menu_keyboard())
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f)] for f in files] + [[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    await message.answer("Выберите бэкап для восстановления:", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm)

@dp.message(AddEditClient.awaiting_confirm)
async def restore_or_clear_confirm(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await db_menu(message, state)
        return
    if message.text.startswith("clients_db_") and message.text.endswith(".json"):
        fname = message.text
        if not os.path.exists(fname):
            await message.answer("Файл не найден.")
            await db_menu(message, state)
            return
        shutil.copyfile(fname, DB_FILE)
        await message.answer(f"База восстановлена из {fname}.", reply_markup=db_menu_keyboard())
        await state.clear()
        return
    if message.text == "Да":
        save_db([])
        await message.answer("База очищена.", reply_markup=db_menu_keyboard())
        await state.clear()
        return
    if message.text == "Нет":
        await state.clear()
        await db_menu(message, state)
        return
    await message.answer("Выберите правильный пункт!")

@dp.message(F.text == "Очистить базу")
async def clear_db_ask(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True
    )
    await message.answer("Уверены, что хотите удалить ВСЮ базу?", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm)

# --- НАПОМИНАНИЯ О КОНЦЕ ПОДПИСКИ И ДНЯХ РОЖДЕНИЯ ---

async def notify_expiring_subs():
    clients = load_db()
    now = datetime.now()
    for c in clients:
        subs = c.get("subscriptions", [])
        for sub in subs:
            try:
                end = datetime.strptime(sub.get("end", ""), "%d.%m.%Y")
                if (end - now).days == 1:  # За день до окончания
                    text, photo_id = format_card(c, show_photo_id=True)
                    msg = f"❗️У клиента заканчивается подписка:\n\n{text}"
                    if photo_id:
                        await bot.send_photo(ADMIN_ID, photo_id, caption=msg)
                    else:
                        await bot.send_message(ADMIN_ID, msg)
            except: continue

async def notify_birthdays():
    clients = load_db()
    now = datetime.now()
    for c in clients:
        bdate = c.get("birth_date", "")
        try:
            bd = datetime.strptime(bdate, "%d.%m.%Y").replace(year=now.year)
            if bd.date() == now.date():
                text, photo_id = format_card(c, show_photo_id=True)
                msg = f"🎉 У клиента сегодня день рождения!\n\n{text}"
                if photo_id:
                    await bot.send_photo(ADMIN_ID, photo_id, caption=msg)
                else:
                    await bot.send_message(ADMIN_ID, msg)
        except: continue

# Планировщик задач (ежедневно в 9:00 уведомления)
@scheduler.scheduled_job("cron", hour=9, minute=0)
async def scheduled_notify():
    await notify_expiring_subs()
    await notify_birthdays()

# --- ГЛАВНОЕ МЕНЮ (перезапуск) ---
@dp.message(F.text == "❌ Отмена")
async def cancel_any(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Главное меню", reply_markup=main_menu())

# --- ЗАПУСК ПОЛЛИНГА ---
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
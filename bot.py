import asyncio
import os
import json
import shutil
import glob
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
        os.makedirs("/data/backups", exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"/data/backups/backup_{now_str}.json"
        shutil.copyfile(DB_FILE, backup_name)
        backups = sorted(glob.glob("/data/backups/backup_*.json"))
        if len(backups) > 5:
            os.remove(backups[0])
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
    edit_input = State()
    edit_games = State()
    edit_reserve = State()
    edit_subs_total = State()
    edit_sub_1_type = State()
    edit_sub_1_duration = State()
    edit_sub_1_start = State()
    edit_sub_2_type = State()
    edit_sub_2_duration = State()
    edit_sub_2_start = State()
    awaiting_confirm_clear = State()

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def yes_no_cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

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
            [
                KeyboardButton(text="📩 Выгрузить всю базу в чат"),
                KeyboardButton(text="🔄 Заканчивается подписка (7д)"),
            ],
            [
                KeyboardButton(text="🎉 Скоро ДР (7д)"),
                KeyboardButton(text="⚠️ Без подписки"),
            ],
            [
                KeyboardButton(text="⏯️ Сделать бэкап базы"),
                KeyboardButton(text="▶️ Восстановить из бэкапа"),
            ],
            [
                KeyboardButton(text="🗑️ Очистить базу"),
                KeyboardButton(text="❌ Назад"),
            ],
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
    if region and not (region.startswith("(") and region.endswith(")")) and region != "—":
        region = f"({region})"
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

async def clear_and_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Главное меню", reply_markup=main_menu())

def calculate_end_date(start_date_str: str, months: int) -> str:
    start = datetime.strptime(start_date_str, "%d.%m.%Y")
    try:
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        day = start.day
        end = start.replace(year=year, month=month, day=day)
    except:
        end = start + timedelta(days=months * 30)
    return end.strftime("%d.%m.%Y")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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

# --- Add Client Handlers ---
@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите номер телефона или Telegram (@username):", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.contact)

@dp.message(AddEditClient.contact)
async def step_contact(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    await state.update_data(contact=message.text.strip())
    await message.answer("Дата рождения есть?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Отсутствует")], [KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True))
    await state.set_state(AddEditClient.birthdate_yesno)

@dp.message(AddEditClient.birthdate_yesno)
async def step_birthdate_ask(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Отсутствует":
        await state.update_data(birth_date="отсутствует")
        await ask_account(message, state)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отсутствует")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.birthdate)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.birthdate)
async def step_birthdate(message: types.Message, state: FSMContext):
    if message.text == "Отсутствует":
        await state.update_data(birth_date="отсутствует")
        await ask_account(message, state)
        return
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    await state.update_data(birth_date=message.text.strip())
    await ask_account(message, state)

async def ask_account(message, state: FSMContext):
    await message.answer("Введи:\n1. Логин\n2. Пароль\n3. Почта-пароль (можно пропустить)\n\nКаждый пункт с новой строки.", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.account)

@dp.message(AddEditClient.account)
async def step_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
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
        await clear_and_main_menu(message, state)
        return
    if message.text not in ("(укр)", "(тур)", "(другой)", "(польша)", "(британия)"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(region=message.text)
    await message.answer("Какая консоль?", reply_markup=console_btns())
    await state.set_state(AddEditClient.console)

@dp.message(AddEditClient.console)
async def step_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text not in ("PS4", "PS5", "PS4/PS5"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(console=message.text)
    await message.answer("Есть подписки?", reply_markup=yes_no_cancel_kb())
    await state.set_state(AddEditClient.subscriptions_yesno)

@dp.message(AddEditClient.subscriptions_yesno)
async def step_subs_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await ask_games(message, state)
        return
    if message.text == "Да":
        await message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Одна"), KeyboardButton(text="Две")], [KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True))
        await state.set_state(AddEditClient.subscriptions_count)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.subscriptions_count)
async def step_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
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
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет подписки":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await ask_games(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(sub_1_type=message.text)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_1_duration)

@dp.message(AddEditClient.sub_1_duration)
async def sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    data = await state.get_data()
    sub_1_type = data.get("sub_1_type")
    if (sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.sub_1_start)

@dp.message(AddEditClient.sub_1_start)
async def sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("sub_1_duration")
    months = int(duration.replace("м", ""))
    end_str = calculate_end_date(message.text.strip(), months)
    sub = {
        "name": data.get("sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end_str
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
        await clear_and_main_menu(message, state)
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
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_2_duration)

@dp.message(AddEditClient.sub_2_duration)
async def sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    data = await state.get_data()
    sub_2_type = data.get("sub_2_type")
    if (sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.sub_2_start)

@dp.message(AddEditClient.sub_2_start)
async def sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("sub_2_duration")
    months = int(duration.replace("м", ""))
    end_str = calculate_end_date(message.text.strip(), months)
    sub = {
        "name": data.get("sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end_str
    }
    subs = [data.get("sub_1"), sub]
    await state.update_data(sub_2=sub, subscriptions=subs)
    await ask_games(message, state)

async def ask_games(message, state: FSMContext):
    await message.answer("Оформлены игры?", reply_markup=yes_no_cancel_kb())
    await state.set_state(AddEditClient.games_yesno)

@dp.message(AddEditClient.games_yesno)
async def games_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет":
        await state.update_data(games=[])
        await ask_reserve(message, state)
        return
    if message.text == "Да":
        await message.answer("Введи список игр (каждая с новой строки):", reply_markup=cancel_kb())
        await state.set_state(AddEditClient.games_input)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.games_input)
async def games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    await state.update_data(games=games)
    await ask_reserve(message, state)

async def ask_reserve(message, state: FSMContext):
    await message.answer("Есть ли резервные коды?", reply_markup=yes_no_cancel_kb())
    await state.set_state(AddEditClient.reserve_yesno)

@dp.message(AddEditClient.reserve_yesno)
async def reserve_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет":
        await state.update_data(reserve_photo_id=None)
        await finish_client(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот (фото):", reply_markup=cancel_kb())
        await state.set_state(AddEditClient.reserve_photo)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.reserve_photo)
async def reserve_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
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
    clients = load_db()
    clients.append(client)
    save_db(clients)
    await clear_and_main_menu(message, state)
    text, photo_id = format_card(client, show_photo_id=True)
    if photo_id:
        sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
    else:
        sent = await message.answer(text, reply_markup=edit_keyboard(client))
    scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))

# --- Search Client ---
@dp.message(F.text == "🔍 Найти клиента")
async def find_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите любой поисковый запрос (номер/TG, имя, регион, логин, игра и т.д.):", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.edit_input)

@dp.message(AddEditClient.edit_input)
async def edit_text_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return

    data = await state.get_data()
    edit_field = data.get("edit_field")
    cid = data.get("edit_id")
    if edit_field and cid:
        # Это редактирование поля клиента, обновляем данные
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                if edit_field == "contact":
                    c["contact"] = message.text.strip()
                elif edit_field == "birth_date":
                    c["birth_date"] = message.text.strip()
                elif edit_field == "account":
                    rows = message.text.strip().split("\n")
                    login = rows[0].strip() if len(rows) > 0 else ""
                    password = rows[1].strip() if len(rows) > 1 else ""
                    mail_pass = rows[2].strip() if len(rows) > 2 else ""
                    c["account"] = {"login": login, "password": password, "mail_pass": mail_pass}
                elif edit_field == "console":
                    c["console"] = message.text.strip()
                elif edit_field == "region":
                    c["region"] = message.text.strip()
                clients[i] = c
                save_db(clients)
                await clear_chat(message)
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    sent = await message.answer(text, reply_markup=edit_keyboard(c))
                scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
                await state.clear()
                return
        await message.answer("Ошибка при обновлении.")
        await clear_and_main_menu(message, state)
        return
    else:
        # Поиск клиентов
        results = find_clients(message.text.strip())
        if not results:
            await message.answer("Клиентов не найдено.")
            await clear_and_main_menu(message, state)
            return
        for client in results:
            text, photo_id = format_card(client, show_photo_id=True)
            if photo_id:
                sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
            else:
                sent = await message.answer(text, reply_markup=edit_keyboard(client))
            scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))

# --- Inline buttons edit handlers ---
@dp.callback_query(F.data.startswith("edit_"))
async def edit_fields(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.")
        return
    act, field, cid_str = callback.data.split("_", 2)
    cid = int(cid_str)
    clients = load_db()
    client = next((c for c in clients if c["id"] == cid), None)
    if not client:
        await callback.message.answer("Клиент не найден!")
        return
    await state.clear()
    await state.update_data(edit_id=cid)

    if field == "contact":
        await callback.message.answer("Введите новый номер телефона или Telegram:", reply_markup=cancel_kb())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="contact")
        await callback.answer()
        return

    if field == "birth":
        await callback.message.answer("Введите новую дату рождения (дд.мм.гггг) или 'отсутствует':", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отсутствует")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="birth_date")
        await callback.answer()
        return

    if field == "account":
        await callback.message.answer("Введи:\n1. Логин\n2. Пароль\n3. Почта-пароль (можно пропустить)\n\nКаждый пункт с новой строки.", reply_markup=cancel_kb())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="account")
        await callback.answer()
        return

    if field == "console":
        await callback.message.answer("Выбери консоль:", reply_markup=console_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="console")
        await callback.answer()
        return

    if field == "region":
        await callback.message.answer("Выбери регион аккаунта:", reply_markup=region_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="region")
        await callback.answer()
        return

    if field == "reserve":
        await callback.message.answer("Загрузите новое фото резерв-кодов:", reply_markup=cancel_kb())
        await state.set_state(AddEditClient.edit_reserve)
        await callback.answer()
        return

    if field == "sub":
        await callback.message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                [KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_subs_total)
        await callback.answer()
        return

    if field == "games":
        await callback.message.answer("Введи список игр (каждая с новой строки):", reply_markup=cancel_kb())
        await state.set_state(AddEditClient.edit_games)
        await callback.answer()
        return

@dp.message(AddEditClient.edit_games)
async def edit_games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    data = await state.get_data()
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == data.get("edit_id"):
            c["games"] = games
            clients[i] = c
            save_db(clients)
            await clear_chat(message)
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
            else:
                sent = await message.answer(text, reply_markup=edit_keyboard(c))
            scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
            await state.clear()
            return

@dp.message(AddEditClient.edit_reserve)
async def edit_reserve_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if not message.photo:
        await message.answer("Отправьте фото!")
        return
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == data.get("edit_id"):
            c["reserve_photo_id"] = photo_id
            clients[i] = c
            save_db(clients)
            await clear_chat(message)
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
            else:
                sent = await message.answer(text, reply_markup=edit_keyboard(c))
            scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
            await state.clear()
            return

@dp.message(AddEditClient.edit_subs_total)
async def edit_subs_total(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == data.get("edit_id"):
                c["subscriptions"] = [{"name": "отсутствует"}]
                clients[i] = c
                save_db(clients)
                await clear_chat(message)
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    sent = await message.answer(text, reply_markup=edit_keyboard(c))
                scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
                await state.clear()
                return
        await message.answer("Ошибка обновления")
        await clear_and_main_menu(message, state)
        return
    if message.text == "Одна":
        await state.update_data(subs_total=1)
        await sub_edit_select(message, state, sub_num=1, only_one=True)
        return
    if message.text == "Две":
        await state.update_data(subs_total=2)
        await sub_edit_select(message, state, sub_num=1, only_one=False)
        return
    await message.answer("Выберите из списка!")

async def sub_edit_select(message, state: FSMContext, sub_num=1, only_one=False):
    if sub_num == 1:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
                [KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
        await message.answer("Выберите тип подписки:", reply_markup=kb)
        await state.set_state(AddEditClient.edit_sub_1_type)
    else:
        data = await state.get_data()
        prev = data.get("edit_sub_1_type")
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
        await state.set_state(AddEditClient.edit_sub_2_type)

@dp.message(AddEditClient.edit_sub_1_type)
async def edit_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == data.get("edit_id"):
                c["subscriptions"] = [{"name": "отсутствует"}]
                clients[i] = c
                save_db(clients)
                await clear_chat(message)
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    sent = await message.answer(text, reply_markup=edit_keyboard(c))
                scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
                await state.clear()
                return
        await message.answer("Ошибка обновления")
        await clear_and_main_menu(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(edit_sub_1_type=message.text)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_duration)

@dp.message(AddEditClient.edit_sub_1_duration)
async def edit_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    data = await state.get_data()
    sub_1_type = data.get("edit_sub_1_type")
    if (sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.edit_sub_1_start)

@dp.message(AddEditClient.edit_sub_1_start)
async def edit_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_1_duration")
    months = int(duration.replace("м", ""))
    end_str = calculate_end_date(message.text.strip(), months)
    sub = {
        "name": data.get("edit_sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end_str
    }
    await state.update_data(edit_sub_1=sub)
    subs_total = data.get("subs_total", 1)
    if subs_total == 2:
        await sub_edit_select(message, state, sub_num=2)
    else:
        data = await state.get_data()
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == data.get("edit_id"):
                c["subscriptions"] = [data.get("edit_sub_1")]
                clients[i] = c
                save_db(clients)
                await clear_chat(message)
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    sent = await message.answer(text, reply_markup=edit_keyboard(c))
                scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
                await state.clear()
                return

@dp.message(AddEditClient.edit_sub_2_type)
async def edit_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет подписки":
        data = await state.get_data()
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == data.get("edit_id"):
                c["subscriptions"] = [data.get("edit_sub_1")]
                clients[i] = c
                save_db(clients)
                await clear_chat(message)
                text, photo_id = format_card(c, show_photo_id=True)
                if photo_id:
                    sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
                else:
                    sent = await message.answer(text, reply_markup=edit_keyboard(c))
                scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
                await state.clear()
                return
        await message.answer("Ошибка обновления")
        await clear_and_main_menu(message, state)
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
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_2_duration)

@dp.message(AddEditClient.edit_sub_2_duration)
async def edit_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    data = await state.get_data()
    sub_2_type = data.get("edit_sub_2_type")
    if (sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=cancel_kb())
    await state.set_state(AddEditClient.edit_sub_2_start)

@dp.message(AddEditClient.edit_sub_2_start)
async def edit_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_2_duration")
    months = int(duration.replace("м", ""))
    end_str = calculate_end_date(message.text.strip(), months)
    sub = {
        "name": data.get("edit_sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end_str
    }
    data = await state.get_data()
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == data.get("edit_id"):
            subs = [data.get("edit_sub_1"), sub]
            c["subscriptions"] = subs
            clients[i] = c
            save_db(clients)
            await clear_chat(message)
            text, photo_id = format_card(c, show_photo_id=True)
            if photo_id:
                sent = await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(c))
            else:
                sent = await message.answer(text, reply_markup=edit_keyboard(c))
            scheduler.add_job(lambda: asyncio.create_task(delete_message(sent.chat.id, sent.message_id)), "date", run_date=datetime.now() + timedelta(minutes=5))
            await state.clear()
            return

# --- Save Client Changes ---
@dp.callback_query(F.data.startswith("save_"))
async def save_client_changes(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.")
        return
    cid = int(callback.data[len("save_"):])
    clients = load_db()
    client = next((c for c in clients if c["id"] == cid), None)
    if not client:
        await callback.answer("Клиент не найден.")
        return
    save_db(clients)
    await callback.answer("Изменения сохранены.")
    await clear_chat(callback.message)
    await start_cmd(callback.message, state)

# --- Delete message helper ---
async def delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

# --- Base Menu Handlers ---
@dp.message(F.text == "📦 База")
async def base_menu_handler(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await clear_chat(message)
    await message.answer("Меню базы:", reply_markup=base_menu())

@dp.message(F.text == "📩 Выгрузить всю базу в чат")
async def export_all_clients(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    clients = load_db()
    if not clients:
        await message.answer("База пуста.")
        return
    await clear_chat(message)
    for client in clients:
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "🔄 Заканчивается подписка (7д)")
async def expiring_subs(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    clients = load_db()
    threshold = datetime.now() + timedelta(days=7)
    filtered = []
    for c in clients:
        subs = c.get("subscriptions", [])
        for sub in subs:
            try:
                end_date = datetime.strptime(sub.get("end", "01.01.1970"), "%d.%m.%Y")
                if end_date <= threshold and sub.get("name") != "отсутствует":
                    filtered.append(c)
                    break
            except:
                continue
    if not filtered:
        await message.answer("Нет подписок, заканчивающихся в ближайшие 7 дней.")
        return
    await clear_chat(message)
    for client in filtered:
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "🎉 Скоро ДР (7д)")
async def upcoming_birthdays(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    clients = load_db()
    now = datetime.now()
    filtered = []
    for c in clients:
        bdate_str = c.get("birth_date")
        if not bdate_str or bdate_str == "отсутствует":
            continue
        try:
            bdate = datetime.strptime(bdate_str, "%d.%m.%Y")
            this_year_bday = bdate.replace(year=now.year)
            diff = (this_year_bday - now).days
            if 0 <= diff <= 7:
                filtered.append(c)
        except:
            continue
    if not filtered:
        await message.answer("Нет клиентов с ДР в ближайшие 7 дней.")
        return
    await clear_chat(message)
    for client in filtered:
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "⚠️ Без подписки")
async def clients_without_subscription(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    clients = load_db()
    filtered = [c for c in clients if c.get("subscriptions", [{}])[0].get("name") == "отсутствует"]
    if not filtered:
        await message.answer("Нет клиентов без подписки.")
        return
    await clear_chat(message)
    for client in filtered:
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

@dp.message(F.text == "⏯️ Сделать бэкап базы")
async def backup_db(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    if os.path.exists(DB_FILE):
        os.makedirs("/data/backups", exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"/data/backups/backup_{now_str}.json"
        shutil.copyfile(DB_FILE, backup_name)
        backups = sorted(glob.glob("/data/backups/backup_*.json"))
        if len(backups) > 5:
            os.remove(backups[0])
        await message.answer(f"Бэкап создан: {backup_name}")
    else:
        await message.answer("Файл базы не найден.")

@dp.message(F.text == "▶️ Восстановить из бэкапа")
async def restore_backup(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    backups = sorted(glob.glob("/data/backups/backup_*.json"), reverse=True)
    if not backups:
        await message.answer("Бэкапов нет.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=os.path.basename(b), callback_data=f"restore_{i}")]
        for i, b in enumerate(backups[:5])
    ])
    await state.update_data(backups=backups)
    await message.answer("Выберите бэкап для восстановления:", reply_markup=kb)

@dp.callback_query(F.data.startswith("restore_"))
async def restore_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.")
        return
    index = int(callback.data[len("restore_"):])
    data = await state.get_data()
    backups = data.get("backups", [])
    if index >= len(backups):
        await callback.answer("Некорректный выбор.")
        return
    backup_path = backups[index]
    shutil.copyfile(backup_path, DB_FILE)
    await callback.message.answer(f"Бэкап {os.path.basename(backup_path)} восстановлен.")
    await callback.answer()
    await clear_and_main_menu(callback.message, state)

@dp.message(F.text == "🗑️ Очистить базу")
async def clear_base_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True)
    await message.answer("Вы уверены, что хотите очистить базу? Подтвердите:", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm_clear)

@dp.message(AddEditClient.awaiting_confirm_clear)
async def clear_base_confirm(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Нет":
        await clear_and_main_menu(message, state)
        return
    if message.text == "Да":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True)
        await message.answer("Вы уверены? Это действие нельзя отменить!", reply_markup=kb)
        await state.set_state(AddEditClient.awaiting_confirm_clear)
        await state.update_data(confirm_second=True)
        return
    data = await state.get_data()
    if data.get("confirm_second"):
        # Очистка базы
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        await message.answer("База очищена.")
        await clear_and_main_menu(message, state)
        return
    await message.answer("Пожалуйста, подтвердите действие.")

async def on_startup():
    scheduler.start()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup)
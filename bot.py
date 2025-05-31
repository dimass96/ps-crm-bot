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
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cryptography.fernet import Fernet

# --- Настройки и файлы ---
DATA_DIR = "/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DB_FILE = os.path.join(DATA_DIR, "clients_db.json")
KEY_FILE = os.path.join(DATA_DIR, "secret.key")

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

# --- Крипто ---
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

# --- Работа с базой ---
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
        shutil.copyfile(DB_FILE, DB_FILE + "_backup")
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

# --- FSM состояния ---
class AddEditClient(StatesGroup):
    contact = State()
    birthdate_yesno = State()
    birth_date = State()
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
    edit_subs_total = State()
    edit_sub_1_type = State()
    edit_sub_1_duration = State()
    edit_sub_1_start = State()
    edit_sub_2_type = State()
    edit_sub_2_duration = State()
    edit_sub_2_start = State()
    edit_reserve = State()
    awaiting_confirm_clear = State()
    awaiting_confirm_restore = State()

# --- Клавиатуры ---
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

# --- Форматирование вывода клиента ---
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

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# --- Запуск и главное меню ---
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
                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.contact)

@dp.message(AddEditClient.contact)
async def step_contact(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    await state.update_data(contact=message.text.strip())
    await message.answer("Дата рождения есть?", reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("Да"), KeyboardButton("Нет")], [KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
                             reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.birth_date)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.birth_date)
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
                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
        [[KeyboardButton("Да"), KeyboardButton("Нет")], [KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
            [[KeyboardButton("Одна"), KeyboardButton("Две")], [KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
                [KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra")],
                [KeyboardButton("PS Plus Essential"), KeyboardButton("EA Play")],
                [KeyboardButton("Нет подписки")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True
        )
        await message.answer("Выберите тип подписки:", reply_markup=kb)
        await state.set_state(AddEditClient.sub_1_type)
    else:
        data = await state.get_data()
        prev = data.get("sub_1_type")
        if prev == "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential")],
                    [KeyboardButton("Нет подписки")],
                    [KeyboardButton("❌ Отмена")]
                ], resize_keyboard=True)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton("EA Play")],
                    [KeyboardButton("Нет подписки")],
                    [KeyboardButton("❌ Отмена")]
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
    # Следующий шаг - срок
    if message.text.startswith("PS Plus"):
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True
        )
    else:  # EA Play
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("1м"), KeyboardButton("12м")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True
        )
    await message.answer("Выберите срок подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_1_duration)

@dp.message(AddEditClient.sub_1_duration)
async def sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if not message.text.endswith("м"):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_1_duration=message.text)
    await message.answer("Введите дату оформления подписки (дд.мм.гггг):",
                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
    except:
        await message.answer("Введите дату в формате дд.мм.гггг")
        return
    await state.update_data(sub_1_start=message.text.strip())
    data = await state.get_data()
    total = data.get("subs_total", 1)
    if total == 1:
        # Сохраняем подписку и идем к играм
        name = data["sub_1_type"]
        duration = data["sub_1_duration"]
        start = data["sub_1_start"]
        end = calc_end_date(start, duration)
        await state.update_data(subscriptions=[{"name": name, "duration": duration, "start": start, "end": end}])
        await ask_games(message, state)
    else:
        # Запрашиваем вторую подписку
        await sub_select(message, state, sub_num=2)

@dp.message(AddEditClient.sub_2_type)
async def sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text == "Нет подписки":
        # Вторая подписка отсутствует, сохраняем первую и идем к играм
        data = await state.get_data()
        name = data["sub_1_type"]
        duration = data["sub_1_duration"]
        start = data["sub_1_start"]
        end = calc_end_date(start, duration)
        subs = [{"name": name, "duration": duration, "start": start, "end": end}]
        await state.update_data(subscriptions=subs)
        await ask_games(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    # Проверяем, чтобы вторая подписка была другой категории
    data = await state.get_data()
    if data.get("sub_1_type") == message.text:
        await message.answer("Вторая подписка должна быть другой категории!")
        return
    await state.update_data(sub_2_type=message.text)
    if message.text.startswith("PS Plus"):
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True
        )
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("1м"), KeyboardButton("12м")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True
        )
    await message.answer("Выберите срок второй подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_2_duration)

@dp.message(AddEditClient.sub_2_duration)
async def sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if not message.text.endswith("м"):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_2_duration=message.text)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):",
                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
    except:
        await message.answer("Введите дату в формате дд.мм.гггг")
        return
    await state.update_data(sub_2_start=message.text.strip())
    # Собираем обе подписки
    data = await state.get_data()
    sub1 = {
        "name": data["sub_1_type"],
        "duration": data["sub_1_duration"],
        "start": data["sub_1_start"],
        "end": calc_end_date(data["sub_1_start"], data["sub_1_duration"])
    }
    sub2 = {
        "name": data["sub_2_type"],
        "duration": data["sub_2_duration"],
        "start": data["sub_2_start"],
        "end": calc_end_date(data["sub_2_start"], data["sub_2_duration"])
    }
    await state.update_data(subscriptions=[sub1, sub2])
    await ask_games(message, state)

def calc_end_date(start_str, duration_str):
    start = datetime.strptime(start_str, "%d.%m.%Y")
    months = int(duration_str[:-1])
    year = start.year + (start.month + months - 1) // 12
    month = (start.month + months - 1) % 12 + 1
    day = start.day
    try:
        end_date = datetime(year, month, day)
    except:
        # На случай, если дня в месяце нет (например 31 в феврале)
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    return end_date.strftime("%d.%m.%Y")

async def ask_games(message, state: FSMContext):
    await message.answer("Оформлены игры?", reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("Да"), KeyboardButton("Нет")], [KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
        await ask_reserve_codes(message, state)
        return
    if message.text == "Да":
        await message.answer("Вводите игры построчно (можно много). Когда закончите — напишите 'Готово'.",
                             reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.games_input)
        await state.update_data(games=[])
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.games_input)
async def step_games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text.lower() == "готово":
        data = await state.get_data()
        games = data.get("games", [])
        await state.update_data(games=games)
        await ask_reserve_codes(message, state)
        return
    data = await state.get_data()
    games = data.get("games", [])
    games.append(message.text.strip())
    await state.update_data(games=games)

async def ask_reserve_codes(message, state: FSMContext):
    await message.answer("Есть резервные коды?", reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("Да"), KeyboardButton("Нет")], [KeyboardButton("❌ Отмена")]], resize_keyboard=True))
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
        await finalize_client(message, state)
        return
    if message.text == "Да":
        await message.answer("Отправьте скриншот с резервными кодами:",
                             reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.reserve_photo)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.reserve_photo, F.photo)
async def step_reserve_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(reserve_photo_id=file_id)
    await finalize_client(message, state)

@dp.message(AddEditClient.reserve_photo)
async def step_reserve_photo_wrong(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте фото с резервными кодами.")

async def finalize_client(message, state: FSMContext):
    data = await state.get_data()
    # Создаем ID клиента
    clients = load_db()
    client_id = get_next_client_id(clients)
    client = {
        "id": client_id,
        "contact": data.get("contact"),
        "birth_date": data.get("birth_date", "отсутствует"),
        "account": data.get("account", {}),
        "region": data.get("region", "—"),
        "console": data.get("console", "—"),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id")
    }
    save_new_client(client)
    await clear_chat(message)
    text, photo_id = format_card(client, show_photo_id=True)
    if photo_id:
        await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
    else:
        await message.answer(text, reply_markup=edit_keyboard(client))
    await state.clear()

# --- Поиск клиента ---
@dp.message(F.text == "🔍 Найти клиента")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await message.answer("Введите номер телефона или Telegram для поиска:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
    await state.set_state("search_input")

@dp.message("search_input")
async def search_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    results = find_clients(message.text)
    if not results:
        await message.answer("Клиент не найден.")
        return
    for client in results:
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(text, reply_markup=edit_keyboard(client))
    await state.clear()

# --- Обработка inline кнопок редактирования ---
@dp.callback_query(lambda c: c.data and c.data.startswith("edit_"))
async def edit_handler(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    parts = data.split("_")
    action = parts[1]
    client_id = int(parts[2])
    clients = load_db()
    client = next((c for c in clients if c["id"] == client_id), None)
    if not client:
        await callback.answer("Клиент не найден")
        return
    await state.update_data(edit_client=client)
    if action == "contact":
        await callback.message.answer("Введите новый номер или Telegram:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="contact")
    elif action == "account":
        await callback.message.answer("Введите новые данные аккаунта (логин\nпароль\nпочта-пароль):", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="account")
    elif action == "region":
        await callback.message.answer("Выберите регион:", reply_markup=region_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="region")
    elif action == "console":
        await callback.message.answer("Выберите консоль:", reply_markup=console_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="console")
    elif action == "birth":
        await callback.message.answer("Введите новую дату рождения (дд.мм.гггг) или 'отсутствует':", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="birth_date")
    elif action == "games":
        await callback.message.answer("Введите игры построчно. После окончания напишите 'Готово'.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_games)
    elif action == "reserve":
        await callback.message.answer("Отправьте новое фото резервных кодов или 'Нет' для удаления:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_reserve)
    elif action == "sub":
        # Начинаем редактировать подписки (полный процесс)
        await callback.message.answer("Выберите подписку для редактирования (1 или 2) или 'Удалить подписку':",
                                      reply_markup=ReplyKeyboardMarkup(
                                          [[KeyboardButton("1"), KeyboardButton("2")], [KeyboardButton("Удалить подписку")], [KeyboardButton("❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_subs_total)
    await callback.answer()

@dp.message(AddEditClient.edit_input)
async def edit_input_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    client = data.get("edit_client")
    field = data.get("edit_field")
    if not client or not field:
        await message.answer("Ошибка данных. Попробуйте заново.")
        await state.clear()
        return
    if field == "contact":
        client["contact"] = message.text.strip()
    elif field == "account":
        rows = message.text.strip().split("\n")
        login = rows[0].strip() if len(rows) > 0 else ""
        password = rows[1].strip() if len(rows) > 1 else ""
        mail_pass = rows[2].strip() if len(rows) > 2 else ""
        client["account"] = {"login": login, "password": password, "mail_pass": mail_pass}
    elif field == "region":
        if message.text not in ("укр", "тур", "другой", "(польша)", "(британия)"):
            await message.answer("Неверный регион, выберите из списка кнопками.")
            return
        client["region"] = message.text
    elif field == "console":
        if message.text not in ("PS4", "PS5", "PS4/PS5"):
            await message.answer("Неверная консоль, выберите из списка кнопками.")
            return
        client["console"] = message.text
    elif field == "birth_date":
        if message.text.lower() == "отсутствует":
            client["birth_date"] = "отсутствует"
        else:
            try:
                datetime.strptime(message.text.strip(), "%d.%m.%Y")
            except:
                await message.answer("Неверный формат даты. Дд.мм.гггг")
                return
            client["birth_date"] = message.text.strip()
    update_client(client)
    await state.update_data(edit_client=client)
    text, photo_id = format_card(client, show_photo_id=True)
    if photo_id:
        await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
    else:
        await message.answer(text, reply_markup=edit_keyboard(client))
    await state.set_state(AddEditClient.edit_choose)

@dp.message(AddEditClient.edit_games)
async def edit_games_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    client = data.get("edit_client")
    games = client.get("games", [])
    if message.text.lower() == "готово":
        client["games"] = games
        update_client(client)
        await state.update_data(edit_client=client)
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(text, reply_markup=edit_keyboard(client))
        await state.set_state(AddEditClient.edit_choose)
        return
    games.append(message.text.strip())
    client["games"] = games
    await state.update_data(edit_client=client)

@dp.message(AddEditClient.edit_reserve)
async def edit_reserve_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    client = data.get("edit_client")
    if message.text.lower() == "нет":
        client["reserve_photo_id"] = None
        update_client(client)
        await state.update_data(edit_client=client)
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(text, reply_markup=edit_keyboard(client))
        await state.set_state(AddEditClient.edit_choose)
        return
    if message.photo:
        photo = message.photo[-1]
        client["reserve_photo_id"] = photo.file_id
        update_client(client)
        await state.update_data(edit_client=client)
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(text, reply_markup=edit_keyboard(client))
        await state.set_state(AddEditClient.edit_choose)
        return
    await message.answer("Пожалуйста, отправьте фото или 'Нет'.")

@dp.message(AddEditClient.edit_subs_total)
async def edit_subs_total_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    data = await state.get_data()
    client = data.get("edit_client")
    if message.text == "Удалить подписку":
        client["subscriptions"] = [{"name": "отсутствует"}]
        update_client(client)
        await state.update_data(edit_client=client)
        text, photo_id = format_card(client, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
        else:
            await message.answer(text, reply_markup=edit_keyboard(client))
        await state.set_state(AddEditClient.edit_choose)
        return
    if message.text not in ("1", "2"):
        await message.answer("Введите '1' или '2', либо 'Удалить подписку'")
        return
    await state.update_data(edit_sub_num=int(message.text))
    await message.answer("Выберите тип подписки для редактирования:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra")],
            [KeyboardButton("PS Plus Essential"), KeyboardButton("EA Play")],
            [KeyboardButton("❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_1_type)

@dp.message(AddEditClient.edit_sub_1_type)
async def edit_sub_1_type_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой")
        return
    await state.update_data(edit_sub_type=message.text)
    if message.text.startswith("PS Plus"):
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("1м"), KeyboardButton("12м")],
                [KeyboardButton("❌ Отмена")]
            ], resize_keyboard=True)
    await message.answer("Выберите срок подписки:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_duration)

@dp.message(AddEditClient.edit_sub_1_duration)
async def edit_sub_1_duration_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    if not message.text.endswith("м"):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_duration=message.text)
    await message.answer("Введите дату оформления подписки (дд.мм.гггг):",
                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_1_start)

@dp.message(AddEditClient.edit_sub_1_start)
async def edit_sub_1_start_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
        return
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Введите дату в формате дд.мм.гггг")
        return
    data = await state.get_data()
    client = data.get("edit_client")
    sub_num = data.get("edit_sub_num")
    name = data.get("edit_sub_type")
    duration = data.get("edit_sub_duration")
    start = message.text.strip()
    end = calc_end_date(start, duration)
    subs = client.get("subscriptions", [])
    if sub_num > len(subs):
        subs.append({"name": name, "duration": duration, "start": start, "end": end})
    else:
        subs[sub_num-1] = {"name": name, "duration": duration, "start": start, "end": end}
    client["subscriptions"] = subs
    update_client(client)
    await state.update_data(edit_client=client)
    text, photo_id = format_card(client, show_photo_id=True)
    if photo_id:
        await message.answer_photo(photo_id, caption=text, reply_markup=edit_keyboard(client))
    else:
        await message.answer(text, reply_markup=edit_keyboard(client))
    await state.set_state(AddEditClient.edit_choose)

@dp.callback_query(lambda c: c.data and c.data.startswith("save_"))
async def save_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Изменения сохранены")
    await clear_chat(callback.message)
    await start_cmd(callback.message, state)

# --- Очистка базы с подтверждениями ---
@dp.message(F.text == "🗑️ Очистить базу")
async def ask_clear_base(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Да"), KeyboardButton("Нет")]
        ], resize_keyboard=True)
    await message.answer("Вы уверены, что хотите очистить базу? Напишите 'Да' или 'Нет'", reply_markup=kb)
    await state.set_state(AddEditClient.awaiting_confirm_clear)

@dp.message(AddEditClient.awaiting_confirm_clear)
async def clear_confirm(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("Подтверждаю"), KeyboardButton("Не подтверждаю")]
            ], resize_keyboard=True)
        await message.answer("Это действие нельзя будет отменить. Подтверждаете?", reply_markup=kb)
        await state.set_state(AddEditClient.awaiting_confirm_restore)
    else:
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)

@dp.message(AddEditClient.awaiting_confirm_restore)
async def clear_final_confirm(message: types.Message, state: FSMContext):
    if message.text == "Подтверждаю":
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        await message.answer("База очищена.")
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)
    else:
        await state.clear()
        await clear_chat(message)
        await start_cmd(message, state)

# --- Выгрузка базы ---
@dp.message(F.text == "📩 Выгрузить всю базу в чат")
async def dump_db(message: types.Message):
    clients = load_db()
    if not clients:
        await message.answer("База пустая.")
        return
    texts = []
    for c in clients:
        text, _ = format_card(c)
        texts.append(text)
    joined = "\n\n".join(texts)
    if len(joined) < 4000:
        await message.answer(joined)
    else:
        # Если очень много - разобьем на части
        for i in range(0, len(joined), 3500):
            await message.answer(joined[i:i+3500])

# --- Бэкап базы ---
@dp.message(F.text == "⏯️ Сделать бэкап базы")
async def backup_db(message: types.Message):
    if os.path.exists(DB_FILE):
        shutil.copyfile(DB_FILE, DB_FILE + ".backup")
        await message.answer("Бэкап базы создан.")
    else:
        await message.answer("База пуста, нечего бэкапить.")

# --- Восстановление из бэкапа ---
@dp.message(F.text == "▶️ Восстановить из бэкапа")
async def restore_db(message: types.Message):
    backup_file = DB_FILE + ".backup"
    if os.path.exists(backup_file):
        shutil.copyfile(backup_file, DB_FILE)
        await message.answer("База восстановлена из бэкапа.")
    else:
        await message.answer("Бэкап не найден.")

# --- Заканчиваются подписки через 7 дней ---
@dp.message(F.text == "🔄 Заканчивается подписка (7д)")
async def subs_ending_soon(message: types.Message):
    clients = load_db()
    today = datetime.now()
    soon_clients = []
    for c in clients:
        subs = c.get("subscriptions", [])
        for s in subs:
            try:
                end_date = datetime.strptime(s.get("end", "01.01.1900"), "%d.%m.%Y")
                if 0 <= (end_date - today).days <= 7:
                    soon_clients.append(c)
                    break
            except:
                continue
    if not soon_clients:
        await message.answer("Нет подписок, заканчивающихся в ближайшие 7 дней.")
        return
    for c in soon_clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

# --- Скоро дни рождения ---
@dp.message(F.text == "🎉 Скоро ДР (7д)")
async def birthdays_soon(message: types.Message):
    clients = load_db()
    today = datetime.now()
    soon_clients = []
    for c in clients:
        bd = c.get("birth_date", "")
        if bd == "отсутствует" or not bd:
            continue
        try:
            bd_date = datetime.strptime(bd, "%d.%m.%Y")
            bd_this_year = bd_date.replace(year=today.year)
            delta = (bd_this_year - today).days
            if 0 <= delta <= 7:
                soon_clients.append(c)
        except:
            continue
    if not soon_clients:
        await message.answer("Нет клиентов с ДР в ближайшие 7 дней.")
        return
    for c in soon_clients:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

# --- Без подписки ---
@dp.message(F.text == "⚠️ Без подписки")
async def no_subs_clients(message: types.Message):
    clients = load_db()
    no_subs = [c for c in clients if c.get("subscriptions", [{"name": "отсутствует"}])[0].get("name") == "отсутствует"]
    if not no_subs:
        await message.answer("Все клиенты с подписками.")
        return
    for c in no_subs:
        text, photo_id = format_card(c, show_photo_id=True)
        if photo_id:
            await message.answer_photo(photo_id, caption=text)
        else:
            await message.answer(text)

# --- Статистика ---
@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    clients = load_db()
    n_clients = len(clients)
    n_no_subs = sum(1 for c in clients if c.get("subscriptions", [{"name": "отсутствует"}])[0].get("name") == "отсутствует")
    n_with_subs = n_clients - n_no_subs
    subs_types = {}
    two_subs = sum(1 for c in clients if len(c.get("subscriptions", [])) > 1)
    soon_subs = 0
    soon_bd = 0
    n_games = 0
    region_map = {"укр":0,"тур":0,"(польша)":0,"(британия)":0,"другой":0}
    today = datetime.now()
    for c in clients:
        region = c.get("region", "другой")
        region_map[region] = region_map.get(region, 0) + 1
        subs = c.get("subscriptions", [])
        for s in subs:
            n = s.get("name")
            if n and n != "отсутствует":
                subs_types[n] = subs_types.get(n, 0) + 1
                try:
                    end_date = datetime.strptime(s.get("end", "01.01.1900"), "%d.%m.%Y")
                    if 0 <= (end_date - today).days <= 7:
                        soon_subs += 1
                except:
                    pass
        bd = c.get("birth_date", "")
        if bd and bd != "отсутствует":
            try:
                bd_date = datetime.strptime(bd, "%d.%m.%Y")
                bd_this_year = bd_date.replace(year=today.year)
                if 0 <= (bd_this_year - today).days <= 7:
                    soon_bd += 1
            except:
                pass
        games = c.get("games", [])
        if games:
            n_games += len(games)
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

# --- Очистка чата вручную ---
@dp.message(F.text == "📦 База")
async def base_section(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=base_menu())

@dp.message(F.text == "❌ Отмена")
async def cancel_action(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message)
    await start_cmd(message, state)

# --- Запуск планировщика (без ошибки no running event loop) ---
async def scheduler_start():
    scheduler.start()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
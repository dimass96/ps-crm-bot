import os
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.filters import Command, Text
from aiogram import F

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_FILE = "clients_db.json"

class AddClient(StatesGroup):
    waiting_number = State()
    waiting_birth_exists = State()
    waiting_birth_date = State()
    waiting_account = State()
    waiting_region = State()
    waiting_sub_exists = State()
    waiting_sub_count = State()
    waiting_sub_1_type = State()
    waiting_sub_1_term = State()
    waiting_sub_1_date = State()
    waiting_sub_2_type = State()
    waiting_sub_2_term = State()
    waiting_sub_2_date = State()
    waiting_games_exists = State()
    waiting_games = State()
    waiting_reserve_exists = State()
    waiting_reserve_photo = State()
    confirm = State()

class EditClient(StatesGroup):
    choosing_action = State()
    edit_number = State()
    edit_birth = State()
    edit_account = State()
    edit_region = State()
    edit_reserve = State()
    edit_sub = State()
    edit_sub_which = State()
    edit_sub_1_type = State()
    edit_sub_1_term = State()
    edit_sub_1_date = State()
    edit_sub_2_type = State()
    edit_sub_2_term = State()
    edit_sub_2_date = State()
    edit_games = State()
    confirm = State()

def load_clients():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_clients(clients):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def add_client(client):
    clients = load_clients()
    for i, c in enumerate(clients):
        if (c.get("number") == client.get("number") and c.get("number")) or (c.get("telegram") == client.get("telegram") and c.get("telegram")):
            clients[i] = client
            save_clients(clients)
            return
    clients.append(client)
    save_clients(clients)

def find_client(query):
    clients = load_clients()
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            return c
    return None

def update_client(client):
    add_client(client)

def delete_client(query):
    clients = load_clients()
    new_clients = [c for c in clients if not (c.get("number") == query or c.get("telegram") == query)]
    save_clients(new_clients)

def get_sub_types(exclude=None):
    types = ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]
    if exclude:
        return [t for t in types if t != exclude]
    return types

def get_term_buttons(sub_type):
    if sub_type == "EA Play":
        return ["1м", "12м"]
    return ["1м", "3м", "12м"]

def calc_end_date(start, term):
    months = 1
    if "3" in term:
        months = 3
    elif "12" in term:
        months = 12
    elif "1" in term:
        months = 1
    try:
        dt = datetime.strptime(start, "%d.%m.%Y")
        month = dt.month - 1 + months
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, [31,
              29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
              31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
        result = datetime(year, month, day)
        return result.strftime("%d.%m.%Y")
    except:
        return "ошибка даты"

def build_main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="🧹 Очистить чат")],
            [KeyboardButton(text="⬇️ Выгрузить базу")]
        ],
        resize_keyboard=True
    )
    return kb

def build_yes_no_cancel():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Есть"), KeyboardButton(text="Нету")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return kb

def build_sub_count():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Одна"), KeyboardButton(text="Две"), KeyboardButton(text="Никакая")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return kb

def build_sub_types(available=None):
    if available is None:
        available = ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t) for t in available[:3]],
            [KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return kb

def build_term_buttons(sub_type):
    if sub_type == "EA Play":
        terms = ["1м", "12м"]
    else:
        terms = ["1м", "3м", "12м"]
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t) for t in terms],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return kb

def build_region():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур"), KeyboardButton(text="другой")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return kb

def build_edit_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📱 Изменить номер-TG"), KeyboardButton("📅 Изменить дату рождения")],
            [KeyboardButton("🔐 Изменить аккаунт"), KeyboardButton("🌍 Изменить регион")],
            [KeyboardButton("🖼 Изменить резерв коды"), KeyboardButton("💳 Изменить подписку")],
            [KeyboardButton("🎮 Изменить игры"), KeyboardButton("✅ Сохранить")],
            [KeyboardButton("❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return kb

def format_client_info(client):
    text = ""
    number = client.get("number") or client.get("telegram") or "-"
    birth = client.get("birthdate", "отсутствует")
    account = client.get("account", "")
    mail = client.get("mailpass", "")
    region = client.get("region", "отсутствует")
    games = client.get("games", [])
    subs = client.get("subscriptions", [])
    reserve_path = client.get("reserve_path")
    if client.get("number"):
        text += f"<a href='tel:{client['number']}'>📱{client['number']}</a>"
    elif client.get("telegram"):
        text += f"<a href='https://t.me/{client['telegram']}'>📱@{client['telegram']}</a>"
    text += f" | {birth}\n"
    if mail or account:
        text += f"🔐 {mail} ; {account}\n"
    if subs:
        for s in subs:
            text += f"🗓 <b>{s['name']} {s['term']}</b>\n{s['start']} ➔ {s['end']}\n"
    else:
        text += "🗓 Подписки: (отсутствует)\n"
    text += f"🌍 Регион: ({region})\n"
    if games:
        text += "🎮 Игры:\n" + "\n".join(f"• {g}" for g in games)
    else:
        text += "🎮 Игры: (отсутствует)"
    return text, reserve_path

async def clear_chat(chat_id):
    try:
        async for msg in bot.get_chat_history(chat_id, limit=60):
            try:
                await bot.delete_message(chat_id, msg.message_id)
            except:
                pass
    except:
        pass

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=build_main_menu())

@dp.message(Text("🧹 Очистить чат"))
async def clear_cmd(message: types.Message, state: FSMContext):
    await clear_chat(message.chat.id)
    await message.answer("Чат очищен", reply_markup=build_main_menu())

@dp.message(Text("➕ Добавить клиента"))
async def add_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
    ))
    await state.set_state(AddClient.waiting_number)

@dp.message(AddClient.waiting_number)
async def process_number(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    data = await state.get_data()
    number = ""
    telegram = ""
    if message.text.startswith("+"):
        number = message.text
    elif message.text.startswith("@"):
        telegram = message.text[1:]
    else:
        number = message.text
    await state.update_data(number=number, telegram=telegram)
    await message.answer("Шаг 2\nДата рождения:\nВыберите Есть или Нету.", reply_markup=build_yes_no_cancel())
    await state.set_state(AddClient.waiting_birth_exists)

@dp.message(AddClient.waiting_birth_exists)
async def process_birth_exists(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_birth_date)
    elif message.text == "Нету":
        await state.update_data(birthdate="отсутствует")
        await message.answer("Шаг 3\nДанные от аккаунта:\n(логин/почта; пароль)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_account)

@dp.message(AddClient.waiting_birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025")
        return
    await state.update_data(birthdate=message.text)
    await message.answer("Шаг 3\nДанные от аккаунта:\n(логин/почта; пароль)", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
    ))
    await state.set_state(AddClient.waiting_account)

@dp.message(AddClient.waiting_account)
async def process_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    data = message.text.strip().split(";")
    mailpass = data[0].strip() if data else ""
    account = data[1].strip() if len(data) > 1 else ""
    await state.update_data(mailpass=mailpass, account=account)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=build_region())
    await state.set_state(AddClient.waiting_region)

@dp.message(AddClient.waiting_region)
async def process_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    region = message.text
    await state.update_data(region=region)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("Да"), KeyboardButton("Нет")],
            [KeyboardButton("❌ Отмена")]
        ], resize_keyboard=True
    ))
    await state.set_state(AddClient.waiting_sub_exists)

@dp.message(AddClient.waiting_sub_exists)
async def process_sub_exists(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    if message.text == "Да":
        await message.answer("Сколько подписок оформлено?", reply_markup=build_sub_count())
        await state.set_state(AddClient.waiting_sub_count)
    elif message.text == "Нет":
        await state.update_data(subscriptions=[])
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=build_yes_no_cancel())
        await state.set_state(AddClient.waiting_games_exists)

@dp.message(AddClient.waiting_sub_count)
async def process_sub_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    if message.text == "Никакая":
        await state.update_data(subscriptions=[])
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=build_yes_no_cancel())
        await state.set_state(AddClient.waiting_games_exists)
        return
    if message.text == "Одна":
        await message.answer("Выберите подписку:", reply_markup=build_sub_types())
        await state.set_state(AddClient.waiting_sub_1_type)
        await state.update_data(subs_count=1)
    elif message.text == "Две":
        await message.answer("Выберите первую подписку:", reply_markup=build_sub_types())
        await state.set_state(AddClient.waiting_sub_1_type)
        await state.update_data(subs_count=2, sub1=None, sub2=None)

@dp.message(AddClient.waiting_sub_1_type)
async def process_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    sub_type = message.text
    await state.update_data(sub_1_type=sub_type)
    await message.answer(f"Срок {sub_type}:", reply_markup=build_term_buttons(sub_type))
    await state.set_state(AddClient.waiting_sub_1_term)

@dp.message(AddClient.waiting_sub_1_term)
async def process_sub1_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    term = message.text
    await state.update_data(sub_1_term=term)
    await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
    ))
    await state.set_state(AddClient.waiting_sub_1_date)

@dp.message(AddClient.waiting_sub_1_date)
async def process_sub1_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025")
        return
    data = await state.get_data()
    subs_count = data.get("subs_count", 1)
    sub_1 = {
        "name": data["sub_1_type"],
        "term": data["sub_1_term"],
        "start": message.text,
        "end": calc_end_date(message.text, data["sub_1_term"])
    }
    if subs_count == 1:
        await state.update_data(subscriptions=[sub_1])
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=build_yes_no_cancel())
        await state.set_state(AddClient.waiting_games_exists)
    else:
        await state.update_data(sub_1=sub_1)
        excl = "EA Play" if data["sub_1_type"].startswith("PS Plus") else "PS Plus Deluxe"
        available = get_sub_types(exclude=data["sub_1_type"])
        await message.answer("Выберите вторую подписку:", reply_markup=build_sub_types(available))
        await state.set_state(AddClient.waiting_sub_2_type)

@dp.message(AddClient.waiting_sub_2_type)
async def process_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    sub_type = message.text
    await state.update_data(sub_2_type=sub_type)
    await message.answer(f"Срок {sub_type}:", reply_markup=build_term_buttons(sub_type))
    await state.set_state(AddClient.waiting_sub_2_term)

@dp.message(AddClient.waiting_sub_2_term)
async def process_sub2_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    term = message.text
    await state.update_data(sub_2_term=term)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
    ))
    await state.set_state(AddClient.waiting_sub_2_date)

@dp.message(AddClient.waiting_sub_2_date)
async def process_sub2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025")
        return
    data = await state.get_data()
    sub_1 = data.get("sub_1")
    sub_2 = {
        "name": data["sub_2_type"],
        "term": data["sub_2_term"],
        "start": message.text,
        "end": calc_end_date(message.text, data["sub_2_term"])
    }
    await state.update_data(subscriptions=[sub_1, sub_2])
    await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=build_yes_no_cancel())
    await state.set_state(AddClient.waiting_games_exists)

@dp.message(AddClient.waiting_games_exists)
async def process_games_exists(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("Введите список игр через Enter (по одной в строке):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_games)
    else:
        await state.update_data(games=[])
        await message.answer("Шаг 7\nЕсть резерв коды?", reply_markup=build_yes_no_cancel())
        await state.set_state(AddClient.waiting_reserve_exists)

@dp.message(AddClient.waiting_games)
async def process_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    games = [g.strip() for g in message.text.strip().split("\n") if g.strip()]
    await state.update_data(games=games)
    await message.answer("Шаг 7\nЕсть резерв коды?", reply_markup=build_yes_no_cancel())
    await state.set_state(AddClient.waiting_reserve_exists)

@dp.message(AddClient.waiting_reserve_exists)
async def process_reserve_exists(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("Загрузите скриншот резервных кодов:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("❌ Отмена")]], resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_reserve_photo)
    else:
        await state.update_data(reserve_path=None)
        await confirm_client(message, state)

@dp.message(AddClient.waiting_reserve_photo, F.photo)
async def process_reserve_photo(message: types.Message, state: FSMContext):
    file = await bot.get_file(message.photo[-1].file_id)
    file_path = f"reserves/{message.photo[-1].file_id}.jpg"
    os.makedirs("reserves", exist_ok=True)
    await bot.download_file(file.file_path, file_path)
    await state.update_data(reserve_path=file_path)
    await confirm_client(message, state)

@dp.message(AddClient.waiting_reserve_photo)
async def process_reserve_photo_error(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=build_main_menu())
        return
    await message.answer("Загрузите изображение скриншота резервных кодов.")

async def confirm_client(message, state):
    data = await state.get_data()
    client = {
        "number": data.get("number"),
        "telegram": data.get("telegram"),
        "birthdate": data.get("birthdate", "отсутствует"),
        "mailpass": data.get("mailpass"),
        "account": data.get("account"),
        "region": data.get("region", "отсутствует"),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "reserve_path": data.get("reserve_path")
    }
    add_client(client)
    await clear_chat(message.chat.id)
    text, reserve_path = format_client_info(client)
    if reserve_path:
        with open(reserve_path, "rb") as f:
            photo = InputFile(f)
            await bot.send_photo(
                message.chat.id,
                photo=photo,
                caption=text,
                reply_markup=build_edit_keyboard()
            )
    else:
        await bot.send_message(
            message.chat.id,
            text,
            reply_markup=build_edit_keyboard()
        )
    await state.clear()

@dp.message(Text("❌ Отмена"))
async def cancel_any(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message.chat.id)
    await message.answer("Операция отменена.", reply_markup=build_main_menu())

if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
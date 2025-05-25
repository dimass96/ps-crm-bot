import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
import asyncio
from datetime import datetime, timedelta

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460
DB_PATH = "clients_db.json"

def load_db():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_db(clients):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def add_client_to_db(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client_in_db(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c.get("number") == client["number"] and client["number"]:
            clients[i] = client
            break
        elif c.get("telegram") == client.get("telegram") and client.get("telegram"):
            clients[i] = client
            break
    else:
        clients.append(client)
    save_db(clients)

def find_client(query):
    clients = load_db()
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            return c
    return None

def delete_client(query):
    clients = load_db()
    new_clients = []
    deleted = False
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            deleted = True
            continue
        new_clients.append(c)
    save_db(new_clients)
    return deleted

async def clear_bot_messages(bot, chat_id):
    last_message_id = None
    async for msg in bot.get_chat_history(chat_id, limit=100):
        if msg.from_user and msg.from_user.id == bot.id:
            await bot.delete_message(chat_id, msg.message_id)
        last_message_id = msg.message_id
    return last_message_id

def get_main_menu_kb():
    kb = [
        [KeyboardButton(text="➕ Добавить клиента"), KeyboardButton(text="🔍 Найти клиента")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def get_yes_no_kb():
    kb = [[KeyboardButton(text="Да"), KeyboardButton(text="Нет")], [KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_region_kb():
    kb = [
        [KeyboardButton(text="(укр)"), KeyboardButton(text="(тур)"), KeyboardButton(text="(другой)")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_edit_kb():
    kb = [
        [KeyboardButton(text="📱 Изменить номер-TG"), KeyboardButton(text="📅 Изменить дату рождения")],
        [KeyboardButton(text="🔐 Изменить аккаунт"), KeyboardButton(text="🌍 Изменить регион")],
        [KeyboardButton(text="🖼 Изменить резерв коды"), KeyboardButton(text="💳 Изменить подписку")],
        [KeyboardButton(text="🎮 Изменить игры")],
        [KeyboardButton(text="✅ Сохранить"), KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_subs_kb():
    kb = [
        [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
        [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_sub_count_kb():
    kb = [
        [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_sub_term_kb(ps_type):
    if ps_type == "EA Play":
        kb = [
            [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ]
    else:
        kb = [
            [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def calc_sub_end(start, term):
    try:
        dt = datetime.strptime(start, "%d.%m.%Y")
        if term == "1м":
            end = dt + timedelta(days=30)
        elif term == "3м":
            end = dt + timedelta(days=90)
        elif term == "12м":
            end = dt + timedelta(days=365)
        else:
            end = dt
        return end.strftime("%d.%m.%Y")
    except Exception:
        return start

def format_client_info(client):
    info = ""
    number = client.get("number") or client.get("telegram") or ""
    birth = client.get("birthdate", "отсутствует")
    info += f"👤 {number} | {birth}\n"
    acc = client.get("account", "")
    region = client.get("region", "отсутствует")
    if acc:
        info += f"🔐 {acc} {region}\n"
    mail = client.get("mailpass", "")
    if mail:
        info += f"✉️ Почта-пароль: {mail}\n"
    subs = client.get("subscriptions", [])
    if not subs or (subs and subs[0].get("name") == "отсутствует"):
        info += "💳 Подписки: (отсутствует)\n"
    else:
        for s in subs:
            info += f"💳 {s['name']} {s['term']}\n📅 {s['start']} → {s['end']}\n"
    info += f"🌍 Регион: {region}\n"
    games = client.get("games", [])
    if games:
        info += "🎮 Игры:\n"
        for g in games:
            info += f"• {g}\n"
    return info

class AddClient(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_2b = State()
    step_3 = State()
    step_4 = State()
    step_5 = State()
    step_5a = State()
    step_5b = State()
    step_5c = State()
    step_6 = State()
    step_7 = State()
    step_7b = State()
    edit_number = State()
    edit_birth = State()
    edit_account = State()
    edit_region = State()
    edit_codes = State()
    edit_subs = State()
    edit_games = State()

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await clear_bot_messages(bot, message.chat.id)
    await message.answer("Главное меню", reply_markup=get_main_menu_kb())
    await state.clear()

@dp.message(F.text == "❌ Отмена")
async def cancel_any(message: types.Message, state: FSMContext):
    await clear_bot_messages(bot, message.chat.id)
    await message.answer("Главное меню", reply_markup=get_main_menu_kb())
    await state.clear()

@dp.message(F.text == "➕ Добавить клиента")
async def add_step_1(message: types.Message, state: FSMContext):
    await clear_bot_messages(bot, message.chat.id)
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.step_1)

@dp.message(AddClient.step_1)
async def add_step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    client = {
        "number": message.text if message.text.isdigit() else "",
        "telegram": message.text if not message.text.isdigit() else "",
    }
    await state.update_data(client=client)
    await message.answer("Шаг 2\nДата рождения:", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.step_2)

@dp.message(AddClient.step_2)
async def add_step_2b(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())
        await state.set_state(AddClient.step_2b)
    else:
        data = await state.get_data()
        client = data.get("client", {})
        client["birthdate"] = "отсутствует"
        await state.update_data(client=client)
        await message.answer("Шаг 3\nДанные от аккаунта:\n(3 строки: логин, пароль, пароль от почты/если есть)", reply_markup=get_cancel_kb())
        await state.set_state(AddClient.step_3)

@dp.message(AddClient.step_2b)
async def add_step_3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    client["birthdate"] = message.text
    await state.update_data(client=client)
    await message.answer("Шаг 3\nДанные от аккаунта:\n(3 строки: логин, пароль, пароль от почты/если есть)", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.step_3)

@dp.message(AddClient.step_3)
async def add_step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    lines = message.text.split('\n')
    login = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mailpass = lines[2] if len(lines) > 2 else ""
    acc = f"{login}; {password}"
    data = await state.get_data()
    client = data.get("client", {})
    client["account"] = acc
    client["mailpass"] = mailpass
    await state.update_data(client=client)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=get_region_kb())
    await state.set_state(AddClient.step_4)

@dp.message(AddClient.step_4)
async def add_step_5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    region = message.text
    data = await state.get_data()
    client = data.get("client", {})
    client["region"] = region
    await state.update_data(client=client)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.step_5)

@dp.message(AddClient.step_5)
async def add_step_5a(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    if message.text == "Нет":
        client["subscriptions"] = [{"name": "отсутствует"}]
        await state.update_data(client=client)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yes_no_kb())
        await state.set_state(AddClient.step_6)
        return
    await message.answer("Сколько подписок оформлено?", reply_markup=get_sub_count_kb())
    await state.set_state(AddClient.step_5a)

@dp.message(AddClient.step_5a)
async def add_step_5b(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    if message.text == "Одна":
        await message.answer("Выберите подписку:", reply_markup=get_subs_kb())
        await state.set_state(AddClient.step_5b)
    elif message.text == "Две":
        await message.answer("Выберите первую подписку:", reply_markup=get_subs_kb())
        await state.set_state(AddClient.step_5b)
        await state.update_data(sub_count=2, sub_current=1)
    else:
        await message.answer("Пожалуйста, выберите количество: Одна или Две.", reply_markup=get_sub_count_kb())

@dp.message(AddClient.step_5b)
async def add_step_5c(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    ps_type = message.text
    await state.update_data(ps_type_1=ps_type)
    await message.answer("Выберите срок подписки:", reply_markup=get_sub_term_kb(ps_type))
    await state.set_state(AddClient.step_5c)

@dp.message(AddClient.step_5c)
async def add_step_5d(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    term = message.text
    await state.update_data(term_1=term)
    await message.answer("Введите дату оформления подписки (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state("add_sub_1_date")

@dp.message(State("add_sub_1_date"))
async def add_step_5e(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    start_1 = message.text
    data = await state.get_data()
    client = data.get("client", {})
    subs = []
    ps_type_1 = data.get("ps_type_1")
    term_1 = data.get("term_1")
    end_1 = calc_sub_end(start_1, term_1)
    subs.append({"name": ps_type_1, "term": term_1, "start": start_1, "end": end_1})
    if data.get("sub_count", 1) == 2:
        other = "EA Play" if ps_type_1.startswith("PS Plus") else "PS Plus Deluxe"
        await message.answer(f"Выберите вторую подписку:", reply_markup=get_subs_kb())
        await state.update_data(subs=subs)
        await state.set_state("add_sub_2_type")
        return
    client["subscriptions"] = subs
    await state.update_data(client=client)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.step_6)

@dp.message(State("add_sub_2_type"))
async def add_step_5f(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    ps_type_2 = message.text
    await state.update_data(ps_type_2=ps_type_2)
    await message.answer("Выберите срок подписки:", reply_markup=get_sub_term_kb(ps_type_2))
    await state.set_state("add_sub_2_term")

@dp.message(State("add_sub_2_term"))
async def add_step_5g(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    term_2 = message.text
    await state.update_data(term_2=term_2)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state("add_sub_2_date")

@dp.message(State("add_sub_2_date"))
async def add_step_5h(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    subs = data.get("subs", [])
    ps_type_2 = data.get("ps_type_2")
    term_2 = data.get("term_2")
    start_2 = message.text
    end_2 = calc_sub_end(start_2, term_2)
    subs.append({"name": ps_type_2, "term": term_2, "start": start_2, "end": end_2})
    client["subscriptions"] = subs
    await state.update_data(client=client)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.step_6)

@dp.message(AddClient.step_6)
async def add_step_7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    if message.text == "Нет":
        data = await state.get_data()
        client = data.get("client", {})
        client["games"] = []
        await state.update_data(client=client)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yes_no_kb())
        await state.set_state(AddClient.step_7)
        return
    await message.answer("Введите список игр через Enter:", reply_markup=get_cancel_kb())
    await state.set_state("add_games")

@dp.message(State("add_games"))
async def add_step_7b(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    games = [g.strip() for g in message.text.split('\n') if g.strip()]
    data = await state.get_data()
    client = data.get("client", {})
    client["games"] = games
    await state.update_data(client=client)
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.step_7)

@dp.message(AddClient.step_7)
async def add_step_8(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    if message.text == "Нет":
        data = await state.get_data()
        client = data.get("client", {})
        client["codes_photo"] = None
        add_client_to_db(client)
        await clear_bot_messages(bot, message.chat.id)
        info = format_client_info(client)
        await message.answer(info, reply_markup=get_edit_kb())
        await state.clear()
        return
    await message.answer("Загрузите фото резервных кодов:", reply_markup=get_cancel_kb())
    await state.set_state("add_codes_photo")

@dp.message(State("add_codes_photo"))
async def finish_add_client(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото резервных кодов или отмените.")
        return
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    client = data.get("client", {})
    client["codes_photo"] = file_id
    add_client_to_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "🔍 Найти клиента")
async def search_client(message: types.Message, state: FSMContext):
    await clear_bot_messages(bot, message.chat.id)
    await message.answer("Введите номер телефона или Telegram:", reply_markup=get_cancel_kb())
    await state.set_state("searching")

@dp.message(State("searching"))
async def searching_process(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    client = find_client(message.text)
    await clear_bot_messages(bot, message.chat.id)
    if not client:
        await message.answer("Клиент не найден", reply_markup=get_main_menu_kb())
        await state.clear()
        return
    await state.update_data(client=client)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

# Редактирование данных клиента:
@dp.message(F.text == "📱 Изменить номер-TG")
async def edit_number(message: types.Message, state: FSMContext):
    await message.answer("Введите новый номер или Telegram:", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.edit_number)

@dp.message(AddClient.edit_number)
async def save_edit_number(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    if message.text.isdigit():
        client["number"] = message.text
        client["telegram"] = ""
    else:
        client["telegram"] = message.text
        client["number"] = ""
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "📅 Изменить дату рождения")
async def edit_birth(message: types.Message, state: FSMContext):
    await message.answer("Введите новую дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.edit_birth)

@dp.message(AddClient.edit_birth)
async def save_edit_birth(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    client["birthdate"] = message.text
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "🔐 Изменить аккаунт")
async def edit_account(message: types.Message, state: FSMContext):
    await message.answer("Введите новые данные аккаунта (логин, пароль, почта):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.edit_account)

@dp.message(AddClient.edit_account)
async def save_edit_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    lines = message.text.split('\n')
    login = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mailpass = lines[2] if len(lines) > 2 else ""
    acc = f"{login}; {password}"
    data = await state.get_data()
    client = data.get("client", {})
    client["account"] = acc
    client["mailpass"] = mailpass
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "🌍 Изменить регион")
async def edit_region(message: types.Message, state: FSMContext):
    await message.answer("Выберите новый регион:", reply_markup=get_region_kb())
    await state.set_state(AddClient.edit_region)

@dp.message(AddClient.edit_region)
async def save_edit_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    client["region"] = message.text
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "🖼 Изменить резерв коды")
async def edit_codes(message: types.Message, state: FSMContext):
    await message.answer("Загрузите новые резерв коды:", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.edit_codes)

@dp.message(AddClient.edit_codes)
async def save_edit_codes(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото резервных кодов или отмените.")
        return
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    client = data.get("client", {})
    client["codes_photo"] = file_id
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "💳 Изменить подписку")
async def edit_subs(message: types.Message, state: FSMContext):
    await message.answer("Выберите подписку для изменения:", reply_markup=get_subs_kb())
    await state.set_state(AddClient.edit_subs)

@dp.message(AddClient.edit_subs)
async def save_edit_subs(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    ps_type = message.text
    await state.update_data(ps_type_1=ps_type)
    await message.answer("Выберите срок подписки:", reply_markup=get_sub_term_kb(ps_type))
    await state.set_state("edit_sub_term")

@dp.message(State("edit_sub_term"))
async def save_edit_subs_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    term = message.text
    await state.update_data(term_1=term)
    await message.answer("Введите дату оформления подписки (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state("edit_sub_date")

@dp.message(State("edit_sub_date"))
async def save_edit_subs_final(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    data = await state.get_data()
    client = data.get("client", {})
    ps_type_1 = data.get("ps_type_1")
    term_1 = data.get("term_1")
    start_1 = message.text
    end_1 = calc_sub_end(start_1, term_1)
    client["subscriptions"] = [{"name": ps_type_1, "term": term_1, "start": start_1, "end": end_1}]
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "🎮 Изменить игры")
async def edit_games(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("client", {})
    games = client.get("games", [])
    games_str = "\n".join(games) if games else ""
    await message.answer(f"Текущий список игр:\n{games_str}\n\nВведите новый список через Enter:", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.edit_games)

@dp.message(AddClient.edit_games)
async def save_edit_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_any(message, state)
        return
    games = [g.strip() for g in message.text.split('\n') if g.strip()]
    data = await state.get_data()
    client = data.get("client", {})
    client["games"] = games
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    info = format_client_info(client)
    file_id = client.get("codes_photo")
    if file_id:
        await message.answer_photo(file_id, caption=info, reply_markup=get_edit_kb())
    else:
        await message.answer(info, reply_markup=get_edit_kb())
    await state.clear()

@dp.message(F.text == "✅ Сохранить")
async def save_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("client", {})
    update_client_in_db(client)
    await clear_bot_messages(bot, message.chat.id)
    name = client.get("number") or client.get("telegram")
    msg = f"✅ {name} успешно сохранён"
    m = await message.answer(msg)
    await asyncio.sleep(10)
    await bot.delete_message(m.chat.id, m.message_id)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
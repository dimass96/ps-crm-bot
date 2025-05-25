import os
import json
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup, KeyboardButton,
    InputFile
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460
DB_PATH = "clients_db.json"
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

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
        if c.get("number") == client.get("number") and c.get("number"):
            clients[i] = client
            break
        elif c.get("number") == "" and c.get("telegram") == client.get("telegram"):
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

def export_all():
    clients = load_db()
    result = []
    for c in clients:
        number = c.get("number") or c.get("telegram") or ""
        birth = c.get("birthdate", "отсутствует")
        acc = c.get("account", "")
        acc_mail = c.get("mailpass", "")
        region = c.get("region", "отсутствует")
        subs = c.get("subscriptions", [])
        games = c.get("games", [])
        text = f"Клиент: {number} | {birth}\nАккаунт: {acc} ({region})\n"
        if acc_mail:
            text += f"Почта-пароль: {acc_mail}\n"
        if subs and subs[0].get("name") != "отсутствует":
            for s in subs:
                text += f"Подписка: {s['name']} {s['term']} с {s['start']} по {s['end']}\n"
        else:
            text += "Подписки: отсутствует\n"
        text += f"Регион: {region}\n"
        if games:
            text += "Игры:\n"
            for g in games:
                text += f"- {g}\n"
        text += "\n"
        result.append(text)
    return "\n".join(result)

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").strftime("%d.%m.%Y")
    except Exception:
        return date_str

def format_subs(subs):
    out = ""
    for s in subs:
        out += f"💳 {s['name']} {s['term']}\n📅 {format_date(s['start'])} → {format_date(s['end'])}\n"
    return out

def format_client_info(client):
    number = client.get("number") or client.get("telegram") or ""
    birth = client.get("birthdate") or "отсутствует"
    account = client.get("account", "")
    mailpass = client.get("mailpass", "")
    region = client.get("region", "")
    subs = client.get("subscriptions", [])
    games = client.get("games", [])
    info = f"👤 {number} | {birth}\n"
    if account:
        info += f"🔐 {account}\n"
    if mailpass:
        info += f"✉️ Почта-пароль: {mailpass}\n"
    if subs and subs[0].get("name") != "отсутствует":
        info += format_subs(subs)
    else:
        info += "💳 Подписки: (отсутствует)\n"
    info += f"\n🌍 Регион: ({region})\n"
    if games:
        info += "\n🎮 Игры:\n"
        for g in games:
            info += f"• {g}\n"
    return info.strip()

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить клиента")],
        [KeyboardButton(text="🔍 Найти клиента")],
        [KeyboardButton(text="🧹 Очистить чат"), KeyboardButton(text="📄 Выгрузить базу")]
    ],
    resize_keyboard=True
)

def yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def region_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур")],
            [KeyboardButton(text="другой"), KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def sub_count_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def sub_choice_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
            [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def psplus_term_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def eaplay_term_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def edit_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Изменить номер-TG"), KeyboardButton(text="📅 Изменить дату рождения")],
            [KeyboardButton(text="🔐 Изменить аккаунт"), KeyboardButton(text="🌍 Изменить регион")],
            [KeyboardButton(text="🖼 Изменить резерв коды"), KeyboardButton(text="💳 Изменить подписку")],
            [KeyboardButton(text="🎮 Изменить игры"), KeyboardButton(text="✅ Сохранить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

class AddClientFSM(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_3 = State()
    step_4 = State()
    step_5 = State()
    step_5_subcount = State()
    step_5_sub1 = State()
    step_5_term1 = State()
    step_5_date1 = State()
    step_5_sub2 = State()
    step_5_term2 = State()
    step_5_date2 = State()
    step_6 = State()
    step_7 = State()
    codes_photo = State()
    finish = State()
    editing = State()
    edit_field = State()
    edit_photo = State()

async def clear_chat(chat_id):
    last_message_id = None
    async for msg in bot.get_chat_history(chat_id, limit=60):
        try:
            await bot.delete_message(chat_id, msg.message_id)
            last_message_id = msg.message_id
        except Exception:
            continue

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await clear_chat(message.chat.id)
    await message.answer("Меню:", reply_markup=main_menu_kb)

@dp.message(lambda m: m.text == "🧹 Очистить чат")
async def clear_cmd(message: Message, state: FSMContext):
    await state.clear()
    await clear_chat(message.chat.id)
    await message.answer("Чат очищен.", reply_markup=main_menu_kb)

@dp.message(lambda m: m.text == "📄 Выгрузить базу")
async def export_cmd(message: Message, state: FSMContext):
    text = export_all()
    path = os.path.join(MEDIA_DIR, "export.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    await message.answer_document(InputFile(path), caption="Выгрузка базы", reply_markup=main_menu_kb)

@dp.message(lambda m: m.text == "➕ Добавить клиента")
async def add_client(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddClientFSM.step_1)
    await message.answer("Шаг 1\nВведите номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(AddClientFSM.step_1)
async def add_step_1(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text.startswith("+"):
        number = message.text
        telegram = ""
    elif message.text.startswith("@"):
        number = ""
        telegram = message.text
    else:
        await message.answer("Введите корректный номер или Telegram (пример: +380..., либо @username).")
        return
    await state.update_data(number=number, telegram=telegram)
    await state.set_state(AddClientFSM.step_2)
    await message.answer("Шаг 2\nДата рождения есть?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_2)
async def add_step_2(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.step_2)
        await state.update_data(birth_ask=True)
        return
    elif message.text == "Нет":
        await state.update_data(birthdate="отсутствует")
        await state.set_state(AddClientFSM.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:\n(логин/пароль, почта если есть — каждое с новой строки)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    elif await state.get_data():
        d = await state.get_data()
        if d.get("birth_ask"):
            await state.update_data(birthdate=message.text.strip())
            await state.set_state(AddClientFSM.step_3)
            await message.answer("Шаг 3\nДанные от аккаунта:\n(логин/пароль, почта если есть — каждое с новой строки)", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
            return
    await message.answer("Пожалуйста, выберите Да или Нет.")

@dp.message(AddClientFSM.step_3)
async def add_step_3(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    lines = message.text.strip().split('\n')
    login = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mailpass = lines[2] if len(lines) > 2 else ""
    account = f"{login}; {password}" if password else login
    await state.update_data(account=account, mailpass=mailpass)
    await state.set_state(AddClientFSM.step_4)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb())

@dp.message(AddClientFSM.step_4)
async def add_step_4(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    region = message.text.strip()
    await state.update_data(region=region)
    await state.set_state(AddClientFSM.step_5)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_5)
async def add_step_5(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await state.set_state(AddClientFSM.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        return
    if message.text == "Да":
        await state.set_state(AddClientFSM.step_5_subcount)
        await message.answer("Сколько подписок оформлено?", reply_markup=sub_count_kb())
        return
    await message.answer("Пожалуйста, выберите Да или Нет.")

@dp.message(AddClientFSM.step_5_subcount)
async def add_step_5_subcount(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Одна":
        await state.update_data(sub_count=1)
        await state.set_state(AddClientFSM.step_5_sub1)
        await message.answer("Выберите подписку:", reply_markup=sub_choice_kb())
        return
    if message.text == "Две":
        await state.update_data(sub_count=2)
        await state.set_state(AddClientFSM.step_5_sub1)
        await state.update_data(subs=[])
        await message.answer("Выберите первую подписку:", reply_markup=sub_choice_kb())
        return
    await message.answer("Пожалуйста, выберите количество подписок.")

@dp.message(AddClientFSM.step_5_sub1)
async def add_step_5_sub1(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    sub = message.text.strip()
    await state.update_data(sub1=sub)
    if sub.startswith("EA Play"):
        await state.set_state(AddClientFSM.step_5_term1)
        await message.answer("Выберите срок подписки:", reply_markup=eaplay_term_kb())
    else:
        await state.set_state(AddClientFSM.step_5_term1)
        await message.answer("Выберите срок подписки:", reply_markup=psplus_term_kb())

@dp.message(AddClientFSM.step_5_term1)
async def add_step_5_term1(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    term = message.text.strip()
    await state.update_data(term1=term)
    await state.set_state(AddClientFSM.step_5_date1)
    await message.answer("Введите дату оформления первой подписки (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(AddClientFSM.step_5_date1)
async def add_step_5_date1(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    date1 = message.text.strip()
    data = await state.get_data()
    sub_count = data.get("sub_count", 1)
    sub1 = data.get("sub1")
    term1 = data.get("term1")
    sublist = []
    end1 = ""
    try:
        dt = datetime.strptime(date1, "%d.%m.%Y")
        if "1м" in term1:
            end1 = (dt + timedelta(days=30)).strftime("%d.%m.%Y")
        elif "3м" in term1:
            end1 = (dt + timedelta(days=90)).strftime("%d.%m.%Y")
        elif "12м" in term1:
            end1 = (dt + timedelta(days=365)).strftime("%d.%m.%Y")
        else:
            end1 = date1
    except Exception:
        end1 = date1
    sublist.append({"name": sub1, "term": term1, "start": date1, "end": end1})
    if sub_count == 1:
        await state.update_data(subscriptions=sublist)
        await state.set_state(AddClientFSM.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        return
    await state.update_data(subs=sublist)
    await state.set_state(AddClientFSM.step_5_sub2)
    other = "EA Play" if "PS Plus" in sub1 else "PS Plus Deluxe"
    await message.answer("Выберите вторую подписку:", reply_markup=sub_choice_kb())

@dp.message(AddClientFSM.step_5_sub2)
async def add_step_5_sub2(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    sub2 = message.text.strip()
    await state.update_data(sub2=sub2)
    if sub2.startswith("EA Play"):
        await state.set_state(AddClientFSM.step_5_term2)
        await message.answer("Выберите срок подписки:", reply_markup=eaplay_term_kb())
    else:
        await state.set_state(AddClientFSM.step_5_term2)
        await message.answer("Выберите срок подписки:", reply_markup=psplus_term_kb())

@dp.message(AddClientFSM.step_5_term2)
async def add_step_5_term2(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    term2 = message.text.strip()
    await state.update_data(term2=term2)
    await state.set_state(AddClientFSM.step_5_date2)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(AddClientFSM.step_5_date2)
async def add_step_5_date2(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    date2 = message.text.strip()
    data = await state.get_data()
    sublist = data.get("subs", [])
    sub2 = data.get("sub2")
    term2 = data.get("term2")
    end2 = ""
    try:
        dt = datetime.strptime(date2, "%d.%m.%Y")
        if "1м" in term2:
            end2 = (dt + timedelta(days=30)).strftime("%d.%m.%Y")
        elif "3м" in term2:
            end2 = (dt + timedelta(days=90)).strftime("%d.%m.%Y")
        elif "12м" in term2:
            end2 = (dt + timedelta(days=365)).strftime("%d.%m.%Y")
        else:
            end2 = date2
    except Exception:
        end2 = date2
    sublist.append({"name": sub2, "term": term2, "start": date2, "end": end2})
    await state.update_data(subscriptions=sublist)
    await state.set_state(AddClientFSM.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_6)
async def add_step_6(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(games=[])
        await state.set_state(AddClientFSM.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
        return
    if message.text == "Да":
        await message.answer("Введите список игр (каждая на новой строке):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.step_6)
        await state.update_data(games_ask=True)
        return
    data = await state.get_data()
    if data.get("games_ask"):
        games = [g.strip() for g in message.text.split("\n") if g.strip()]
        await state.update_data(games=games)
        await state.set_state(AddClientFSM.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
        return
    await message.answer("Пожалуйста, выберите Да или Нет.")

@dp.message(AddClientFSM.step_7)
async def add_step_7(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await save_and_show_client(message, state, with_codes=False)
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.codes_photo)
        return
    await message.answer("Пожалуйста, выберите Да или Нет.")

@dp.message(AddClientFSM.codes_photo, F.photo)
async def add_codes_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    file_path = os.path.join(MEDIA_DIR, f"{photo_id}.jpg")
    await bot.download(message.photo[-1], destination=file_path)
    await state.update_data(reserve_codes_path=file_path)
    await save_and_show_client(message, state, with_codes=True)

@dp.message(AddClientFSM.codes_photo)
async def add_codes_photo_invalid(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    await message.answer("Пожалуйста, отправьте скриншот с резервными кодами.")

async def save_and_show_client(message: Message, state: FSMContext, with_codes=False):
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path") if with_codes else ""
    }
    add_client_to_db(client)
    await state.clear()
    await clear_chat(message.chat.id)
    text = format_client_info(client)
    kb = edit_kb()
    if with_codes and client["reserve_codes_path"]:
        await message.answer_photo(InputFile(client["reserve_codes_path"]), caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    # message с инфой не удаляется 5 минут, можно реализовать тут таймер, если требуется

@dp.message(lambda m: m.text == "🔍 Найти клиента")
async def find_client_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер телефона или Telegram клиента:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClientFSM.editing)

@dp.message(AddClientFSM.editing)
async def process_find_edit(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    client = find_client(message.text.strip())
    if not client:
        await message.answer("Клиент не найден.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(edit_client=client)
    await clear_chat(message.chat.id)
    text = format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        await message.answer_photo(InputFile(client["reserve_codes_path"]), caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.set_state(AddClientFSM.edit_field)

@dp.message(AddClientFSM.edit_field)
async def process_edit_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("edit_client")
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "📱 Изменить номер-TG":
        await message.answer("Введите новый номер или Telegram:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(editing="number")
        return
    if message.text == "📅 Изменить дату рождения":
        await message.answer("Введите новую дату рождения:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(editing="birthdate")
        return
    if message.text == "🔐 Изменить аккаунт":
        await message.answer("Введите новые данные аккаунта (логин/пароль, почта если есть, каждое с новой строки):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(editing="account")
        return
    if message.text == "🌍 Изменить регион":
        await message.answer("Выберите новый регион:", reply_markup=region_kb())
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(editing="region")
        return
    if message.text == "🖼 Изменить резерв коды":
        await message.answer("Загрузите новый скриншот резервных кодов:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.edit_photo)
        return
    if message.text == "💳 Изменить подписку":
        await message.answer("Сколько подписок оформлено?", reply_markup=sub_count_kb())
        await state.set_state(AddClientFSM.step_5_subcount)
        await state.update_data(editing="subscriptions")
        return
    if message.text == "🎮 Изменить игры":
        old_games = "\n".join(client.get("games", [])) if client.get("games") else ""
        await message.answer(f"Текущий список игр:\n{old_games}\n\nВведите новый список игр (каждая с новой строки):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(editing="games")
        return
    if message.text == "✅ Сохранить":
        update_client_in_db(client)
        await state.clear()
        await clear_chat(message.chat.id)
        out = client.get("number") or client.get("telegram")
        await message.answer(f"✅ {out} успешно сохранен", reply_markup=main_menu_kb)
        return
    # после ввода новой инфы:
    editing = data.get("editing")
    if editing == "number":
        if message.text.startswith("+"):
            client["number"] = message.text
        elif message.text.startswith("@"):
            client["telegram"] = message.text
        update_client_in_db(client)
    elif editing == "birthdate":
        client["birthdate"] = message.text
        update_client_in_db(client)
    elif editing == "account":
        parts = message.text.split("\n")
        account = parts[0] if len(parts) > 0 else ""
        mail = parts[1] if len(parts) > 1 else ""
        mailpass = parts[2] if len(parts) > 2 else ""
        client["account"] = account
        client["mailpass"] = f"{mail}; {mailpass}" if mail and mailpass else mail or mailpass
        update_client_in_db(client)
    elif editing == "region":
        client["region"] = message.text
        update_client_in_db(client)
    elif editing == "games":
        games = [g.strip() for g in message.text.split("\n") if g.strip()]
        client["games"] = games
        update_client_in_db(client)
    await clear_chat(message.chat.id)
    text = format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        await message.answer_photo(InputFile(client["reserve_codes_path"]), caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.update_data(edit_client=client)
    await state.set_state(AddClientFSM.edit_field)

@dp.message(AddClientFSM.edit_photo, F.photo)
async def process_edit_codes_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("edit_client")
    photo_id = message.photo[-1].file_id
    file_path = os.path.join(MEDIA_DIR, f"{photo_id}.jpg")
    await bot.download(message.photo[-1], destination=file_path)
    client["reserve_codes_path"] = file_path
    update_client_in_db(client)
    await clear_chat(message.chat.id)
    text = format_client_info(client)
    kb = edit_kb()
    await message.answer_photo(InputFile(client["reserve_codes_path"]), caption=text, reply_markup=kb)
    await state.update_data(edit_client=client)
    await state.set_state(AddClientFSM.edit_field)

@dp.message(AddClientFSM.edit_photo)
async def process_edit_codes_photo_invalid(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    await message.answer("Пожалуйста, загрузите скриншот.")

if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from datetime import datetime, timedelta

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460
DB_PATH = "clients_db.json"
MEDIA_DIR = "media"

os.makedirs(MEDIA_DIR, exist_ok=True)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔍 Найти клиента")],
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
            [KeyboardButton(text="укр"), KeyboardButton(text="тур"), KeyboardButton(text="другой")],
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
        if c.get("number") == client["number"]:
            clients[i] = client
            break
        elif c.get("number") == "" and c.get("telegram") == client["telegram"]:
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

class AddClientFSM(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_3 = State()
    step_4 = State()
    step_5 = State()
    step_6 = State()
    step_7 = State()
    codes_photo = State()
    editing = State()
    edit_field = State()
    edit_photo = State()

class SearchClient(StatesGroup):
    searching = State()

async def start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await start(message, state)

@dp.message(lambda m: m.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddClientFSM.step_1)
    await message.answer("Шаг 1\nВведите номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(AddClientFSM.step_1)
async def add_step_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    number = ""
    telegram = ""
    val = message.text.strip()
    if val.startswith("@"):
        telegram = val
    elif any(x.isdigit() for x in val):
        number = val
    else:
        telegram = val
    await state.update_data(number=number, telegram=telegram)
    await state.set_state(AddClientFSM.step_2)
    await message.answer("Шаг 2\nЕсть ли дата рождения?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_2)
async def add_step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(birthdate="отсутствует")
        await state.set_state(AddClientFSM.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:\nВведите логин (e-mail), пароль и пароль от почты (если есть, 3 строки)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.step_2)
        await state.update_data(wait_birthdate=True)
        return
    if (await state.get_data()).get("wait_birthdate"):
        await state.update_data(birthdate=message.text.strip(), wait_birthdate=False)
        await state.set_state(AddClientFSM.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:\nВведите логин (e-mail), пароль и пароль от почты (если есть, 3 строки)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(AddClientFSM.step_3)
async def add_step_3(message: types.Message, state: FSMContext):
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
async def add_step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    region = message.text.strip()
    await state.update_data(region=region)
    await state.set_state(AddClientFSM.step_5)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_5)
async def add_step_5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await state.set_state(AddClientFSM.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        return
    if message.text == "Да":
        await message.answer("Сколько подписок оформлено?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Одна"), KeyboardButton(text="Две")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(wait_sub_count=True)
        return
    if message.text in ["Одна", "Две"]:
        await state.update_data(sub_count=message.text)
        await message.answer("Выберите подписку:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")], [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(wait_sub1=True)
        return
    if message.text in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        sub1 = {"name": message.text}
        await state.update_data(sub1=sub1)
        if message.text == "EA Play":
            await message.answer("Срок EA Play:", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        else:
            await message.answer("Срок PS Plus:", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(wait_sub1_term=True)
        return
    if message.text in ["1м", "3м", "12м"]:
        data = await state.get_data()
        if data.get("wait_sub1_term"):
            sub1 = data.get("sub1", {})
            sub1["term"] = message.text
            await state.update_data(sub1=sub1)
            await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
            await state.update_data(wait_sub1_date=True)
            return
        elif data.get("wait_sub2_term"):
            sub2 = data.get("sub2", {})
            sub2["term"] = message.text
            await state.update_data(sub2=sub2)
            await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
            await state.update_data(wait_sub2_date=True)
            return
    data = await state.get_data()
    if data.get("wait_sub1_date"):
        sub1 = data.get("sub1", {})
        sub1["start"] = message.text.strip()
        try:
            date_obj = datetime.strptime(sub1["start"], "%d.%m.%Y")
            months = int(sub1["term"].replace("м", ""))
            sub1["end"] = (date_obj + timedelta(days=30*months)).strftime("%d.%m.%Y")
        except Exception:
            sub1["end"] = ""
        await state.update_data(sub1=sub1)
        if data.get("sub_count") == "Две":
            await message.answer("Выберите вторую подписку:", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")], [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
            await state.update_data(wait_sub2=True)
            await state.update_data(wait_sub1_date=False)
            return
        else:
            await state.update_data(subscriptions=[sub1])
            await state.set_state(AddClientFSM.step_6)
            await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
            return
    if data.get("wait_sub2"):
        sub2 = {"name": message.text}
        await state.update_data(sub2=sub2)
        if message.text == "EA Play":
            await message.answer("Срок EA Play:", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        else:
            await message.answer("Срок PS Plus:", reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(wait_sub2_term=True)
        await state.update_data(wait_sub2=False)
        return
    if data.get("wait_sub2_date"):
        sub2 = data.get("sub2", {})
        sub2["start"] = message.text.strip()
        try:
            date_obj = datetime.strptime(sub2["start"], "%d.%m.%Y")
            months = int(sub2["term"].replace("м", ""))
            sub2["end"] = (date_obj + timedelta(days=30*months)).strftime("%d.%m.%Y")
        except Exception:
            sub2["end"] = ""
        await state.update_data(sub2=sub2)
        subs = [data.get("sub1", {}), sub2]
        await state.update_data(subscriptions=subs)
        await state.set_state(AddClientFSM.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        await state.update_data(wait_sub2_date=False)
        return

@dp.message(AddClientFSM.step_6)
async def add_step_6(message: types.Message, state: FSMContext):
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
        await state.update_data(wait_games=True)
        return
    data = await state.get_data()
    if data.get("wait_games"):
        games = [x.strip() for x in message.text.split('\n') if x.strip()]
        await state.update_data(games=games)
        await state.set_state(AddClientFSM.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_7)
async def add_step_7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(reserve_codes_path=None)
        await finish_add_client(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите фото с резервными кодами:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.codes_photo)
        return

@dp.message(AddClientFSM.codes_photo, F.photo)
async def codes_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    path = os.path.join(MEDIA_DIR, f"{file_id}.jpg")
    await message.bot.download(message.photo[-1], destination=path)
    await state.update_data(reserve_codes_path=path)
    await finish_add_client(message, state)

def format_client_info(client):
    text = f"👤 {client.get('number') or client.get('telegram') or ''} | {client.get('birthdate','отсутствует')}\n"
    text += f"🔐 {client.get('account','')}\n"
    if client.get('mailpass'):
        text += f"✉️ Почта-пароль: {client.get('mailpass')}\n"
    subs = client.get('subscriptions', [])
    if subs and subs[0].get("name") != "отсутствует":
        for s in subs:
            text += f"\n💳 {s.get('name')} {s.get('term','')} \n📅 {s.get('start','')} → {s.get('end','')}\n"
    else:
        text += "\n💳 Подписки: (отсутствует)\n"
    text += f"\n🌍 Регион: {client.get('region')}\n"
    games = client.get('games', [])
    if games:
        text += "\n🎮 Игры:\n" + "\n".join(f"• {g}" for g in games) + "\n"
    return text

async def finish_add_client(message, state: FSMContext):
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    add_client_to_db(client)
    text = f"✅ {client.get('number') or client.get('telegram')} добавлен\n\n"
    text += format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        with open(client["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.set_state(AddClientFSM.editing)

@dp.message(AddClientFSM.editing)
async def edit_menu(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "✅ Сохранить":
        update_client_in_db(client)
        await message.answer(f"✅ {client.get('number') or client.get('telegram')} успешно сохранен")
        await start(message, state)
        return
    if message.text == "📱 Изменить номер-TG":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field="number")
        await message.answer("Введите новый номер или Telegram", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "📅 Изменить дату рождения":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field="birthdate")
        await message.answer("Введите новую дату рождения", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "🔐 Изменить аккаунт":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field="account")
        await message.answer("Введите новые данные аккаунта (логин, пароль, почта через строку)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "🌍 Изменить регион":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field="region")
        await message.answer("Выберите регион", reply_markup=region_kb())
        return
    if message.text == "🖼 Изменить резерв коды":
        await state.set_state(AddClientFSM.edit_photo)
        await message.answer("Загрузите новые коды", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "💳 Изменить подписку":
        await state.set_state(AddClientFSM.step_5)
        await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())
        return
    if message.text == "🎮 Изменить игры":
        games = "\n".join(client.get("games", [])) if client.get("games") else ""
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field="games")
        await message.answer(f"Введите список игр (каждая на новой строке):\n{games}", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return

@dp.message(AddClientFSM.edit_field)
async def handle_edit_field(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.set_state(AddClientFSM.editing)
        data = await state.get_data()
        client = {
            "number": data.get("number", ""),
            "telegram": data.get("telegram", ""),
            "birthdate": data.get("birthdate", "отсутствует"),
            "account": data.get("account", ""),
            "mailpass": data.get("mailpass", ""),
            "region": data.get("region", ""),
            "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
            "games": data.get("games", []),
            "reserve_codes_path": data.get("reserve_codes_path", None)
        }
        text = format_client_info(client)
        kb = edit_kb()
        if client.get("reserve_codes_path"):
            with open(client["reserve_codes_path"], "rb") as img:
                await message.answer_photo(img, caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return
    data = await state.get_data()
    field = data.get("edit_field")
    if field == "number":
        val = message.text.strip()
        number = ""
        telegram = ""
        if val.startswith("@"):
            telegram = val
        elif any(x.isdigit() for x in val):
            number = val
        else:
            telegram = val
        await state.update_data(number=number, telegram=telegram)
    elif field == "birthdate":
        await state.update_data(birthdate=message.text.strip())
    elif field == "account":
        lines = message.text.strip().split('\n')
        login = lines[0] if len(lines) > 0 else ""
        password = lines[1] if len(lines) > 1 else ""
        mailpass = lines[2] if len(lines) > 2 else ""
        account = f"{login}; {password}" if password else login
        await state.update_data(account=account, mailpass=mailpass)
    elif field == "region":
        await state.update_data(region=message.text.strip())
    elif field == "games":
        games = [x.strip() for x in message.text.split('\n') if x.strip()]
        await state.update_data(games=games)
    await state.set_state(AddClientFSM.editing)
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    text = format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        with open(client["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

@dp.message(AddClientFSM.edit_photo, F.photo)
async def handle_edit_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    path = os.path.join(MEDIA_DIR, f"{file_id}.jpg")
    await message.bot.download(message.photo[-1], destination=path)
    await state.update_data(reserve_codes_path=path)
    await state.set_state(AddClientFSM.editing)
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    text = format_client_info(client)
    kb = edit_kb()
    with open(client["reserve_codes_path"], "rb") as img:
        await message.answer_photo(img, caption=text, reply_markup=kb)

@dp.message(lambda m: m.text == "🔍 Найти клиента")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер или Telegram для поиска:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(SearchClient.searching)

@dp.message(SearchClient.searching)
async def search_find(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    c = find_client(message.text.strip())
    if not c:
        await message.answer("Клиент не найден.", reply_markup=main_menu_kb())
        await state.clear()
        return
    await state.clear()
    await state.set_state(AddClientFSM.editing)
    await state.update_data(**c)
    text = format_client_info(c)
    kb = edit_kb()
    if c.get("reserve_codes_path"):
        with open(c["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

import asyncio
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import os
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460
DATA_FILE = "clients.json"

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher()

class AddClient(StatesGroup):
    contact = State()
    birth_date = State()
    console = State()
    account_login = State()
    account_password = State()
    mail_password = State()
    region = State()
    sub_count = State()
    sub1_type = State()
    sub1_duration = State()
    sub1_start = State()
    sub2_type = State()
    sub2_duration = State()
    sub2_start = State()
    games_ask = State()
    games = State()
    reserve_ask = State()
    reserve_photo = State()
    confirm = State()
    edit_choose = State()
    edit_input = State()
    edit_games = State()
    edit_subs = State()
    edit_reserve = State()

# --- DATABASE --- #
def load_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(clients):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def get_next_client_id(clients):
    return max([c.get("id", 0) for c in clients], default=0) + 1

def find_client(query):
    clients = load_db()
    for client in clients:
        if client["contact"].lower() == query.lower():
            return client
    return None

def update_client(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == client["id"]:
            clients[i] = client
            save_db(clients)
            return

def save_new_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def format_client_info(client):
    lines = []
    contact = client.get("contact", "—")
    bdate = client.get("birth_date") or "—"
    console = client.get("console", "—")
    lines.append(f"📱 <b>{contact}</b> | {bdate} <b>({console})</b>")
    login = client.get("account_login", "—")
    password = client.get("account_password", "—")
    mail_pass = client.get("mail_password", "—")
    lines.append(f"🔑 {login}; {password}")
    lines.append(f"📧 {mail_pass}")
    for i in (1, 2):
        sub = client.get(f"subscription_{i}", {})
        if sub and sub.get("type"):
            lines.append(f"💳 {sub['type']} {sub['duration']}")
            lines.append(f"📅 {sub['start_date']} — {sub['end_date']}")
    region = client.get("region", "—")
    lines.append(f"🌍 Регион: <b>({region})</b>")
    if client.get("games"):
        lines.append("\n🎮 Игры:")
        for game in client["games"]:
            lines.append(game)
    if client.get("reserve_codes"):
        lines.append("\n🗂 Резерв-коды: загружено")
    return "\n".join(lines)

# --- INLINE KEYBOARD FOR EDIT --- #
def edit_keyboard(client):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Контакт", callback_data=f"edit_contact_{client['id']}"),
         InlineKeyboardButton(text="🎂 Дата рождения", callback_data=f"edit_birth_date_{client['id']}")],
        [InlineKeyboardButton(text="🎮 Консоль", callback_data=f"edit_console_{client['id']}"),
         InlineKeyboardButton(text="🔑 Логин/Пароль", callback_data=f"edit_account_{client['id']}")],
        [InlineKeyboardButton(text="📧 Почта", callback_data=f"edit_mail_password_{client['id']}"),
         InlineKeyboardButton(text="🌍 Регион", callback_data=f"edit_region_{client['id']}")],
        [InlineKeyboardButton(text="💳 Подписки", callback_data=f"edit_subs_{client['id']}"),
         InlineKeyboardButton(text="🎲 Игры", callback_data=f"edit_games_{client['id']}")],
        [InlineKeyboardButton(text="🗂 Резерв-коды", callback_data=f"edit_reserve_{client['id']}")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="to_menu")]
    ])
    return kb

# --- START & MENU --- #
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔎 Поиск"), KeyboardButton(text="📤 Выгрузить базу")],
            [KeyboardButton(text="🧹 Очистить чат")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=kb)

@dp.message(F.text == "🧹 Очистить чат")
async def clear_chat(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Чат очищен.", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "📤 Выгрузить базу")
async def dump_db(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    clients = load_db()
    text = "\n\n".join(format_client_info(c) for c in clients)
    fname = f"clients_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)
    await bot.send_document(message.chat.id, InputFile(fname))
    os.remove(fname)

# --- FSM: ДОБАВЛЕНИЕ --- #
@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await state.set_state(AddClient.contact)
    await message.answer("Введите номер телефона или @username клиента:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True))

@dp.message(AddClient.contact)
async def add_contact(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    await state.update_data(contact=message.text.strip())
    await state.set_state(AddClient.birth_date)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Есть дата рождения"), KeyboardButton(text="Нет даты рождения")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("Есть ли дата рождения клиента?", reply_markup=kb)

@dp.message(AddClient.birth_date)
async def add_birth(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text == "Есть дата рождения":
        await message.answer("Введите дату рождения (дд.мм.гггг):")
        return
    elif message.text == "Нет даты рождения":
        await state.update_data(birth_date="")
        await state.set_state(AddClient.console)
    else:
        try:
            dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
            await state.update_data(birth_date=message.text.strip())
            await state.set_state(AddClient.console)
        except:
            await message.answer("Введите дату в формате дд.мм.гггг или выберите кнопку.")
            return
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS4"), KeyboardButton(text="PS5")],
            [KeyboardButton(text="PS4/PS5")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("Какая консоль у клиента?", reply_markup=kb)

@dp.message(AddClient.console)
async def add_console(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text not in ("PS4", "PS5", "PS4/PS5"):
        await message.answer("Выберите консоль кнопкой.")
        return
    await state.update_data(console=message.text)
    await state.set_state(AddClient.account_login)
    await message.answer("Введите ЛОГИН от аккаунта:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True))

@dp.message(AddClient.account_login)
async def add_login(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    await state.update_data(account_login=message.text.strip())
    await state.set_state(AddClient.account_password)
    await message.answer("Введите ПАРОЛЬ от аккаунта:")

@dp.message(AddClient.account_password)
async def add_pass(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    await state.update_data(account_password=message.text.strip())
    await state.set_state(AddClient.mail_password)
    await message.answer("Введите ПАРОЛЬ от почты (или '-' если нет):")

@dp.message(AddClient.mail_password)
async def add_mail(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    mail = message.text.strip() if message.text.strip() != "-" else ""
    await state.update_data(mail_password=mail)
    await state.set_state(AddClient.region)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур")],
            [KeyboardButton(text="польша"), KeyboardButton(text="британия")],
            [KeyboardButton(text="другой")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите регион аккаунта:", reply_markup=kb)

@dp.message(AddClient.region)
async def add_region(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text not in ("укр", "тур", "польша", "британия", "другой"):
        await message.answer("Выберите регион кнопкой.")
        return
    await state.update_data(region=message.text)
    await state.set_state(AddClient.sub_count)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Нет подписки")],
            [KeyboardButton(text="Одна подписка")],
            [KeyboardButton(text="Две подписки")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("Сколько подписок у клиента?", reply_markup=kb)

@dp.message(AddClient.sub_count)
async def add_sub_count(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text == "Нет подписки":
        await state.update_data(subscription_1={}, subscription_2={})
        await state.set_state(AddClient.games_ask)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Есть игры")],
                [KeyboardButton(text="Нет игр")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Есть ли у клиента оформленные игры?", reply_markup=kb)
    elif message.text == "Одна подписка":
        await state.update_data(subscription_2={})
        await state.set_state(AddClient.sub1_type)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential")],
                [KeyboardButton(text="EA Play")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите подписку:", reply_markup=kb)
    elif message.text == "Две подписки":
        await state.set_state(AddClient.sub1_type)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential")],
                [KeyboardButton(text="EA Play")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите первую подписку:", reply_markup=kb)
        await state.update_data(want_second_sub=True)
    else:
        await message.answer("Выберите вариант кнопкой.")

@dp.message(AddClient.sub1_type)
async def add_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой.")
        return
    sub1 = {"type": message.text}
    await state.update_data(subscription_1=sub1)
    if message.text == "EA Play":
        durations = [["1м", "12м"]]
    else:
        durations = [["1м", "3м", "12м"]]
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in row] for row in durations
        ] + [[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
    await state.set_state(AddClient.sub1_duration)
    await message.answer("Выберите срок подписки:", reply_markup=kb)

@dp.message(AddClient.sub1_duration)
async def add_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    data = await state.get_data()
    sub1 = data.get("subscription_1", {})
    if sub1.get("type") == "EA Play" and message.text not in ("1м", "12м"):
        await message.answer("EA Play только 1м или 12м.")
        return
    elif sub1.get("type") != "EA Play" and message.text not in ("1м", "3м", "12м"):
        await message.answer("Выберите срок кнопкой.")
        return
    sub1["duration"] = message.text
    await state.update_data(subscription_1=sub1)
    await state.set_state(AddClient.sub1_start)
    await message.answer("Введите дату оформления подписки (дд.мм.гггг):")

@dp.message(AddClient.sub1_start)
async def add_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    data = await state.get_data()
    sub1 = data.get("subscription_1", {})
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        sub1["start_date"] = message.text.strip()
        months = int(sub1["duration"].replace("м", ""))
        sub1["end_date"] = (dt + timedelta(days=30*months)).strftime("%d.%m.%Y")
        await state.update_data(subscription_1=sub1)
    except:
        await message.answer("Введите дату в формате дд.мм.гггг.")
        return
    if data.get("want_second_sub"):
        await state.set_state(AddClient.sub2_type)
        if sub1["type"] != "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
    else:
        await state.set_state(AddClient.games_ask)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Есть игры")],
                [KeyboardButton(text="Нет игр")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Есть ли у клиента оформленные игры?", reply_markup=kb)

@dp.message(AddClient.sub2_type)
async def add_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    data = await state.get_data()
    sub1 = data.get("subscription_1", {})
    if sub1["type"] == "EA Play" and message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
        await message.answer("Вторая подписка должна быть из другой категории.")
        return
    if sub1["type"] != "EA Play" and message.text != "EA Play":
        await message.answer("Вторая подписка должна быть EA Play.")
        return
    sub2 = {"type": message.text}
    await state.update_data(subscription_2=sub2)
    if message.text == "EA Play":
        durations = [["1м", "12м"]]
    else:
        durations = [["1м", "3м", "12м"]]
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label) for label in row] for row in durations
        ] + [[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
    await state.set_state(AddClient.sub2_duration)
    await message.answer("Выберите срок подписки:", reply_markup=kb)

@dp.message(AddClient.sub2_duration)
async def add_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    data = await state.get_data()
    sub2 = data.get("subscription_2", {})
    if sub2.get("type") == "EA Play" and message.text not in ("1м", "12м"):
        await message.answer("EA Play только 1м или 12м.")
        return
    elif sub2.get("type") != "EA Play" and message.text not in ("1м", "3м", "12м"):
        await message.answer("Выберите срок кнопкой.")
        return
    sub2["duration"] = message.text
    await state.update_data(subscription_2=sub2)
    await state.set_state(AddClient.sub2_start)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):")

@dp.message(AddClient.sub2_start)
async def add_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    data = await state.get_data()
    sub2 = data.get("subscription_2", {})
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        sub2["start_date"] = message.text.strip()
        months = int(sub2["duration"].replace("м", ""))
        sub2["end_date"] = (dt + timedelta(days=30*months)).strftime("%d.%m.%Y")
        await state.update_data(subscription_2=sub2)
    except:
        await message.answer("Введите дату в формате дд.мм.гггг.")
        return
    await state.set_state(AddClient.games_ask)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Есть игры")],
            [KeyboardButton(text="Нет игр")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("Есть ли у клиента оформленные игры?", reply_markup=kb)

@dp.message(AddClient.games_ask)
async def add_games_ask(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text == "Есть игры":
        await state.update_data(games=[])
        await state.set_state(AddClient.games)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Закончить ввод игр")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Вводите по одной игре в строку. Когда закончите, нажмите 'Закончить ввод игр'.", reply_markup=kb)
    elif message.text == "Нет игр":
        await state.update_data(games=[])
        await state.set_state(AddClient.reserve_ask)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Есть резерв-коды")],
                [KeyboardButton(text="Нет резерв-кодов")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Есть ли резерв-коды?", reply_markup=kb)
    else:
        await message.answer("Выберите вариант кнопкой.")

@dp.message(AddClient.games)
async def add_games(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text == "Закончить ввод игр":
        await state.set_state(AddClient.reserve_ask)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Есть резерв-коды")],
                [KeyboardButton(text="Нет резерв-кодов")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Есть ли резерв-коды?", reply_markup=kb)
        return
    data = await state.get_data()
    games = data.get("games", [])
    games.append(message.text.strip())
    await state.update_data(games=games)
    await message.answer("Добавлено. Введите следующую игру или нажмите 'Закончить ввод игр'.")

@dp.message(AddClient.reserve_ask)
async def add_reserve_ask(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await cmd_start(message, state)
        return
    if message.text == "Есть резерв-коды":
        await state.set_state(AddClient.reserve_photo)
        await message.answer("Отправьте фото резерв-кодов:", reply_markup=ReplyKeyboardRemove())
    elif message.text == "Нет резерв-кодов":
        await state.update_data(reserve_codes=[])
        await finish_add_client(message, state)
    else:
        await message.answer("Выберите вариант кнопкой.")

@dp.message(AddClient.reserve_photo)
async def add_reserve_photo(message: types.Message, state: FSMContext):
    if message.photo:
        photo_id = message.photo[-1].file_id
        await state.update_data(reserve_codes=[photo_id])
        await finish_add_client(message, state)
    else:
        await message.answer("Пожалуйста, отправьте фото!")

async def finish_add_client(message, state: FSMContext):
    data = await state.get_data()
    client = {
        "id": get_next_client_id(load_db()),
        "contact": data.get("contact", ""),
        "birth_date": data.get("birth_date", ""),
        "console": data.get("console", ""),
        "account_login": data.get("account_login", ""),
        "account_password": data.get("account_password", ""),
        "mail_password": data.get("mail_password", ""),
        "region": data.get("region", ""),
        "subscription_1": data.get("subscription_1", {}),
        "subscription_2": data.get("subscription_2", {}),
        "games": data.get("games", []),
        "reserve_codes": data.get("reserve_codes", []),
    }
    save_new_client(client)
    await state.clear()
    await message.answer("Клиент добавлен!", reply_markup=ReplyKeyboardRemove())
    msg = await message.answer(format_client_info(client), parse_mode="HTML", reply_markup=edit_keyboard(client))
    # Бот сразу предлагает редактирование

# --- FSM: ПОИСК --- #
@dp.message(F.text == "🔎 Поиск")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер телефона или @username клиента для поиска:")

@dp.message()
async def search_flow(message: types.Message):
    if message.text.startswith("+") or message.text.startswith("@"):
        client = find_client(message.text.strip())
        if client:
            await message.answer(format_client_info(client), parse_mode="HTML", reply_markup=edit_keyboard(client))
        else:
            await message.answer("Клиент не найден.")

# --- FSM: EDIT --- #
@dp.callback_query(F.data.startswith("edit_"))
async def edit_field_call(callback: types.CallbackQuery, state: FSMContext):
    action, field, cid = callback.data.split("_", 2)
    cid = int(cid)
    client = None
    for c in load_db():
        if c["id"] == cid:
            client = c
            break
    if not client:
        await callback.message.answer("Клиент не найден.")
        return

    await state.update_data(edit_id=cid, edit_field=field)
    # Универсальные поля
    if field in ("contact", "birth_date", "console", "account", "mail_password", "region"):
        text = {
            "contact": "Введите новый контакт:",
            "birth_date": "Введите новую дату рождения (дд.мм.гггг) или пусто:",
            "console": "Выберите консоль (PS4, PS5, PS4/PS5):",
            "account": "Введите новый логин и пароль в формате login;password",
            "mail_password": "Введите новый пароль от почты:",
            "region": "Введите новый регион (укр, тур, польша, британия, другой):"
        }[field]
        await callback.message.answer(text)
        await state.set_state(AddClient.edit_input)
        return
    if field == "games":
        await callback.message.answer("Вводите игры по одной в строку. 'Готово' чтобы закончить.")
        await state.set_state(AddClient.edit_games)
        await state.update_data(new_games=[])
        return
    if field == "subs":
        await callback.message.answer("Измените подписки (лучше пересоздать клиента — если нужно, доработаю).")
        await state.clear()
        return
    if field == "reserve":
        await callback.message.answer("Отправьте новое фото резерв-кодов:")
        await state.set_state(AddClient.edit_reserve)
        return

@dp.message(AddClient.edit_input)
async def edit_input_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cid = data.get("edit_id")
    field = data.get("edit_field")
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == cid:
            if field == "account":
                if ";" not in message.text:
                    await message.answer("Формат: логин;пароль")
                    return
                login, password = message.text.split(";", 1)
                c["account_login"] = login.strip()
                c["account_password"] = password.strip()
            elif field == "console":
                if message.text not in ("PS4", "PS5", "PS4/PS5"):
                    await message.answer("Выберите консоль кнопкой.")
                    return
                c["console"] = message.text
            elif field == "region":
                if message.text not in ("укр", "тур", "польша", "британия", "другой"):
                    await message.answer("Введите корректный регион.")
                    return
                c["region"] = message.text
            else:
                c[field] = message.text.strip()
            clients[i] = c
            save_db(clients)
            await message.answer("Изменено! Вот новая карточка клиента:")
            await message.answer(format_client_info(c), parse_mode="HTML", reply_markup=edit_keyboard(c))
            await state.clear()
            return
    await message.answer("Ошибка обновления клиента.")
    await state.clear()

@dp.message(AddClient.edit_games)
async def edit_games_handler(message: types.Message, state: FSMContext):
    if message.text.lower() in ("готово", "Готово"):
        data = await state.get_data()
        games = data.get("new_games", [])
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["games"] = games
                clients[i] = c
                save_db(clients)
                await message.answer("Игры обновлены!", reply_markup=None)
                await message.answer(format_client_info(c), parse_mode="HTML", reply_markup=edit_keyboard(c))
                await state.clear()
                return
        await message.answer("Ошибка обновления клиента.")
        await state.clear()
    else:
        data = await state.get_data()
        games = data.get("new_games", [])
        games.append(message.text.strip())
        await state.update_data(new_games=games)
        await message.answer("Добавлено! Введите следующую игру или 'Готово'.")

@dp.message(AddClient.edit_reserve)
async def edit_reserve_handler(message: types.Message, state: FSMContext):
    if message.photo:
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["reserve_codes"] = [photo_id]
                clients[i] = c
                save_db(clients)
                await message.answer("Резерв-коды обновлены!", reply_markup=None)
                await message.answer(format_client_info(c), parse_mode="HTML", reply_markup=edit_keyboard(c))
                await state.clear()
                return
        await message.answer("Ошибка обновления клиента.")
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте фото!")

@dp.callback_query(F.data == "to_menu")
async def to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(callback.message, state)

# --- NOTIFICATIONS --- #
async def notify_subs_and_birthdays():
    while True:
        clients = load_db()
        today = datetime.now()
        tomorrow = (today + timedelta(days=1)).strftime("%d.%m.%Y")
        for c in clients:
            for i in (1, 2):
                sub = c.get(f"subscription_{i}", {})
                if sub and sub.get("end_date") == tomorrow:
                    await bot.send_message(ADMIN_ID, f"У клиента {c['contact']} завтра заканчивается подписка: {sub['type']}")
        for c in clients:
            if c.get("birth_date"):
                try:
                    bdate = datetime.strptime(c["birth_date"], "%d.%m.%Y")
                    if bdate.day == today.day and bdate.month == today.month:
                        await bot.send_message(ADMIN_ID, f"Сегодня день рождения у клиента: {c['contact']}")
                except:
                    continue
        await asyncio.sleep(60 * 60 * 6)

async def main():
    asyncio.create_task(notify_subs_and_birthdays())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

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

def update_client_in_db(index, client):
    clients = load_db()
    if 0 <= index < len(clients):
        clients[index] = client
        save_db(clients)

def find_client(query):
    clients = load_db()
    for idx, c in enumerate(clients):
        if c.get("number") == query or c.get("telegram") == query:
            return idx, c
    return None, None

class AddClient(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_2_date = State()
    step_3 = State()
    step_4 = State()
    step_4_console = State()
    step_5 = State()
    step_5_main = State()
    step_5_1_type = State()
    step_5_1_term = State()
    step_5_1_date = State()
    step_5_2_type = State()
    step_5_2_term = State()
    step_5_2_date = State()
    step_6 = State()
    step_6_games = State()
    step_7 = State()
    step_7_photo = State()
    editing_number = State()
    editing_birth = State()
    editing_account = State()
    editing_console = State()
    editing_region = State()
    editing_subscription = State()
    editing_games = State()
    editing_reserve = State()
    searching = State()

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

def get_main_menu():
    kb = [
        [types.KeyboardButton(text="➕ Добавить клиента")],
        [types.KeyboardButton(text="🔍 Найти клиента")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_yesno_kb():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Да"), types.KeyboardButton(text="Нет")],
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_cancel_kb():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="❌ Отмена")]], resize_keyboard=True
    )

def get_region_kb():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="укр"), types.KeyboardButton(text="тур"), types.KeyboardButton(text="другой")],
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_console_kb():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="PS4"), types.KeyboardButton(text="PS5"), types.KeyboardButton(text="PS4/PS5")],
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_subscription_type_kb():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="PS Plus Deluxe"), types.KeyboardButton(text="PS Plus Extra")],
            [types.KeyboardButton(text="PS Plus Essential"), types.KeyboardButton(text="EA Play")],
            [types.KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_subscription_term_kb(sub):
    if sub == "EA Play":
        kb = [
            [types.KeyboardButton(text="1м"), types.KeyboardButton(text="12м")],
            [types.KeyboardButton(text="❌ Отмена")]
        ]
    else:
        kb = [
            [types.KeyboardButton(text="1м"), types.KeyboardButton(text="3м"), types.KeyboardButton(text="12м")],
            [types.KeyboardButton(text="❌ Отмена")]
        ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_edit_kb():
    kb = [
        [
            types.InlineKeyboardButton(text="📱 Изменить номер-TG", callback_data="edit_number"),
            types.InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birth"),
        ],
        [
            types.InlineKeyboardButton(text="🔐 Изменить аккаунт", callback_data="edit_account"),
            types.InlineKeyboardButton(text="🎮 Изменить консоль", callback_data="edit_console"),
        ],
        [
            types.InlineKeyboardButton(text="🌍 Изменить регион", callback_data="edit_region"),
            types.InlineKeyboardButton(text="🖼 Изменить резерв коды", callback_data="edit_reserve"),
        ],
        [
            types.InlineKeyboardButton(text="💳 Изменить подписку", callback_data="edit_subscription"),
            types.InlineKeyboardButton(text="🎲 Изменить игры", callback_data="edit_games"),
        ],
        [
            types.InlineKeyboardButton(text="✅ Сохранить", callback_data="save_changes"),
        ]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)

def format_client_info(client):
    number = client.get("number") or client.get("telegram") or ""
    birth = client.get("birthdate", "отсутствует")
    console = client.get("console", "")
    if console:
        main_row = f"{number} | {birth} ({console})"
    else:
        main_row = f"{number} | {birth}"
    acc = client.get("account", "")
    acc_mail = client.get("mailpass", "")
    region = client.get("region", "отсутствует")
    subs = client.get("subscriptions", [])
    games = client.get("games", [])
    msg = f"👤 {main_row}\n"
    msg += f"🔐 {acc}\n"
    if acc_mail:
        msg += f"✉️ Почта-пароль: {acc_mail}\n"
    if subs and subs[0].get("name") != "отсутствует":
        for s in subs:
            msg += f"\n💳 {s['name']} {s['term']}\n📅 {s['start']} → {s['end']}\n"
    else:
        msg += "\n💳 Подписки: (отсутствует)\n"
    msg += f"\n🌍 Регион: ({region})\n"
    if games:
        msg += "\n🎲 Игры:\n" + "\n".join([f"• {g}" for g in games])
    return msg

async def show_client_card(chat_id, client):
    text = format_client_info(client)
    reserve_id = client.get("reserve_photo_id")
    if reserve_id:
        msg = await bot.send_photo(chat_id, reserve_id, caption=text, reply_markup=get_edit_kb())
    else:
        msg = await bot.send_message(chat_id, text, reply_markup=get_edit_kb())
    return msg

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Выберите действие:", reply_markup=get_main_menu())

@dp.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=get_main_menu())

@dp.message(F.text == "➕ Добавить клиента")
async def add_client(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddClient.step_1)
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_1)
async def step_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    number = message.text
    is_telegram = number.startswith("@")
    data = {"number": "", "telegram": ""}
    if is_telegram:
        data["telegram"] = number
    else:
        data["number"] = number
    await state.update_data(new_client=data)
    await state.set_state(AddClient.step_2)
    await message.answer("Шаг 2\nДата рождения:", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_2)
async def step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    if message.text.lower() == "нет":
        client = (await state.get_data())["new_client"]
        client["birthdate"] = "отсутствует"
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=get_cancel_kb())
    elif message.text.lower() == "да":
        await state.set_state(AddClient.step_2_date)
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_2_date)
async def step_2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y")
        client = (await state.get_data())["new_client"]
        client["birthdate"] = message.text
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=get_cancel_kb())
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_3)
async def step_3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    lines = message.text.strip().split("\n")
    client = (await state.get_data())["new_client"]
    client["account"] = lines[0] if len(lines) > 0 else ""
    client["mailpass"] = lines[1] if len(lines) > 1 else ""
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_4)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=get_region_kb())

@dp.message(AddClient.step_4)
async def step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    client = (await state.get_data())["new_client"]
    client["region"] = message.text
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_4_console)
    await message.answer("Какая консоль?", reply_markup=get_console_kb())

@dp.message(AddClient.step_4_console)
async def step_4_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    client = (await state.get_data())["new_client"]
    client["console"] = message.text
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_5)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=get_yesno_kb())

# Дальнейшая часть — полностью как в твоем рабочем коде, начиная с шага подписок (AddClient.step_5) и далее!
# Просто скопируй с прошлой актуальной версии (подписки, игры, резерв, поиск, редактирование, обработчики, сохранение и т.д.).

# Пример: если нужно — вышлю всю часть ниже по запросу "далее" или "добавь всё до конца".
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))

@dp.message(AddClient.step_5)
async def step_5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    if message.text.lower() == "нет":
        client = (await state.get_data())["new_client"]
        client["subscriptions"] = [{"name": "отсутствует"}]
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())
    elif message.text.lower() == "да":
        await state.set_state(AddClient.step_5_main)
        kb = [
            [types.KeyboardButton(text="Одна"), types.KeyboardButton(text="Две")],
            [types.KeyboardButton(text="❌ Отмена")]
        ]
        await message.answer("Сколько подписок?", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(AddClient.step_5_main)
async def step_5_main(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    await state.update_data(sub_count=message.text)
    await state.set_state(AddClient.step_5_1_type)
    await message.answer("Выберите первую подписку:", reply_markup=get_subscription_type_kb())

@dp.message(AddClient.step_5_1_type)
async def step_5_1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    await state.update_data(sub_1_type=message.text)
    await state.set_state(AddClient.step_5_1_term)
    await message.answer("Срок первой подписки:", reply_markup=get_subscription_term_kb(message.text))

@dp.message(AddClient.step_5_1_term)
async def step_5_1_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    await state.update_data(sub_1_term=message.text)
    await state.set_state(AddClient.step_5_1_date)
    await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_5_1_date)
async def step_5_1_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата! Введите в формате дд.мм.гггг", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    sub_count = data.get("sub_count")
    sub_1_type = data.get("sub_1_type")
    sub_1_term = data.get("sub_1_term")
    sub_1_start = message.text
    term_months = int(sub_1_term.replace("м", ""))
    dt_end = (dt + timedelta(days=30*term_months)).strftime("%d.%m.%Y")
    subscriptions = [{
        "name": sub_1_type,
        "term": sub_1_term,
        "start": sub_1_start,
        "end": dt_end
    }]
    await state.update_data(subscriptions=subscriptions)
    if sub_count == "Две":
        if "EA Play" in sub_1_type:
            kb = [
                [types.KeyboardButton(text="PS Plus Deluxe"), types.KeyboardButton(text="PS Plus Extra")],
                [types.KeyboardButton(text="PS Plus Essential")],
                [types.KeyboardButton(text="❌ Отмена")]
            ]
        else:
            kb = [
                [types.KeyboardButton(text="EA Play")],
                [types.KeyboardButton(text="❌ Отмена")]
            ]
        await state.set_state(AddClient.step_5_2_type)
        await message.answer("Выберите вторую подписку:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    else:
        client = (await state.get_data())["new_client"]
        client["subscriptions"] = subscriptions
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_5_2_type)
async def step_5_2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    await state.update_data(sub_2_type=message.text)
    await state.set_state(AddClient.step_5_2_term)
    await message.answer("Срок второй подписки:", reply_markup=get_subscription_term_kb(message.text))

@dp.message(AddClient.step_5_2_term)
async def step_5_2_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    await state.update_data(sub_2_term=message.text)
    await state.set_state(AddClient.step_5_2_date)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_5_2_date)
async def step_5_2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата! Введите в формате дд.мм.гггг", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    sub_2_type = data.get("sub_2_type")
    sub_2_term = data.get("sub_2_term")
    sub_2_start = message.text
    term_months = int(sub_2_term.replace("м", ""))
    dt_end = (dt + timedelta(days=30*term_months)).strftime("%d.%m.%Y")
    subscriptions = data.get("subscriptions")
    subscriptions.append({
        "name": sub_2_type,
        "term": sub_2_term,
        "start": sub_2_start,
        "end": dt_end
    })
    client = data["new_client"]
    client["subscriptions"] = subscriptions
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_6)
async def step_6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    if message.text.lower() == "нет":
        client = (await state.get_data())["new_client"]
        client["games"] = []
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yesno_kb())
    elif message.text.lower() == "да":
        await state.set_state(AddClient.step_6_games)
        await message.answer("Напиши список игр (каждая с новой строки):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_6_games)
async def step_6_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    client = (await state.get_data())["new_client"]
    client["games"] = games
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_7)
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_7)
async def step_7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    if message.text.lower() == "нет":
        client = (await state.get_data())["new_client"]
        client["reserve_photo_id"] = None
        add_client_to_db(client)
        await show_client_card(message.chat.id, client)
    elif message.text.lower() == "да":
        await state.set_state(AddClient.step_7_photo)
        await message.answer("Загрузите скриншот с резервными кодами (одно фото):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_7_photo, F.photo)
async def step_7_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    client = (await state.get_data())["new_client"]
    client["reserve_photo_id"] = photo_id
    add_client_to_db(client)
    await show_client_card(message.chat.id, client)

@dp.message(AddClient.step_7_photo)
async def step_7_photo_text(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
    else:
        await message.answer("Пожалуйста, отправьте именно фото или нажмите Отмена.", reply_markup=get_cancel_kb())

@dp.message(F.text == "🔍 Найти клиента")
async def search_client(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddClient.searching)
    await message.answer("Введите номер телефона или Telegram клиента для поиска:", reply_markup=get_cancel_kb())

@dp.message(AddClient.searching)
async def searching(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    idx, client = find_client(message.text)
    if client:
        await state.update_data(found_index=idx)
        await show_client_card(message.chat.id, client)
        await state.update_data(client_edit=client)
    else:
        await message.answer("Клиент не найден.", reply_markup=get_main_menu())

# ----- Блок редактирования -----
@dp.callback_query(F.data.startswith("edit_"))
async def edit_handler(callback: types.CallbackQuery, state: FSMContext):
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        await state.update_data(client_edit=clients[idx])
    if callback.data == "edit_number":
        await state.set_state(AddClient.editing_number)
        await bot.send_message(callback.message.chat.id, "Введите новый номер или Telegram:", reply_markup=get_cancel_kb())
    elif callback.data == "edit_birth":
        await state.set_state(AddClient.editing_birth)
        await bot.send_message(callback.message.chat.id, "Введите новую дату рождения:", reply_markup=get_cancel_kb())
    elif callback.data == "edit_account":
        await state.set_state(AddClient.editing_account)
        await bot.send_message(callback.message.chat.id, "Введите новые данные аккаунта (логин, пароль, почта-пароль):", reply_markup=get_cancel_kb())
    elif callback.data == "edit_console":
        await state.set_state(AddClient.editing_console)
        await bot.send_message(callback.message.chat.id, "Выберите консоль:", reply_markup=get_console_kb())
    elif callback.data == "edit_region":
        await state.set_state(AddClient.editing_region)
        await bot.send_message(callback.message.chat.id, "Выберите регион:", reply_markup=get_region_kb())
    elif callback.data == "edit_reserve":
        await state.set_state(AddClient.editing_reserve)
        await bot.send_message(callback.message.chat.id, "Загрузите новые коды:", reply_markup=get_cancel_kb())
    elif callback.data == "edit_subscription":
        await state.set_state(AddClient.editing_subscription)
        await bot.send_message(callback.message.chat.id, "Измените подписки через пошаговый мастер. Начать?", reply_markup=get_yesno_kb())
    elif callback.data == "edit_games":
        await state.set_state(AddClient.editing_games)
        idx = (await state.get_data()).get("found_index")
        games_list = ""
        if idx is not None:
            clients = load_db()
            if 0 <= idx < len(clients):
                if clients[idx]["games"]:
                    games_list = "\n".join(clients[idx]["games"])
        await bot.send_message(callback.message.chat.id, "Отправьте новый список игр (каждая с новой строки):\n" + (games_list if games_list else ""), reply_markup=get_cancel_kb())
    elif callback.data == "save_changes":
        data = await state.get_data()
        idx = data.get("found_index")
        client = data.get("client_edit")
        if idx is not None and client:
            update_client_in_db(idx, client)
        msg = await bot.send_message(callback.message.chat.id, f"✅ {client.get('number') or client.get('telegram')} успешно сохранён", reply_markup=get_main_menu())
        await asyncio.sleep(10)
        await bot.delete_message(callback.message.chat.id, msg.message_id)

@dp.message(AddClient.editing_number)
async def editing_number(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        if message.text.startswith("@"):
            clients[idx]["number"] = ""
            clients[idx]["telegram"] = message.text
        else:
            clients[idx]["number"] = message.text
            clients[idx]["telegram"] = ""
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

@dp.message(AddClient.editing_birth)
async def editing_birth(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        try:
            dt = datetime.strptime(message.text, "%d.%m.%Y")
            clients[idx]["birthdate"] = message.text
        except:
            await message.answer("Некорректная дата!", reply_markup=get_cancel_kb())
            return
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

@dp.message(AddClient.editing_account)
async def editing_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    lines = message.text.strip().split("\n")
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        clients[idx]["account"] = lines[0] if len(lines) > 0 else ""
        clients[idx]["mailpass"] = lines[1] if len(lines) > 1 else ""
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

@dp.message(AddClient.editing_console)
async def editing_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        clients[idx]["console"] = message.text
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

@dp.message(AddClient.editing_region)
async def editing_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        clients[idx]["region"] = message.text
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

@dp.message(AddClient.editing_reserve, F.photo)
async def editing_reserve_photo(message: types.Message, state: FSMContext):
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        photo_id = message.photo[-1].file_id
        clients[idx]["reserve_photo_id"] = photo_id
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

@dp.message(AddClient.editing_reserve)
async def editing_reserve_text(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
    else:
        await message.answer("Пожалуйста, отправьте именно фото или нажмите Отмена.", reply_markup=get_cancel_kb())

@dp.message(AddClient.editing_games)
async def editing_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_handler(message, state)
        return
    idx = (await state.get_data()).get("found_index")
    clients = load_db()
    if idx is not None and 0 <= idx < len(clients):
        games = [g.strip() for g in message.text.split("\n") if g.strip()]
        clients[idx]["games"] = games
        update_client_in_db(idx, clients[idx])
        await show_client_card(message.chat.id, clients[idx])

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
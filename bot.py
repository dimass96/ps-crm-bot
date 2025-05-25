import logging
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import asyncio

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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
                text += f"Подписка: {s['name']} {s['term']} ({region}) с {s['start']} по {s['end']}\n"
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

class ClientForm(StatesGroup):
    choosing_action = State()
    number = State()
    birth_ask = State()
    birthdate = State()
    account = State()
    region = State()
    subscription = State()
    subscription_count = State()
    sub1_type = State()
    sub1_term = State()
    sub1_date = State()
    sub2_type = State()
    sub2_term = State()
    sub2_date = State()
    games_ask = State()
    games = State()
    codes_ask = State()
    codes = State()
    finish = State()
    edit_choice = State()
    edit_number = State()
    edit_birthdate = State()
    edit_account = State()
    edit_region = State()
    edit_codes = State()
    edit_subs = State()
    edit_games = State()
    confirming = State()

main_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_kb.add(KeyboardButton("+ Добавить клиента"))
main_menu_kb.add(KeyboardButton("🔍 Найти клиента"))

def yes_no_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def region_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("укр"), KeyboardButton("тур"), KeyboardButton("другой"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def edit_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("📱 Изменить номер-TG"),
        KeyboardButton("📅 Изменить дату рождения")
    )
    kb.add(
        KeyboardButton("🔐 Изменить аккаунт"),
        KeyboardButton("🌍 Изменить регион")
    )
    kb.add(
        KeyboardButton("🖼 Изменить резерв коды"),
        KeyboardButton("💳 Изменить подписку")
    )
    kb.add(
        KeyboardButton("🎮 Изменить игры"),
        KeyboardButton("✅ Сохранить")
    )
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_count_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("Одна"), KeyboardButton("Две"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_type_kb(exclude=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = []
    if not exclude or exclude != "PS Plus":
        buttons.append(KeyboardButton("PS Plus Deluxe"))
        buttons.append(KeyboardButton("PS Plus Extra"))
        buttons.append(KeyboardButton("PS Plus Essential"))
    if not exclude or exclude != "EA Play":
        buttons.append(KeyboardButton("EA Play"))
    kb.add(*buttons)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_term_kb(sub_type):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if "PS Plus" in sub_type:
        kb.add(KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м"))
    else:
        kb.add(KeyboardButton("1м"), KeyboardButton("12м"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def games_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

async def clear_chat(chat_id, state):
    return

def format_client_info(client):
    s = ""
    number = client.get("number") or client.get("telegram") or ""
    birth = client.get("birthdate", "")
    s += f"<b>👤 {number}</b>"
    if birth:
        s += f" | {birth}"
    s += "\n"
    acc = client.get("account", "")
    mail = client.get("mailpass", "")
    if acc:
        s += f"🔐 {acc}\n"
    if mail:
        s += f"✉️ Почта-пароль: {mail}\n"
    subs = client.get("subscriptions", [])
    for sub in subs:
        if sub.get("name") != "отсутствует":
            s += f"\n📅 {sub['name']} {sub['term']}\n<pre>{sub['start']} → {sub['end']}</pre>"
    if subs and subs[0].get("name") == "отсутствует":
        s += "\n📅 Подписки: (отсутствует)"
    region = client.get("region", "")
    if region:
        s += f"\n\n🌍 Регион: ({region})"
    games = client.get("games", [])
    if games:
        s += "\n🎮 Игры:"
        for g in games:
            s += f"\n• {g}"
    return s

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=main_menu_kb)
    await state.set_state(ClientForm.choosing_action)

@dp.message(F.text == "+ Добавить клиента")
async def start_add_client(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ClientForm.number)

@dp.message(ClientForm.number)
async def step_number(message: types.Message, state: FSMContext):
    value = message.text.strip()
    if value.startswith("@"):
        await state.update_data(telegram=value)
        await state.update_data(number="")
    else:
        await state.update_data(number=value)
        await state.update_data(telegram="")
    await message.answer("Шаг 2\nДата рождения:\nВыберите Есть или Нету.", reply_markup=yes_no_kb())
    await state.set_state(ClientForm.birth_ask)

@dp.message(ClientForm.birth_ask)
async def step_birth_ask(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(ClientForm.birthdate)
    elif message.text == "Нет":
        await state.update_data(birthdate="")
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(ClientForm.account)
    elif message.text == "❌ Отмена":
        await cmd_start(message, state)

@dp.message(ClientForm.birthdate)
async def step_birthdate(message: types.Message, state: FSMContext):
    value = message.text.strip()
    await state.update_data(birthdate=value)
    await message.answer("Шаг 3\nДанные от аккаунта:")
    await state.set_state(ClientForm.account)

@dp.message(ClientForm.account)
async def step_account(message: types.Message, state: FSMContext):
    lines = message.text.strip().split("\n")
    acc = lines[0] if len(lines) > 0 else ""
    mailpass = lines[1] if len(lines) > 1 else ""
    await state.update_data(account=acc)
    await state.update_data(mailpass=mailpass)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb())
    await state.set_state(ClientForm.region)

@dp.message(ClientForm.region)
async def step_region(message: types.Message, state: FSMContext):
    reg = message.text.strip()
    await state.update_data(region=reg)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())
    await state.set_state(ClientForm.subscription)

@dp.message(ClientForm.subscription)
async def step_subscription(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Сколько подписок оформлено?", reply_markup=sub_count_kb())
        await state.set_state(ClientForm.subscription_count)
    elif message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=games_kb())
        await state.set_state(ClientForm.games_ask)
    elif message.text == "❌ Отмена":
        await cmd_start(message, state)

@dp.message(ClientForm.subscription_count)
async def step_subscription_count(message: types.Message, state: FSMContext):
    if message.text == "Одна":
        await message.answer("Выберите подписку:", reply_markup=sub_type_kb())
        await state.set_state(ClientForm.sub1_type)
    elif message.text == "Две":
        await message.answer("Выберите первую подписку:", reply_markup=sub_type_kb())
        await state.set_state(ClientForm.sub1_type)
    elif message.text == "❌ Отмена":
        await cmd_start(message, state)

@dp.message(ClientForm.sub1_type)
async def step_sub1_type(message: types.Message, state: FSMContext):
    await state.update_data(sub1_type=message.text)
    await message.answer("Выберите срок:", reply_markup=sub_term_kb(message.text))
    await state.set_state(ClientForm.sub1_term)

@dp.message(ClientForm.sub1_term)
async def step_sub1_term(message: types.Message, state: FSMContext):
    await state.update_data(sub1_term=message.text)
    await message.answer("Дата оформления подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ClientForm.sub1_date)

@dp.message(ClientForm.sub1_date)
async def step_sub1_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(sub1_date=message.text)
    if data.get("subscription_count") == "Одна":
        subs = [{
            "name": data.get("sub1_type"),
            "term": data.get("sub1_term"),
            "start": data.get("sub1_date"),
            "end": "рассчитай сам"
        }]
        await state.update_data(subscriptions=subs)
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=games_kb())
        await state.set_state(ClientForm.games_ask)
    else:
        exclude = "EA Play" if "PS Plus" in data.get("sub1_type", "") else "PS Plus"
        await message.answer("Выберите вторую подписку:", reply_markup=sub_type_kb(exclude=exclude))
        await state.set_state(ClientForm.sub2_type)

@dp.message(ClientForm.sub2_type)
async def step_sub2_type(message: types.Message, state: FSMContext):
    await state.update_data(sub2_type=message.text)
    await message.answer("Выберите срок:", reply_markup=sub_term_kb(message.text))
    await state.set_state(ClientForm.sub2_term)

@dp.message(ClientForm.sub2_term)
async def step_sub2_term(message: types.Message, state: FSMContext):
    await state.update_data(sub2_term=message.text)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ClientForm.sub2_date)

@dp.message(ClientForm.sub2_date)
async def step_sub2_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subs = [
        {
            "name": data.get("sub1_type"),
            "term": data.get("sub1_term"),
            "start": data.get("sub1_date"),
            "end": "рассчитай сам"
        },
        {
            "name": data.get("sub2_type"),
            "term": data.get("sub2_term"),
            "start": message.text,
            "end": "рассчитай сам"
        }
    ]
    await state.update_data(subscriptions=subs)
    await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=games_kb())
    await state.set_state(ClientForm.games_ask)

@dp.message(ClientForm.games_ask)
async def step_games_ask(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Введите список игр, каждая на новой строке:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(ClientForm.games)
    elif message.text == "Нет":
        await state.update_data(games=[])
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
        await state.set_state(ClientForm.codes_ask)
    elif message.text == "❌ Отмена":
        await cmd_start(message, state)

@dp.message(ClientForm.games)
async def step_games(message: types.Message, state: FSMContext):
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    await state.update_data(games=games)
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
    await state.set_state(ClientForm.codes_ask)

@dp.message(ClientForm.codes_ask)
async def step_codes_ask(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(ClientForm.codes)
    elif message.text == "Нет":
        await state.update_data(codes_photo=None)
        client = await state.get_data()
        add_client_to_db(client)
        msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
        await state.update_data(client_msg=msg.message_id)
        await state.set_state(ClientForm.edit_choice)
    elif message.text == "❌ Отмена":
        await cmd_start(message, state)

@dp.message(ClientForm.codes, F.photo)
async def step_codes_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(codes_photo=photo_id)
    client = await state.get_data()
    add_client_to_db(client)
    if photo_id:
        msg = await message.answer_photo(photo_id, caption=format_client_info(client), reply_markup=edit_kb())
    else:
        msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

@dp.message(ClientForm.codes)
async def codes_invalid(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте скриншот резервных кодов.")

@dp.message(ClientForm.edit_choice)
async def edit_panel(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data
    if message.text == "📱 Изменить номер-TG":
        await message.answer("Введите новый номер или Telegram:")
        await state.set_state(ClientForm.edit_number)
    elif message.text == "📅 Изменить дату рождения":
        await message.answer("Введите новую дату рождения:")
        await state.set_state(ClientForm.edit_birthdate)
    elif message.text == "🔐 Изменить аккаунт":
        await message.answer("Введите новые данные аккаунта (логин/пароль, почта через enter):")
        await state.set_state(ClientForm.edit_account)
    elif message.text == "🌍 Изменить регион":
        await message.answer("Выберите новый регион:", reply_markup=region_kb())
        await state.set_state(ClientForm.edit_region)
    elif message.text == "🖼 Изменить резерв коды":
        await message.answer("Загрузите новый скриншот резервных кодов:")
        await state.set_state(ClientForm.edit_codes)
    elif message.text == "💳 Изменить подписку":
        await message.answer("Сколько подписок оформлено?", reply_markup=sub_count_kb())
        await state.set_state(ClientForm.subscription_count)
    elif message.text == "🎮 Изменить игры":
        old_games = "\n".join(client.get("games", [])) if client.get("games") else ""
        await message.answer(f"Текущий список игр:\n{old_games}\n\nВведите новый список игр (каждая с новой строки):")
        await state.set_state(ClientForm.edit_games)
    elif message.text == "✅ Сохранить":
        client = await state.get_data()
        update_client_in_db(client)
        identifier = client.get("number") or client.get("telegram")
        await message.answer(f"✅ {identifier} успешно сохранён!", reply_markup=main_menu_kb)
        await state.clear()
    elif message.text == "❌ Отмена":
        await cmd_start(message, state)

@dp.message(ClientForm.edit_number)
async def process_edit_number(message: types.Message, state: FSMContext):
    val = message.text.strip()
    if val.startswith("@"):
        await state.update_data(telegram=val, number="")
    else:
        await state.update_data(number=val, telegram="")
    client = await state.get_data()
    msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

@dp.message(ClientForm.edit_birthdate)
async def process_edit_birthdate(message: types.Message, state: FSMContext):
    await state.update_data(birthdate=message.text.strip())
    client = await state.get_data()
    msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

@dp.message(ClientForm.edit_account)
async def process_edit_account(message: types.Message, state: FSMContext):
    lines = message.text.strip().split("\n")
    acc = lines[0] if len(lines) > 0 else ""
    mailpass = lines[1] if len(lines) > 1 else ""
    await state.update_data(account=acc, mailpass=mailpass)
    client = await state.get_data()
    msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

@dp.message(ClientForm.edit_region)
async def process_edit_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text.strip())
    client = await state.get_data()
    msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

@dp.message(ClientForm.edit_codes, F.photo)
async def process_edit_codes(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(codes_photo=photo_id)
    client = await state.get_data()
    msg = await message.answer_photo(photo_id, caption=format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

@dp.message(ClientForm.edit_codes)
async def codes_invalid_edit(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте новый скриншот резервных кодов.")

@dp.message(ClientForm.edit_games)
async def process_edit_games(message: types.Message, state: FSMContext):
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    await state.update_data(games=games)
    client = await state.get_data()
    msg = await message.answer(format_client_info(client), reply_markup=edit_kb())
    await state.update_data(client_msg=msg.message_id)
    await state.set_state(ClientForm.edit_choice)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
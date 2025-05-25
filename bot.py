import logging
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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
    async with state.proxy() as data:
        pass
    # Тут ты можешь реализовать свою функцию очистки, например, удаляя последние 100 сообщений

@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Выберите действие:", reply_markup=main_menu_kb)
    await ClientForm.choosing_action.set()

@dp.message_handler(lambda m: m.text == "+ Добавить клиента", state=ClientForm.choosing_action)
async def step_number(message: types.Message, state: FSMContext):
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=ReplyKeyboardRemove())
    await ClientForm.number.set()

@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_chat(message.chat.id, state)
    await message.answer("Действие отменено.", reply_markup=main_menu_kb)
    await ClientForm.choosing_action.set()

@dp.message_handler(state=ClientForm.number)
async def step_birth_ask(message: types.Message, state: FSMContext):
    value = message.text.strip()
    if value.startswith("@"):
        await state.update_data(telegram=value)
        await state.update_data(number="")
    else:
        await state.update_data(number=value)
        await state.update_data(telegram="")
    await message.answer("Шаг 2\nДата рождения:\n\nВыберите Есть или Нету.", reply_markup=yes_no_kb())
    await ClientForm.birth_ask.set()

@dp.message_handler(lambda m: m.text in ["Есть", "Нету"], state=ClientForm.birth_ask)
async def step_birthdate(message: types.Message, state: FSMContext):
    if message.text == "Есть":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
        await ClientForm.birthdate.set()
    else:
        await state.update_data(birthdate="отсутствует")
        await step_account(message, state)

@dp.message_handler(state=ClientForm.birthdate)
async def step_account(message: types.Message, state: FSMContext):
    date = message.text.strip()
    await state.update_data(birthdate=date)
    await message.answer("Шаг 3\nДанные от аккаунта:")
    await ClientForm.account.set()

@dp.message_handler(state=ClientForm.account)
async def step_region(message: types.Message, state: FSMContext):
    account_data = message.text.strip().split('\n')
    mail, passw, mailpass = "", "", ""
    if len(account_data) > 0:
        mail = account_data[0]
    if len(account_data) > 1:
        passw = account_data[1]
    if len(account_data) > 2:
        mailpass = account_data[2]
    await state.update_data(account=mail + " ; " + passw, mailpass=mailpass)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb())
    await ClientForm.region.set()

@dp.message_handler(state=ClientForm.region)
async def step_subscription(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text.strip())
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())
    await ClientForm.subscription.set()

@dp.message_handler(lambda m: m.text == "Нет", state=ClientForm.subscription)
async def step_games_ask_skip_sub(message: types.Message, state: FSMContext):
    await state.update_data(subscriptions=[{"name": "отсутствует"}])
    await step_games_ask(message, state)

@dp.message_handler(lambda m: m.text == "Да", state=ClientForm.subscription)
async def step_subscription_count(message: types.Message, state: FSMContext):
    await message.answer("Сколько подписок оформлено?", reply_markup=sub_count_kb())
    await ClientForm.subscription_count.set()

@dp.message_handler(lambda m: m.text in ["Одна", "Две"], state=ClientForm.subscription_count)
async def step_sub1_type(message: types.Message, state: FSMContext):
    await state.update_data(subscription_count=message.text)
    await message.answer("Выберите первую подписку:", reply_markup=sub_type_kb())
    await ClientForm.sub1_type.set()

@dp.message_handler(lambda m: m.text in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"], state=ClientForm.sub1_type)
async def step_sub1_term(message: types.Message, state: FSMContext):
    await state.update_data(sub1_type=message.text)
    await message.answer("Срок первой подписки?", reply_markup=sub_term_kb(message.text))
    await ClientForm.sub1_term.set()

@dp.message_handler(lambda m: m.text in ["1м", "3м", "12м"], state=ClientForm.sub1_term)
async def step_sub1_date(message: types.Message, state: FSMContext):
    await state.update_data(sub1_term=message.text)
    await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
    await ClientForm.sub1_date.set()

@dp.message_handler(state=ClientForm.sub1_date)
async def step_sub2_type(message: types.Message, state: FSMContext):
    await state.update_data(sub1_date=message.text.strip())
    data = await state.get_data()
    if data.get("subscription_count") == "Две":
        prev_type = data.get("sub1_type")
        exclude = "EA Play" if "PS Plus" in prev_type else "PS Plus"
        await message.answer("Выберите вторую подписку:", reply_markup=sub_type_kb(exclude=exclude))
        await ClientForm.sub2_type.set()
    else:
        await finalize_subs(state)
        await step_games_ask(message, state)

@dp.message_handler(lambda m: m.text in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"], state=ClientForm.sub2_type)
async def step_sub2_term(message: types.Message, state: FSMContext):
    await state.update_data(sub2_type=message.text)
    await message.answer("Срок второй подписки?", reply_markup=sub_term_kb(message.text))
    await ClientForm.sub2_term.set()

@dp.message_handler(lambda m: m.text in ["1м", "3м", "12м"], state=ClientForm.sub2_term)
async def step_sub2_date(message: types.Message, state: FSMContext):
    await state.update_data(sub2_term=message.text)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
    await ClientForm.sub2_date.set()

@dp.message_handler(state=ClientForm.sub2_date)
async def finalize_subs_handler(message: types.Message, state: FSMContext):
    await state.update_data(sub2_date=message.text.strip())
    await finalize_subs(state)
    await step_games_ask(message, state)

async def finalize_subs(state):
    data = await state.get_data()
    region = data.get("region", "")
    subs = []
    def calc_end(start, term):
        from datetime import datetime, timedelta
        d = datetime.strptime(start, "%d.%m.%Y")
        months = int(term.replace("м", ""))
        y, m = d.year, d.month + months
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        try:
            res = d.replace(year=y, month=m)
        except ValueError:
            res = d.replace(year=y, month=m, day=28)
        return res.strftime("%d.%m.%Y")
    if data.get("subscription_count") == "Две":
        sub1 = {
            "name": data["sub1_type"],
            "term": data["sub1_term"],
            "start": data["sub1_date"],
            "end": calc_end(data["sub1_date"], data["sub1_term"]),
            "region": region
        }
        sub2 = {
            "name": data["sub2_type"],
            "term": data["sub2_term"],
            "start": data["sub2_date"],
            "end": calc_end(data["sub2_date"], data["sub2_term"]),
            "region": region
        }
        subs = [sub1, sub2]
    else:
        sub1 = {
            "name": data["sub1_type"],
            "term": data["sub1_term"],
            "start": data["sub1_date"],
            "end": calc_end(data["sub1_date"], data["sub1_term"]),
            "region": region
        }
        subs = [sub1]
    await state.update_data(subscriptions=subs)

async def step_games_ask(message, state):
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=games_kb())
    await ClientForm.games_ask.set()

@dp.message_handler(lambda m: m.text == "Да", state=ClientForm.games_ask)
async def games_input(message: types.Message, state: FSMContext):
    await message.answer("Введите список игр, каждая на новой строке:", reply_markup=ReplyKeyboardRemove())
    await ClientForm.games.set()

@dp.message_handler(lambda m: m.text == "Нет", state=ClientForm.games_ask)
async def skip_games(message: types.Message, state: FSMContext):
    await state.update_data(games=[])
    await step_codes_ask(message, state)

@dp.message_handler(state=ClientForm.games)
async def games_save(message: types.Message, state: FSMContext):
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    await state.update_data(games=games)
    await step_codes_ask(message, state)

async def step_codes_ask(message, state):
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
    await ClientForm.codes_ask.set()

@dp.message_handler(lambda m: m.text == "Да", state=ClientForm.codes_ask)
async def codes_get(message: types.Message, state: FSMContext):
    await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=ReplyKeyboardRemove())
    await ClientForm.codes.set()

@dp.message_handler(lambda m: m.text == "Нет", state=ClientForm.codes_ask)
async def codes_skip(message: types.Message, state: FSMContext):
    await state.update_data(codes=None)
    await finish_add(message, state)

@dp.message_handler(content_types=types.ContentType.PHOTO, state=ClientForm.codes)
async def codes_save(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(codes=file_id)
    await finish_add(message, state)

async def finish_add(message, state):
    data = await state.get_data()
    number = data.get("number", "")
    telegram = data.get("telegram", "")
    birthdate = data.get("birthdate", "")
    account = data.get("account", "")
    mailpass = data.get("mailpass", "")
    region = data.get("region", "")
    subs = data.get("subscriptions", [])
    games = data.get("games", [])
    codes = data.get("codes", None)
    client = {
        "number": number,
        "telegram": telegram,
        "birthdate": birthdate,
        "account": account,
        "mailpass": mailpass,
        "region": region,
        "subscriptions": subs,
        "games": games,
        "codes": codes
    }
    update_client_in_db(client)
    await clear_chat(message.chat.id, state)
    msg = await send_full_info(message.chat.id, client)
    await state.update_data(current_client=client)
    await state.update_data(info_message_id=msg.message_id)
    await ClientForm.edit_choice.set()

async def send_full_info(chat_id, client):
    info = format_client_info(client)
    codes = client.get("codes")
    if codes:
        msg = await bot.send_photo(chat_id, codes, caption=info, reply_markup=edit_kb())
    else:
        msg = await bot.send_message(chat_id, info, reply_markup=edit_kb())
    return msg

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

@dp.message_handler(lambda m: m.text.startswith("📱 Изменить номер"), state=ClientForm.edit_choice)
async def edit_number_handler(message: types.Message, state: FSMContext):
    await message.answer("Введите новый номер или Telegram:")
    await ClientForm.edit_number.set()

@dp.message_handler(state=ClientForm.edit_number)
async def save_edit_number(message: types.Message, state: FSMContext):
    value = message.text.strip()
    data = await state.get_data()
    client = data.get("current_client", {})
    if value.startswith("@"):
        client["telegram"] = value
        client["number"] = ""
    else:
        client["number"] = value
        client["telegram"] = ""
    await state.update_data(current_client=client)
    update_client_in_db(client)
    await refresh_edit_block(message, state)

@dp.message_handler(lambda m: m.text.startswith("📅 Изменить дату"), state=ClientForm.edit_choice)
async def edit_birthdate_handler(message: types.Message, state: FSMContext):
    await message.answer("Введите новую дату рождения:")
    await ClientForm.edit_birthdate.set()

@dp.message_handler(state=ClientForm.edit_birthdate)
async def save_edit_birthdate(message: types.Message, state: FSMContext):
    value = message.text.strip()
    data = await state.get_data()
    client = data.get("current_client", {})
    client["birthdate"] = value
    await state.update_data(current_client=client)
    update_client_in_db(client)
    await refresh_edit_block(message, state)

@dp.message_handler(lambda m: m.text.startswith("🔐 Изменить аккаунт"), state=ClientForm.edit_choice)
async def edit_account_handler(message: types.Message, state: FSMContext):
    await message.answer("Введите новые данные аккаунта (логин, пароль, почта-пароль):")
    await ClientForm.edit_account.set()

@dp.message_handler(state=ClientForm.edit_account)
async def save_edit_account(message: types.Message, state: FSMContext):
    account_data = message.text.strip().split('\n')
    mail, passw, mailpass = "", "", ""
    if len(account_data) > 0:
        mail = account_data[0]
    if len(account_data) > 1:
        passw = account_data[1]
    if len(account_data) > 2:
        mailpass = account_data[2]
    value = mail + " ; " + passw
    data = await state.get_data()
    client = data.get("current_client", {})
    client["account"] = value
    client["mailpass"] = mailpass
    await state.update_data(current_client=client)
    update_client_in_db(client)
    await refresh_edit_block(message, state)

@dp.message_handler(lambda m: m.text.startswith("🌍 Изменить регион"), state=ClientForm.edit_choice)
async def edit_region_handler(message: types.Message, state: FSMContext):
    await message.answer("Выберите регион:", reply_markup=region_kb())
    await ClientForm.edit_region.set()

@dp.message_handler(state=ClientForm.edit_region)
async def save_edit_region(message: types.Message, state: FSMContext):
    region = message.text.strip()
    data = await state.get_data()
    client = data.get("current_client", {})
    client["region"] = region
    await state.update_data(current_client=client)
    update_client_in_db(client)
    await refresh_edit_block(message, state)

@dp.message_handler(lambda m: m.text.startswith("🖼 Изменить резерв"), state=ClientForm.edit_choice)
async def edit_codes_handler(message: types.Message, state: FSMContext):
    await message.answer("Загрузите новые коды:")
    await ClientForm.edit_codes.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=ClientForm.edit_codes)
async def save_edit_codes(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    client = data.get("current_client", {})
    client["codes"] = file_id
    await state.update_data(current_client=client)
    update_client_in_db(client)
    await refresh_edit_block(message, state)

@dp.message_handler(lambda m: m.text.startswith("💳 Изменить подписку"), state=ClientForm.edit_choice)
async def edit_subs_handler(message: types.Message, state: FSMContext):
    await message.answer("Сколько подписок оформить?", reply_markup=sub_count_kb())
    await ClientForm.edit_subs.set()

@dp.message_handler(lambda m: m.text in ["Одна", "Две"], state=ClientForm.edit_subs)
async def edit_sub1_type(message: types.Message, state: FSMContext):
    await state.update_data(subscription_count=message.text)
    await message.answer("Выберите первую подписку:", reply_markup=sub_type_kb())
    await ClientForm.sub1_type.set()

@dp.message_handler(lambda m: m.text.startswith("🎮 Изменить игры"), state=ClientForm.edit_choice)
async def edit_games_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("current_client", {})
    current_games = client.get("games", [])
    games_text = "\n".join(current_games) if current_games else ""
    await message.answer(f"Текущий список игр:\n{games_text}\n\nВведите новый список игр, каждая на новой строке:")
    await ClientForm.edit_games.set()

@dp.message_handler(state=ClientForm.edit_games)
async def save_edit_games(message: types.Message, state: FSMContext):
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    data = await state.get_data()
    client = data.get("current_client", {})
    client["games"] = games
    await state.update_data(current_client=client)
    update_client_in_db(client)
    await refresh_edit_block(message, state)

@dp.message_handler(lambda m: m.text == "✅ Сохранить", state=ClientForm.edit_choice)
async def save_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("current_client", {})
    update_client_in_db(client)
    await clear_chat(message.chat.id, state)
    number = client.get("number") or client.get("telegram")
    await message.answer(f"✅ {number} успешно сохранён", reply_markup=main_menu_kb)
    await ClientForm.choosing_action.set()

async def refresh_edit_block(message, state):
    data = await state.get_data()
    client = data.get("current_client", {})
    info = format_client_info(client)
    codes = client.get("codes")
    msg_id = data.get("info_message_id")
    try:
        await bot.delete_message(message.chat.id, msg_id)
    except:
        pass
    if codes:
        msg = await bot.send_photo(message.chat.id, codes, caption=info, reply_markup=edit_kb())
    else:
        msg = await bot.send_message(message.chat.id, info, reply_markup=edit_kb())
    await state.update_data(info_message_id=msg.message_id)
    await ClientForm.edit_choice.set()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
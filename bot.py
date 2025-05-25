import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database import (
    load_db, save_db, add_client_to_db, update_client_in_db, find_client, find_client_partial,
    delete_client, export_all
)

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="🔎 Поиск")],
        [KeyboardButton(text="🧹 Очистить чат"), KeyboardButton(text="📤 Выгрузить базу")]
    ],
    resize_keyboard=True
)

def get_edit_inline_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Изменить номер/TG", callback_data="edit_number")],
        [InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birthdate")],
        [InlineKeyboardButton(text="🔑 Изменить аккаунт", callback_data="edit_account")],
        [InlineKeyboardButton(text="🌍 Изменить регион", callback_data="edit_region")],
        [InlineKeyboardButton(text="🗂 Изменить резерв коды", callback_data="edit_codes")],
        [InlineKeyboardButton(text="💳 Изменить подписку", callback_data="edit_subscription")],
        [InlineKeyboardButton(text="🎮 Изменить игры", callback_data="edit_games")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="save")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])
    return kb

def human_date(d):
    try:
        return datetime.strptime(d, "%d.%m.%Y").strftime("%d.%m.%Y")
    except:
        return d

class AddClient(StatesGroup):
    number = State()
    birth_question = State()
    birthdate = State()
    account = State()
    region = State()
    subscription_count = State()
    subscription_type_1 = State()
    subscription_term_1 = State()
    subscription_date_1 = State()
    subscription_type_2 = State()
    subscription_term_2 = State()
    subscription_date_2 = State()
    games_question = State()
    games = State()
    codes_question = State()
    codes = State()
    confirm = State()
    edit = State()
    edit_value = State()

async def delete_previous_bot_messages(state: FSMContext, bot, chat_id):
    data = await state.get_data()
    msg_ids = data.get("bot_message_ids", [])
    for msg_id in msg_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    await state.update_data(bot_message_ids=[])

async def send_and_store(state: FSMContext, bot, chat_id, text, reply_markup=None, photo=None, disable_web_page_preview=None):
    await delete_previous_bot_messages(state, bot, chat_id)
    if photo:
        m = await bot.send_photo(chat_id, photo, caption=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        m = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=disable_web_page_preview)
    await state.update_data(bot_message_ids=[m.message_id])
    return m

async def send_info_block(state: FSMContext, bot, chat_id, client, photo=None):
    subs = client.get("subscriptions", [])
    info = f"<b>Клиент</b>: {client.get('number', '') or client.get('telegram', '')}\n"
    info += f"<b>Дата рождения</b>: {client.get('birthdate', '(отсутствует)')}\n"
    acc = client.get('account', '')
    mailpass = client.get('mailpass', '')
    info += f"<b>Аккаунт</b>: {acc}\n"
    if mailpass:
        info += f"<b>Почта-пароль</b>: {mailpass}\n"
    info += f"<b>Регион</b>: {client.get('region', '(отсутствует)')}\n"
    if subs:
        for s in subs:
            info += f"<b>Подписка</b>: {s['name']} {s['term']} с {s['start']} по {s['end']}\n"
    else:
        info += "<b>Подписка</b>: (отсутствует)\n"
    games = client.get("games", [])
    info += f"<b>Игры</b>: " + (", ".join(games) if games else "(отсутствует)") + "\n"
    codes_id = client.get("codes_id")
    kb = get_edit_inline_kb()
    if codes_id:
        msg = await send_and_store(state, bot, chat_id, info, reply_markup=kb)
        await bot.send_photo(chat_id, codes_id, caption="Резерв коды", reply_to_message_id=msg.message_id)
        return msg
    else:
        return await send_and_store(state, bot, chat_id, info, reply_markup=kb)

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await message.answer("Главное меню", reply_markup=main_menu_kb)
    await state.clear()

@dp.message(F.text == "🧹 Очистить чат")
async def cmd_clear(message: types.Message, state: FSMContext):
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await message.answer("Чат очищен.", reply_markup=main_menu_kb)
    await state.clear()

@dp.message(F.text == "📤 Выгрузить базу")
async def cmd_export(message: types.Message, state: FSMContext):
    text = export_all()
    file = InputFile.from_file(BytesIO(text.encode("utf-8")), filename="clients_db.txt")
    await message.answer_document(file, caption="Выгрузка базы клиентов.", reply_markup=main_menu_kb)
    await state.clear()

@dp.message(F.text == "➕ Добавить")
async def start_add(message: types.Message, state: FSMContext):
    await state.clear()
    await send_and_store(state, bot, message.chat.id, "Введите номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.number)

@dp.message(F.text == "🔎 Поиск")
async def start_search(message: types.Message, state: FSMContext):
    await state.clear()
    await send_and_store(state, bot, message.chat.id, "Введите номер телефона или Telegram для поиска:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.edit)

@dp.message(AddClient.number)
async def add_number(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    number = message.text.strip()
    if number.startswith("@"):
        await state.update_data(telegram=number, number="")
    else:
        await state.update_data(number=number, telegram="")
    await send_and_store(state, bot, message.chat.id, "Есть дата рождения?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да")],[KeyboardButton(text="Нет")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.birth_question)

@dp.message(AddClient.birth_question)
async def birth_question(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    if message.text == "Да":
        await send_and_store(state, bot, message.chat.id, "Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClient.birthdate)
    else:
        await state.update_data(birthdate="(отсутствует)")
        await send_and_store(state, bot, message.chat.id, "Введите данные аккаунта (логин/пароль, почта):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClient.account)

@dp.message(AddClient.birthdate)
async def birthdate(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(birthdate=message.text.strip())
    await send_and_store(state, bot, message.chat.id, "Введите данные аккаунта (логин/пароль, почта):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.account)

@dp.message(AddClient.account)
async def account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    lines = message.text.split('\n')
    login = lines[0] if len(lines) > 0 else ''
    password = lines[1] if len(lines) > 1 else ''
    mail = lines[2] if len(lines) > 2 else ''
    acc_str = login
    if password:
        acc_str += f";{password}"
    await state.update_data(account=acc_str, mailpass=mail)
    await send_and_store(state, bot, message.chat.id, "Выберите регион аккаунта:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Укр")],[KeyboardButton(text="Тур")],[KeyboardButton(text="Другое")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.region)

@dp.message(AddClient.region)
async def region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(region=message.text.strip())
    await send_and_store(state, bot, message.chat.id, "Сколько подписок оформлено?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Одна")],[KeyboardButton(text="Две")],[KeyboardButton(text="Нет")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.subscription_count)

@dp.message(AddClient.subscription_count)
async def subscription_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    val = message.text.strip()
    if val == "Нет":
        await state.update_data(subscriptions=[])
        await send_and_store(state, bot, message.chat.id, "Есть оформленные игры?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да")],[KeyboardButton(text="Нет")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClient.games_question)
    elif val == "Одна":
        await send_and_store(state, bot, message.chat.id, "Выберите подписку:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="PS Plus Deluxe")],[KeyboardButton(text="PS Plus Extra")],[KeyboardButton(text="PS Plus Essential")],[KeyboardButton(text="EA Play")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(sub_count=1)
        await state.set_state(AddClient.subscription_type_1)
    elif val == "Две":
        await send_and_store(state, bot, message.chat.id, "Выберите первую подписку:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="PS Plus Deluxe")],[KeyboardButton(text="PS Plus Extra")],[KeyboardButton(text="PS Plus Essential")],[KeyboardButton(text="EA Play")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(sub_count=2)
        await state.set_state(AddClient.subscription_type_1)

@dp.message(AddClient.subscription_type_1)
async def subscription_type_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    s = message.text.strip()
    if s == "EA Play":
        await send_and_store(state, bot, message.chat.id, "Срок подписки:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1 мес")],[KeyboardButton(text="12 мес")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(subscription_type_1=s)
        await state.set_state(AddClient.subscription_term_1)
    else:
        await send_and_store(state, bot, message.chat.id, "Срок подписки:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1 мес")],[KeyboardButton(text="3 мес")],[KeyboardButton(text="12 мес")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(subscription_type_1=s)
        await state.set_state(AddClient.subscription_term_1)

@dp.message(AddClient.subscription_term_1)
async def subscription_term_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(subscription_term_1=message.text.strip())
    await send_and_store(state, bot, message.chat.id, "Дата оформления подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.subscription_date_1)

@dp.message(AddClient.subscription_date_1)
async def subscription_date_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(subscription_date_1=message.text.strip())
    data = await state.get_data()
    if data.get("sub_count") == 2:
        prev = data["subscription_type_1"]
        btns = []
        if prev == "EA Play":
            btns = ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]
        else:
            btns = ["EA Play"]
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=b)] for b in btns]+[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        await send_and_store(state, bot, message.chat.id, "Выберите вторую подписку:", reply_markup=kb)
        await state.set_state(AddClient.subscription_type_2)
    else:
        await collect_subscriptions_and_games(state, message)

@dp.message(AddClient.subscription_type_2)
async def subscription_type_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    s = message.text.strip()
    if s == "EA Play":
        await send_and_store(state, bot, message.chat.id, "Срок подписки:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1 мес")],[KeyboardButton(text="12 мес")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(subscription_type_2=s)
        await state.set_state(AddClient.subscription_term_2)
    else:
        await send_and_store(state, bot, message.chat.id, "Срок подписки:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1 мес")],[KeyboardButton(text="3 мес")],[KeyboardButton(text="12 мес")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(subscription_type_2=s)
        await state.set_state(AddClient.subscription_term_2)

@dp.message(AddClient.subscription_term_2)
async def subscription_term_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(subscription_term_2=message.text.strip())
    await send_and_store(state, bot, message.chat.id, "Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.subscription_date_2)

@dp.message(AddClient.subscription_date_2)
async def subscription_date_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(subscription_date_2=message.text.strip())
    await collect_subscriptions_and_games(state, message)

async def collect_subscriptions_and_games(state, message):
    data = await state.get_data()
    subs = []
    s1 = data.get("subscription_type_1")
    t1 = data.get("subscription_term_1")
    d1 = data.get("subscription_date_1")
    s2 = data.get("subscription_type_2")
    t2 = data.get("subscription_term_2")
    d2 = data.get("subscription_date_2")
    if s1 and t1 and d1:
        end1 = calc_end_date(d1, t1)
        subs.append({"name": s1, "term": t1, "start": d1, "end": end1})
    if s2 and t2 and d2:
        end2 = calc_end_date(d2, t2)
        subs.append({"name": s2, "term": t2, "start": d2, "end": end2})
    await state.update_data(subscriptions=subs)
    await send_and_store(state, bot, message.chat.id, "Есть оформленные игры?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да")],[KeyboardButton(text="Нет")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.games_question)

def calc_end_date(start, term):
    try:
        d = datetime.strptime(start, "%d.%m.%Y")
    except:
        d = datetime.today()
    if "12" in term:
        d = d + timedelta(days=365)
    elif "3" in term:
        d = d + timedelta(days=90)
    elif "1" in term:
        d = d + timedelta(days=30)
    return d.strftime("%d.%m.%Y")

@dp.message(AddClient.games_question)
async def games_question(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    if message.text == "Да":
        await send_and_store(state, bot, message.chat.id, "Введите список игр (каждая игра с новой строки):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClient.games)
    else:
        await state.update_data(games=[])
        await send_and_store(state, bot, message.chat.id, "Есть ли резервные коды?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да")],[KeyboardButton(text="Нет")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClient.codes_question)

@dp.message(AddClient.games)
async def games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    lines = [x.strip() for x in message.text.split("\n") if x.strip()]
    await state.update_data(games=lines)
    await send_and_store(state, bot, message.chat.id, "Есть ли резервные коды?", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Да")],[KeyboardButton(text="Нет")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClient.codes_question)

@dp.message(AddClient.codes_question)
async def codes_question(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    if message.text == "Да":
        await send_and_store(state, bot, message.chat.id, "Загрузите скриншот резервных кодов:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClient.codes)
    else:
        await finalize_add_client(state, message, None)

@dp.message(AddClient.codes, F.photo)
async def codes_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await finalize_add_client(state, message, file_id)

@dp.message(AddClient.codes)
async def codes_waiting_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await delete_previous_bot_messages(state, bot, message.chat.id)
        await message.answer("Добавление отменено.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await send_and_store(state, bot, message.chat.id, "Пожалуйста, загрузите фото резервных кодов либо нажмите '❌ Отмена'.", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

async def finalize_add_client(state: FSMContext, message: types.Message, codes_file_id):
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "(отсутствует)"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", "(отсутствует)"),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "codes_id": codes_file_id
    }
    add_client_to_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=codes_file_id)
    await state.clear()

async def send_info_block(state, bot, chat_id, client, photo=None):
    info_text = render_client_info(client)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить номер/TG", callback_data="edit_number")],
        [InlineKeyboardButton(text="Изменить дату рождения", callback_data="edit_birth")],
        [InlineKeyboardButton(text="Изменить аккаунт", callback_data="edit_account")],
        [InlineKeyboardButton(text="Изменить регион", callback_data="edit_region")],
        [InlineKeyboardButton(text="Изменить резерв коды", callback_data="edit_codes")],
        [InlineKeyboardButton(text="Изменить подписку", callback_data="edit_subscription")],
        [InlineKeyboardButton(text="Изменить игры", callback_data="edit_games")],
        [InlineKeyboardButton(text="Сохранить", callback_data="save_client")]
    ])
    if photo:
        await bot.send_photo(chat_id, photo, caption=info_text, reply_markup=kb)
    else:
        await bot.send_message(chat_id, info_text, reply_markup=kb, parse_mode="HTML")
    await state.update_data(last_info_block=True)

def render_client_info(client):
    lines = []
    number_line = client["number"] or client["telegram"]
    lines.append(f"🆔 <b>{number_line}</b>")
    lines.append(f"🎂 Дата рождения: <b>{client.get('birthdate','(отсутствует)')}</b>")
    acc = client.get("account","")
    if acc:
        lines.append(f"🔑 Данные аккаунта: <b>{acc}</b>")
    if client.get("mailpass"):
        lines.append(f"📧 Почта/Пароль: <b>{client['mailpass']}</b>")
    lines.append(f"🌎 Регион: <b>{client.get('region','(отсутствует)')}</b>")
    if client.get("subscriptions"):
        for sub in client["subscriptions"]:
            lines.append(f"💳 {sub['name']} {sub['term']} (с {sub['start']} до {sub['end']})")
    else:
        lines.append("💳 Подписки: <b>(отсутствует)</b>")
    if client.get("games"):
        games = "\n".join([f"🎮 {g}" for g in client["games"]])
        lines.append(f"Игры:\n{games}")
    else:
        lines.append("🎮 Игры: <b>(отсутствует)</b>")
    if client.get("codes_id"):
        lines.append("🟩 Резерв коды прикреплены ниже")
    else:
        lines.append("🟩 Резерв коды: <b>(отсутствует)</b>")
    return "\n".join(lines)

@dp.callback_query(F.data == "edit_number")
async def edit_number(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer("Введите новый номер или Telegram:")
    await state.set_state(EditClient.edit_number)

@dp.message(EditClient.edit_number)
async def edit_number_enter(message: types.Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    client = get_last_client(data)
    if val.startswith("@"):
        client["telegram"] = val
        client["number"] = ""
    else:
        client["number"] = val
        client["telegram"] = ""
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=client.get("codes_id"))
    await state.clear()

@dp.callback_query(F.data == "edit_birth")
async def edit_birth(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer("Введите новую дату рождения:")
    await state.set_state(EditClient.edit_birth)

@dp.message(EditClient.edit_birth)
async def edit_birth_enter(message: types.Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    client = get_last_client(data)
    client["birthdate"] = val
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=client.get("codes_id"))
    await state.clear()

@dp.callback_query(F.data == "edit_account")
async def edit_account(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer("Введите новые данные аккаунта (логин, пароль, почта через Enter):")
    await state.set_state(EditClient.edit_account)

@dp.message(EditClient.edit_account)
async def edit_account_enter(message: types.Message, state: FSMContext):
    lines = message.text.strip().split("\n")
    data = await state.get_data()
    client = get_last_client(data)
    client["account"] = lines[0] if len(lines) > 0 else ""
    client["mailpass"] = lines[2] if len(lines) > 2 else ""
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=client.get("codes_id"))
    await state.clear()

@dp.callback_query(F.data == "edit_region")
async def edit_region(call: types.CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Украина")],
        [KeyboardButton(text="Турция")],
        [KeyboardButton(text="Другой")],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)
    await call.message.edit_reply_markup()
    await call.message.answer("Выберите регион:", reply_markup=kb)
    await state.set_state(EditClient.edit_region)

@dp.message(EditClient.edit_region)
async def edit_region_enter(message: types.Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    client = get_last_client(data)
    client["region"] = val
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=client.get("codes_id"))
    await state.clear()

@dp.callback_query(F.data == "edit_codes")
async def edit_codes(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer("Загрузите новые резерв коды (фото):")
    await state.set_state(EditClient.edit_codes)

@dp.message(EditClient.edit_codes, F.photo)
async def edit_codes_enter(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = get_last_client(data)
    photo_id = message.photo[-1].file_id
    client["codes_id"] = photo_id
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=photo_id)
    await state.clear()

@dp.callback_query(F.data == "edit_subscription")
async def edit_subscription(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await call.message.answer("Редактирование подписки не реализовано (добавь обработку аналогично добавлению).")
    # Здесь должен быть пошаговый диалог редактирования подписок по аналогии с добавлением клиента
    await state.clear()

@dp.callback_query(F.data == "edit_games")
async def edit_games(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    data = await state.get_data()
    client = get_last_client(data)
    games_list = "\n".join(client.get("games", []))
    text = "Введите новый список игр (по одной в строке):"
    if games_list:
        text += f"\n\nТекущий список:\n{games_list}"
    await call.message.answer(text)
    await state.set_state(EditClient.edit_games)

@dp.message(EditClient.edit_games)
async def edit_games_enter(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = get_last_client(data)
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    client["games"] = games
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, message.chat.id)
    await send_info_block(state, bot, message.chat.id, client, photo=client.get("codes_id"))
    await state.clear()

@dp.callback_query(F.data == "save_client")
async def save_client(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = get_last_client(data)
    await update_client_in_db(client)
    await delete_previous_bot_messages(state, bot, call.message.chat.id)
    num = client["number"] or client["telegram"]
    msg = await call.message.answer(f"✅ {num} успешно сохранён", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(10)
    await bot.delete_message(chat_id=call.message.chat.id, message_id=msg.message_id)
    await state.clear()

async def delete_previous_bot_messages(state, bot, chat_id):
    # Эту функцию нужно переписать на сохранение id всех сообщений бота через state, а потом удалять их поочередно
    data = await state.get_data()
    msgs = data.get("msg_ids", [])
    for msg_id in msgs:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    await state.update_data(msg_ids=[])

def get_last_client(data):
    # Возвращает последнего найденного/добавленного клиента из state (например, по data['client'])
    return data.get("client", {})
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
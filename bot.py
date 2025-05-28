import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_clients, add_client, update_client, find_client,
    delete_client, export_db, get_client_by_id, get_next_id
)
import logging

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode='HTML')
)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить клиента")],
        [KeyboardButton(text="🔍 Найти клиента")],
        [KeyboardButton(text="📦 Выгрузить базу")],
        [KeyboardButton(text="🧹 Очистить чат")]
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True,
    one_time_keyboard=True
)
yes_no_cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
region_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="укр"), KeyboardButton(text="тур")],
        [KeyboardButton(text="другой")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
console_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="PS4"), KeyboardButton(text="PS5"), KeyboardButton(text="PS4/PS5")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
one_two_none_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Одна"), KeyboardButton(text="Две"), KeyboardButton(text="Отсутствует")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
subs_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
        [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
plus_terms_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1 мес"), KeyboardButton(text="3 мес"), KeyboardButton(text="12 мес")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
ea_terms_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1 мес"), KeyboardButton(text="12 мес")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
games_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
reserve_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

class AddClientFSM(StatesGroup):
    number_or_telegram = State()
    birthdate_q = State()
    birthdate = State()
    account = State()
    region = State()
    console = State()
    subscription_q = State()
    subscriptions_count = State()
    subscription_1_type = State()
    subscription_1_term = State()
    subscription_1_date = State()
    subscription_2_type = State()
    subscription_2_term = State()
    subscription_2_date = State()
    games_q = State()
    games_list = State()
    reserve_q = State()
    reserve_photo = State()
    confirm = State()

class EditClientFSM(StatesGroup):
    edit_field = State()
    number_or_telegram = State()
    birthdate_q = State()
    birthdate = State()
    account = State()
    region = State()
    console = State()
    subscriptions_count = State()
    subscription_1_type = State()
    subscription_1_term = State()
    subscription_1_date = State()
    subscription_2_type = State()
    subscription_2_term = State()
    subscription_2_date = State()
    games_q = State()
    games_list = State()
    reserve_photo = State()

class SearchClientFSM(StatesGroup):
    search = State()

async def clear_chat(chat_id):
    return

def get_sub_line(sub):
    name = sub["name"]
    term = sub.get("term", "")
    date_start = sub.get("date_start", "")
    date_end = sub.get("date_end", "")
    out = ""
    if name != "отсутствует":
        emoji = "🗂" if "PS Plus" in name else "📦"
        out += f"{emoji} <b>{name} {term}</b>\n"
        if date_start and date_end:
            out += f"📅 {date_start} ➔ {date_end}\n"
    else:
        out += "<b>Подписка отсутствует</b>\n"
    return out.strip()

def client_card(client):
    number = client.get("number", "")
    telegram = client.get("telegram", "")
    birth = client.get("birthdate", "")
    console = client.get("console", "")
    account = client.get("account", "")
    password = client.get("password", "")
    emailpass = client.get("emailpass", "")
    region = client.get("region", "")
    games = client.get("games", [])
    subs = client.get("subscriptions", [])

    # ——— Блок номера/Telegram
    num_str = ""
    if number:
        num_str += f"🧑‍💼 <b>{number}</b>"
    elif telegram:
        num_str += f"🆔 <b>{telegram}</b>"
    else:
        num_str += "🧑‍💼 <i>отсутствует</i>"
    # ——— Блок даты и консоли
    if birth != "отсутствует" or console:
        num_str += " | "
        if birth != "отсутствует":
            num_str += f"{birth}"
        if console:
            num_str += f" ({console})"
    out = num_str + "\n"

    # ——— Логин/пароль
    if account:
        out += f"🔐 {account}"
        if password:
            out += f";{password}"
        out += "\n"
    # ——— Почта
    if emailpass:
        out += f"📧 Почта-пароль: {emailpass}\n"

    # ——— Подписки
    if subs and subs[0]["name"] != "отсутствует":
        for sub in subs:
            out += get_sub_line(sub) + "\n"
    else:
        out += "🗂 <b>Подписка отсутствует</b>\n"
    # ——— Регион
    out += f"🌍 Регион: ({region})\n"
    # ——— Игры
    out += "🎮 Игры:\n"
    if games:
        for g in games:
            out += f"• {g}\n"
    else:
        out += "• —\n"
    return out.strip()

def get_edit_kb(client_id):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🧑‍💼 Номер/TG", callback_data=f"edit_{client_id}_number"),
        InlineKeyboardButton(text="🎂 Дата", callback_data=f"edit_{client_id}_birthdate")
    )
    kb.row(
        InlineKeyboardButton(text="🔐 Аккаунт", callback_data=f"edit_{client_id}_account"),
        InlineKeyboardButton(text="🌍 Регион", callback_data=f"edit_{client_id}_region")
    )
    kb.row(
        InlineKeyboardButton(text="🎮 Консоль", callback_data=f"edit_{client_id}_console"),
        InlineKeyboardButton(text="🖼 Резерв", callback_data=f"edit_{client_id}_reserve")
    )
    kb.row(
        InlineKeyboardButton(text="🗂 Подписка", callback_data=f"edit_{client_id}_subscription"),
        InlineKeyboardButton(text="🎲 Игры", callback_data=f"edit_{client_id}_games")
    )
    kb.row(
        InlineKeyboardButton(text="✅ Сохранить", callback_data=f"edit_{client_id}_save"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"edit_{client_id}_delete")
    )
    return kb.as_markup()

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа!")
        return
    await message.answer("Главное меню", reply_markup=main_kb)
    await state.clear()

@dp.message(F.text == "🧹 Очистить чат")
async def clear_chat_cmd(message: types.Message, state: FSMContext):
    await message.answer("Чат очищен.", reply_markup=main_kb)
    await state.clear()

@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await message.answer("Шаг 1: Введите номер телефона или Telegram (@...)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.number_or_telegram)

# ====== ДОБАВЛЕНИЕ КЛИЕНТА: FSM шаги ======

@dp.message(AddClientFSM.number_or_telegram)
async def add_step_1(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = {}
    if txt.startswith("@"):
        data["number"] = ""
        data["telegram"] = txt
    else:
        data["number"] = txt
        data["telegram"] = ""
    await state.update_data(**data)
    await message.answer("Шаг 2: Указать дату рождения?", reply_markup=yes_no_cancel_kb)
    await state.set_state(AddClientFSM.birthdate_q)

@dp.message(AddClientFSM.birthdate_q)
async def add_step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Нет":
        await state.update_data(birthdate="отсутствует")
        await message.answer("Шаг 3: Введите аккаунт (логин, пароль, почта-пароль, каждое с новой строки)", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.account)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.birthdate)
        return
    await message.answer("Выберите вариант: Да/Нет/❌ Отмена", reply_markup=yes_no_cancel_kb)

@dp.message(AddClientFSM.birthdate)
async def add_step_2_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    date_txt = message.text.strip()
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
        await state.update_data(birthdate=date_txt)
        await message.answer("Шаг 3: Введите аккаунт (логин, пароль, почта-пароль, каждое с новой строки)", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.account)
    except:
        await message.answer("Некорректная дата. Введите в формате дд.мм.гггг или ❌ Отмена")

@dp.message(AddClientFSM.account)
async def add_step_3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    lines = message.text.strip().split('\n')
    account = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    emailpass = lines[2] if len(lines) > 2 else ""
    await state.update_data(account=account, password=password, emailpass=emailpass)
    await message.answer("Шаг 4: Выберите регион аккаунта", reply_markup=region_kb)
    await state.set_state(AddClientFSM.region)

@dp.message(AddClientFSM.region)
async def add_step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    reg = message.text.lower()
    if reg not in ["укр", "тур", "другой"]:
        await message.answer("Выберите вариант на клавиатуре", reply_markup=region_kb)
        return
    await state.update_data(region=reg)
    await message.answer("Шаг 5: Укажите консоль", reply_markup=console_kb)
    await state.set_state(AddClientFSM.console)

@dp.message(AddClientFSM.console)
async def add_step_5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    cons = message.text
    if cons not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите вариант на клавиатуре", reply_markup=console_kb)
        return
    await state.update_data(console=cons)
    await message.answer("Шаг 6: Есть ли подписки?", reply_markup=one_two_none_kb)
    await state.set_state(AddClientFSM.subscriptions_count)

@dp.message(AddClientFSM.subscriptions_count)
async def add_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Отсутствует":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await message.answer("Шаг 7: Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(AddClientFSM.games_q)
        return
    if message.text not in ["Одна", "Две"]:
        await message.answer("Выберите: Одна, Две или Отсутствует", reply_markup=one_two_none_kb)
        return
    await state.update_data(subs_count=message.text)
    await message.answer("Выберите подписку", reply_markup=subs_kb)
    await state.set_state(AddClientFSM.subscription_1_type)

@dp.message(AddClientFSM.subscription_1_type)
async def add_sub_1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    name = message.text
    if name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Выберите вариант", reply_markup=subs_kb)
        return
    await state.update_data(sub1_name=name)
    if name.startswith("PS Plus"):
        await message.answer("Срок подписки?", reply_markup=plus_terms_kb)
    else:
        await message.answer("Срок подписки?", reply_markup=ea_terms_kb)
    await state.set_state(AddClientFSM.subscription_1_term)

@dp.message(AddClientFSM.subscription_1_term)
async def add_sub_1_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    term = message.text
    state_data = await state.get_data()
    name = state_data.get("sub1_name", "")
    if name.startswith("PS Plus") and term not in ["1 мес", "3 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=plus_terms_kb)
        return
    if name == "EA Play" and term not in ["1 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=ea_terms_kb)
        return
    await state.update_data(sub1_term=term)
    await message.answer("Дата оформления подписки? (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.subscription_1_date)

@dp.message(AddClientFSM.subscription_1_date)
async def add_sub_1_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    date_txt = message.text.strip()
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата. Введите в формате дд.мм.гггг или ❌ Отмена")
        return
    state_data = await state.get_data()
    count = state_data.get("subs_count")
    sub1 = {
        "name": state_data.get("sub1_name"),
        "term": state_data.get("sub1_term"),
        "date_start": date_txt
    }
    add_months = {"1 мес": 1, "3 мес": 3, "12 мес": 12}
    term = sub1["term"]
    months = add_months.get(term, 1)
    date_end = (d + timedelta(days=months*30)).strftime("%d.%m.%Y")
    sub1["date_end"] = date_end
    if count == "Одна":
        await state.update_data(subscriptions=[sub1])
        await message.answer("Шаг 7: Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(AddClientFSM.games_q)
        return
    await state.update_data(sub1=sub1)
    if sub1["name"] == "EA Play":
        await state.update_data(sub2_cat="PS Plus")
        await message.answer("Выберите вторую подписку (PS Plus Deluxe, Extra, Essential)", reply_markup=subs_kb)
    else:
        await state.update_data(sub2_cat="EA Play")
        await message.answer("Вторая подписка — EA Play", reply_markup=subs_kb)
    await state.set_state(AddClientFSM.subscription_2_type)

@dp.message(AddClientFSM.subscription_2_type)
async def add_sub_2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    state_data = await state.get_data()
    cat = state_data.get("sub2_cat")
    name = message.text
    if cat == "EA Play" and name != "EA Play":
        await message.answer("Выберите EA Play", reply_markup=subs_kb)
        return
    if cat == "PS Plus" and name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        await message.answer("Выберите PS Plus Deluxe, Extra или Essential", reply_markup=subs_kb)
        return
    await state.update_data(sub2_name=name)
    if name.startswith("PS Plus"):
        await message.answer("Срок подписки?", reply_markup=plus_terms_kb)
    else:
        await message.answer("Срок подписки?", reply_markup=ea_terms_kb)
    await state.set_state(AddClientFSM.subscription_2_term)

@dp.message(AddClientFSM.subscription_2_term)
async def add_sub_2_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    term = message.text
    state_data = await state.get_data()
    name = state_data.get("sub2_name", "")
    if name.startswith("PS Plus") and term not in ["1 мес", "3 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=plus_terms_kb)
        return
    if name == "EA Play" and term not in ["1 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=ea_terms_kb)
        return
    await state.update_data(sub2_term=term)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.subscription_2_date)

@dp.message(AddClientFSM.subscription_2_date)
async def add_sub_2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    date_txt = message.text.strip()
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата. Введите в формате дд.мм.гггг или ❌ Отмена")
        return
    state_data = await state.get_data()
    sub1 = state_data.get("sub1")
    sub2 = {
        "name": state_data.get("sub2_name"),
        "term": state_data.get("sub2_term"),
        "date_start": date_txt
    }
    add_months = {"1 мес": 1, "3 мес": 3, "12 мес": 12}
    term = sub2["term"]
    months = add_months.get(term, 1)
    date_end = (d + timedelta(days=months*30)).strftime("%d.%m.%Y")
    sub2["date_end"] = date_end
    await state.update_data(subscriptions=[sub1, sub2])
    await message.answer("Шаг 7: Есть оформленные игры?", reply_markup=games_kb)
    await state.set_state(AddClientFSM.games_q)

@dp.message(AddClientFSM.games_q)
async def add_games_q(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Нет":
        await state.update_data(games=[])
        await message.answer("Шаг 8: Есть резервные коды?", reply_markup=reserve_kb)
        await state.set_state(AddClientFSM.reserve_q)
        return
    if message.text == "Да":
        await message.answer("Введите список игр (каждая с новой строки)", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.games_list)
        return
    await message.answer("Да/Нет/❌ Отмена?", reply_markup=games_kb)

@dp.message(AddClientFSM.games_list)
async def add_games_list(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    games = [g.strip() for g in message.text.strip().split("\n") if g.strip()]
    await state.update_data(games=games)
    await message.answer("Шаг 8: Есть резервные коды?", reply_markup=reserve_kb)
    await state.set_state(AddClientFSM.reserve_q)

@dp.message(AddClientFSM.reserve_q)
async def add_reserve_q(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Нет":
        await state.update_data(reserve_photo_id=None)
        await finalize_add(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите фото резервных кодов", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.reserve_photo)
        return
    await message.answer("Да/Нет/❌ Отмена?", reply_markup=reserve_kb)

@dp.message(AddClientFSM.reserve_photo, F.photo)
async def add_reserve_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(reserve_photo_id=photo_id)
    await finalize_add(message, state)

@dp.message(AddClientFSM.reserve_photo)
async def add_reserve_photo_err(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    await message.answer("Отправьте именно фото или ❌ Отмена", reply_markup=cancel_kb)

async def finalize_add(message, state: FSMContext):
    data = await state.get_data()
    new_id = get_next_id()
    client = {
        "id": new_id,
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "password": data.get("password", ""),
        "emailpass": data.get("emailpass", ""),
        "region": data.get("region", ""),
        "console": data.get("console", ""),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id")
    }
    add_client(client)
    text = client_card(client)
    kb = get_edit_kb(client["id"])
    if client["reserve_photo_id"]:
        msg = await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.update_data(last_card_msg_id=msg.message_id, edit_client_id=client["id"])
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass
    await message.answer("Главное меню", reply_markup=main_kb)
    await state.clear()

# === ПОИСК КЛИЕНТА ===

@dp.message(F.text == "🔍 Найти клиента")
async def search_client(message: types.Message, state: FSMContext):
    await message.answer("Введите номер телефона или Telegram (@...)", reply_markup=cancel_kb)
    await state.set_state(SearchClientFSM.search)

@dp.message(SearchClientFSM.search)
async def do_search(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Поиск отменён", reply_markup=main_kb)
        await state.clear()
        return
    client = find_client(message.text.strip())
    if not client:
        await message.answer("Клиент не найден", reply_markup=main_kb)
        await state.clear()
        return
    kb = get_edit_kb(client["id"])
    text = client_card(client)
    if client.get("reserve_photo_id"):
        msg = await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.update_data(edit_client_id=client["id"], last_card_msg_id=msg.message_id)
    await state.set_state(EditClientFSM.edit_field)
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass
    await message.answer("Главное меню", reply_markup=main_kb)
    await state.clear()

from aiogram.types import CallbackQuery

@dp.callback_query(EditClientFSM.edit_field)
async def edit_choose(call: CallbackQuery, state: FSMContext):
    data = call.data
    client_id = int(data.split("_")[1])
    field = data.split("_")[2]
    await state.update_data(edit_client_id=client_id)
    client = get_client_by_id(client_id)
    if field == "save":
        update_client(client)
        await call.answer("✅ Изменения сохранены!")
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await call.message.answer("Главное меню", reply_markup=main_kb)
        await state.clear()
        return
    if field == "delete":
        delete_client(client_id)
        await call.answer("Клиент удалён")
        await bot.delete_message(call.message.chat.id, call.message.message_id)
        await call.message.answer("Клиент удалён!", reply_markup=main_kb)
        await state.clear()
        return
    if field == "number":
        await call.message.answer("Введите новый номер телефона или Telegram", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.number_or_telegram)
        return
    if field == "birthdate":
        await call.message.answer("Указать дату рождения?", reply_markup=yes_no_cancel_kb)
        await state.set_state(EditClientFSM.birthdate_q)
        return
    if field == "account":
        await call.message.answer("Введите аккаунт (логин, пароль, почта-пароль, каждое с новой строки)", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.account)
        return
    if field == "region":
        await call.message.answer("Выберите регион", reply_markup=region_kb)
        await state.set_state(EditClientFSM.region)
        return
    if field == "console":
        await call.message.answer("Выберите консоль", reply_markup=console_kb)
        await state.set_state(EditClientFSM.console)
        return
    if field == "reserve":
        await call.message.answer("Загрузите новое фото резервных кодов", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.reserve_photo)
        return
    if field == "subscription":
        await call.message.answer("Сколько подписок?", reply_markup=one_two_none_kb)
        await state.set_state(EditClientFSM.subscriptions_count)
        return
    if field == "games":
        await call.message.answer("Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(EditClientFSM.games_q)
        return

# === Остальные хендлеры редактирования (аналогично добавлению, но для клиента из базы) ===
# (См. предыдущие твои примеры - если нужно, выгружу продолжение/редактирование шагов отдельно!)

# === ВЫГРУЗКА БАЗЫ ===

@dp.message(F.text == "📦 Выгрузить базу")
async def export_db_cmd(message: types.Message):
    filepath = export_db()
    await message.answer_document(InputFile(filepath), caption="Текущая база клиентов")

# ==== STARTUP ====

async def birthday_notify_loop():
    while True:
        await asyncio.sleep(3600)
        clients = get_clients()
        today = datetime.now().strftime("%d.%m")
        for c in clients:
            if c.get("birthdate", "отсутствует") != "отсутствует":
                try:
                    dt = datetime.strptime(c["birthdate"], "%d.%m.%Y")
                    if dt.strftime("%d.%m") == today:
                        text = f"🎉 У клиента {'@'+c['telegram'] if c['telegram'] else c['number']} сегодня день рождения!\n\n{client_card(c)}"
                        kb = get_edit_kb(c["id"])
                        if c.get("reserve_photo_id"):
                            await bot.send_photo(ADMIN_ID, c["reserve_photo_id"], text, reply_markup=kb)
                        else:
                            await bot.send_message(ADMIN_ID, text, reply_markup=kb)
                except:
                    continue

async def sub_notify_loop():
    while True:
        await asyncio.sleep(3600)
        clients = get_clients()
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
        for c in clients:
            subs = c.get("subscriptions", [])
            for sub in subs:
                if sub.get("date_end") == tomorrow:
                    text = f"⚠️ Завтра у клиента {'@'+c['telegram'] if c['telegram'] else c['number']} заканчивается подписка:\n\n{get_sub_line(sub)}\n\n{client_card(c)}"
                    kb = get_edit_kb(c["id"])
                    if c.get("reserve_photo_id"):
                        await bot.send_photo(ADMIN_ID, c["reserve_photo_id"], text, reply_markup=kb)
                    else:
                        await bot.send_message(ADMIN_ID, text, reply_markup=kb)

async def on_startup():
    asyncio.create_task(birthday_notify_loop())
    asyncio.create_task(sub_notify_loop())

if __name__ == "__main__":
    dp.startup.register(on_startup)
    asyncio.run(dp.start_polling(bot)
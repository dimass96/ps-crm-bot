import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
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

bot = Bot(token=API_TOKEN, parse_mode='HTML')
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
subs_count_kb = ReplyKeyboardMarkup(
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
    reserve_q = State()
    reserve_photo = State()
    confirm = State()

class EditClientFSM(StatesGroup):
    edit_field = State()
    number_or_telegram = State()
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

# Чистка чата вручную
async def clear_all_chat(message: types.Message):
    try:
        async for m in bot.get_chat_history(message.chat.id, limit=100):
            try:
                await bot.delete_message(message.chat.id, m.message_id)
            except:
                pass
    except:
        pass

def pretty_card(client):
    subs = client.get("subscriptions", [])
    games = client.get("games", [])
    card = ""
    # Личные данные
    num = f'+{client["number"]}' if client.get("number") else ""
    tg = f'@{client.get("telegram")}' if client.get("telegram") else ""
    birth = client.get("birthdate", "отсутствует")
    cons = client.get("console", "")
    line1 = f"👤 {num or tg} | {birth} ({cons})\n"
    # Аккаунт и почта
    account = client.get("account", "")
    password = client.get("password", "")
    emailpass = client.get("emailpass", "")
    if account:
        line1 += f"🔑 {account}"
        if password:
            line1 += f" ;{password}"
        line1 += "\n"
    if emailpass:
        line1 += f"📧 Почта-пароль: {emailpass}\n"
    card += line1
    # Подписки
    if not subs or (len(subs) == 1 and subs[0].get("name") == "отсутствует"):
        card += "\n🗂 Подписка: отсутствует\n"
    else:
        for sub in subs:
            card += f'\n🗂 {sub["name"]} {sub["term"]}\n'
            card += f'📅 {sub["date_start"]} → {sub["date_end"]}\n'
    # Регион
    region = client.get("region", "")
    if region:
        card += f'\n🌍 Регион: {region}\n'
    # Игры
    card += f'\n🎮 Игры:\n'
    if games:
        for g in games:
            card += f'• {g}\n'
    else:
        card += "—"
    return card.strip()

def get_edit_kb(client_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Номер/TG", callback_data=f"edit_{client_id}_number")
    kb.button(text="🎂 Дата", callback_data=f"edit_{client_id}_birthdate")
    kb.button(text="🔑 Аккаунт", callback_data=f"edit_{client_id}_account")
    kb.button(text="🌍 Регион", callback_data=f"edit_{client_id}_region")
    kb.button(text="🎮 Консоль", callback_data=f"edit_{client_id}_console")
    kb.button(text="🖼 Резерв", callback_data=f"edit_{client_id}_reserve")
    kb.button(text="🗂 Подписка", callback_data=f"edit_{client_id}_subscription")
    kb.button(text="🎲 Игры", callback_data=f"edit_{client_id}_games")
    kb.button(text="✅ Сохранить", callback_data=f"edit_{client_id}_save")
    kb.button(text="🗑 Удалить", callback_data=f"edit_{client_id}_delete")
    kb.adjust(2,2,2,2,2)
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
    await clear_all_chat(message)
    await message.answer("Чат очищен!", reply_markup=main_kb)
    await state.clear()

@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await message.answer("Шаг 1: Введите номер телефона или Telegram (@...)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.number_or_telegram)

@dp.message(AddClientFSM.number_or_telegram)
async def add_step_1(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = {}
    if txt.startswith("@"):
        data["number"] = ""
        data["telegram"] = txt[1:]
    else:
        data["number"] = txt
        data["telegram"] = ""
    await state.update_data(**data)
    await message.answer("Шаг 2: Введите дату рождения (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.birthdate)

@dp.message(AddClientFSM.birthdate)
async def add_step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    cons = message.text
    if cons not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите вариант на клавиатуре", reply_markup=console_kb)
        return
    await state.update_data(console=cons)
    await message.answer("Шаг 6: Сколько подписок?", reply_markup=subs_count_kb)
    await state.set_state(AddClientFSM.subscriptions_count)

@dp.message(AddClientFSM.subscriptions_count)
async def add_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    val = message.text
    if val not in ["Одна", "Две", "Отсутствует"]:
        await message.answer("Выберите вариант", reply_markup=subs_count_kb)
        return
    if val == "Отсутствует":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await message.answer("Шаг 7: Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(AddClientFSM.games_q)
        return
    await state.update_data(subs_count=val)
    await message.answer("Выберите подписку", reply_markup=subs_kb)
    await state.set_state(AddClientFSM.subscription_1_type)

@dp.message(AddClientFSM.subscription_1_type)
async def add_sub_1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
        await clear_all_chat(message)
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
    text = pretty_card(client)
    kb = get_edit_kb(client["id"])
    await clear_all_chat(message)
    if client["reserve_photo_id"]:
        msg = await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.clear()

from aiogram.types import CallbackQuery

@dp.message(F.text == "🔍 Найти клиента")
async def search_client(message: types.Message, state: FSMContext):
    await message.answer("Введите номер телефона или Telegram (@...)", reply_markup=cancel_kb)
    await state.set_state(SearchClientFSM.search)

@dp.message(SearchClientFSM.search)
async def do_search(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Поиск отменён", reply_markup=main_kb)
        await state.clear()
        return
    key = message.text.strip()
    client = find_client(key)
    if not client:
        await message.answer("Клиент не найден", reply_markup=main_kb)
        await state.clear()
        return
    kb = get_edit_kb(client["id"])
    text = pretty_card(client)
    await clear_all_chat(message)
    if client.get("reserve_photo_id"):
        msg = await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.update_data(edit_client_id=client["id"])
    await state.set_state(EditClientFSM.edit_field)

@dp.callback_query(EditClientFSM.edit_field)
async def edit_choose(call: CallbackQuery, state: FSMContext):
    data = call.data
    client_id = int(data.split("_")[1])
    field = data.split("_")[2]
    await state.update_data(edit_client_id=client_id)
    client = get_client_by_id(client_id)
    if field == "save":
        update_client(client)
        await call.answer("✅ Изменения сохранены!", show_alert=True)
        await clear_all_chat(call.message)
        await call.message.answer("Главное меню", reply_markup=main_kb)
        await state.clear()
        return
    if field == "delete":
        delete_client(client_id)
        await call.answer("🗑 Клиент удалён", show_alert=True)
        await clear_all_chat(call.message)
        await call.message.answer("Клиент удалён!", reply_markup=main_kb)
        await state.clear()
        return
    if field == "number":
        await call.message.answer("Введите новый номер телефона или Telegram", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.number_or_telegram)
        return
    if field == "birthdate":
        await call.message.answer("Введите новую дату рождения (дд.мм.гггг)", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.birthdate)
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
        await call.message.answer("Сколько подписок?", reply_markup=subs_count_kb)
        await state.set_state(EditClientFSM.subscriptions_count)
        return
    if field == "games":
        await call.message.answer("Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(EditClientFSM.games_q)
        return

@dp.message(EditClientFSM.number_or_telegram)
async def edit_number(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    if txt.startswith("@"):
        client["number"] = ""
        client["telegram"] = txt[1:]
    else:
        client["number"] = txt
        client["telegram"] = ""
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.birthdate)
async def edit_birthdate(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    date_txt = message.text.strip()
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
        data = await state.get_data()
        client_id = data.get("edit_client_id")
        client = get_client_by_id(client_id)
        client["birthdate"] = date_txt
        update_client(client)
        await send_edit_card(message, client)
        await state.set_state(EditClientFSM.edit_field)
    except:
        await message.answer("Некорректная дата. Введите в формате дд.мм.гггг или ❌ Отмена")

@dp.message(EditClientFSM.account)
async def edit_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    lines = message.text.strip().split('\n')
    account = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    emailpass = lines[2] if len(lines) > 2 else ""
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["account"] = account
    client["password"] = password
    client["emailpass"] = emailpass
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.region)
async def edit_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    reg = message.text.lower()
    if reg not in ["укр", "тур", "другой"]:
        await message.answer("Выберите вариант на клавиатуре", reply_markup=region_kb)
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["region"] = reg
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.console)
async def edit_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    cons = message.text
    if cons not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите вариант на клавиатуре", reply_markup=console_kb)
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["console"] = cons
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.reserve_photo, F.photo)
async def edit_reserve_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["reserve_photo_id"] = photo_id
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.reserve_photo)
async def edit_reserve_photo_err(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    await message.answer("Отправьте именно фото или ❌ Отмена", reply_markup=cancel_kb)

@dp.message(EditClientFSM.games_q)
async def edit_games_q(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Нет":
        data = await state.get_data()
        client_id = data.get("edit_client_id")
        client = get_client_by_id(client_id)
        client["games"] = []
        update_client(client)
        await send_edit_card(message, client)
        await state.set_state(EditClientFSM.edit_field)
        return
    if message.text == "Да":
        await message.answer("Введите список игр (каждая с новой строки)", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.games_list)
        return
    await message.answer("Да/Нет/❌ Отмена?", reply_markup=games_kb)

@dp.message(EditClientFSM.games_list)
async def edit_games_list(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    games = [g.strip() for g in message.text.strip().split("\n") if g.strip()]
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["games"] = games
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

# ==== Подписки редактирование ====

@dp.message(EditClientFSM.subscriptions_count)
async def edit_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    if message.text not in ["Одна", "Две", "Отсутствует"]:
        await message.answer("Выберите вариант", reply_markup=subs_count_kb)
        return
    if message.text == "Отсутствует":
        data = await state.get_data()
        client_id = data.get("edit_client_id")
        client = get_client_by_id(client_id)
        client["subscriptions"] = [{"name": "отсутствует"}]
        update_client(client)
        await send_edit_card(message, client)
        await state.set_state(EditClientFSM.edit_field)
        return
    await state.update_data(subs_count=message.text)
    await message.answer("Выберите подписку", reply_markup=subs_kb)
    await state.set_state(EditClientFSM.subscription_1_type)

@dp.message(EditClientFSM.subscription_1_type)
async def edit_sub_1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
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
    await state.set_state(EditClientFSM.subscription_1_term)

@dp.message(EditClientFSM.subscription_1_term)
async def edit_sub_1_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
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
    await state.set_state(EditClientFSM.subscription_1_date)

@dp.message(EditClientFSM.subscription_1_date)
async def edit_sub_1_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
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
        data = await state.get_data()
        client_id = data.get("edit_client_id")
        client = get_client_by_id(client_id)
        client["subscriptions"] = [sub1]
        update_client(client)
        await send_edit_card(message, client)
        await state.set_state(EditClientFSM.edit_field)
        return
    await state.update_data(sub1=sub1)
    if sub1["name"] == "EA Play":
        await state.update_data(sub2_cat="PS Plus")
        await message.answer("Выберите вторую подписку (PS Plus Deluxe, Extra, Essential)", reply_markup=subs_kb)
    else:
        await state.update_data(sub2_cat="EA Play")
        await message.answer("Вторая подписка — EA Play", reply_markup=subs_kb)
    await state.set_state(EditClientFSM.subscription_2_type)

@dp.message(EditClientFSM.subscription_2_type)
async def edit_sub_2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
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
    await state.set_state(EditClientFSM.subscription_2_term)

@dp.message(EditClientFSM.subscription_2_term)
async def edit_sub_2_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
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
    await state.set_state(EditClientFSM.subscription_2_date)

@dp.message(EditClientFSM.subscription_2_date)
async def edit_sub_2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clear_all_chat(message)
        await message.answer("Редактирование отменено", reply_markup=main_kb)
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
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["subscriptions"] = [sub1, sub2]
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

# ==== Служебные функции ====

async def send_edit_card(message, client):
    kb = get_edit_kb(client["id"])
    text = pretty_card(client)
    if client.get("reserve_photo_id"):
        await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

@dp.message(F.text == "🧹 Очистить чат")
async def clear_chat_cmd(message: types.Message, state: FSMContext):
    await clear_all_chat(message)
    await message.answer("Чат очищен!", reply_markup=main_kb)

async def clear_all_chat(message):
    # Тут можно добавить удаление последних N сообщений, если нужно полное очищение
    pass

@dp.message(F.text == "📦 Выгрузить базу")
async def export_db_cmd(message: types.Message):
    file = export_db()
    await message.answer_document(InputFile(file, filename="clients.txt"))

# --- Вспомогательные клавиатуры ---

subs_count_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
        [KeyboardButton(text="Отсутствует")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# --- Красивая карточка ---

def pretty_card(client):
    phone = f"👤 {client['number']}" if client.get('number') else ""
    tg = f" | @{client['telegram']}" if client.get('telegram') else ""
    birth = client.get("birthdate", "")
    console = client.get("console", "")
    top_line = f"{phone}{tg} | {birth} {console}".strip(" |")
    account = f"🔑 {client.get('account', '')}"
    email = f"{client.get('emailpass', '')}"
    password = f"Почта-пароль: {client.get('password', '')}" if client.get("password") else ""
    subs_lines = ""
    subs = client.get("subscriptions", [])
    if subs and subs[0]["name"] != "отсутствует":
        for sub in subs:
            subs_lines += f"\n🗂 {sub['name']} {sub['term']}\n📅 {sub['date_start']} → {sub['date_end']}"
    else:
        subs_lines = "\nНет подписки"
    region = client.get("region", "")
    games = client.get("games", [])
    games_block = "\n".join(f"• {g}" for g in games) if games else ""
    card = (
        f"{top_line}\n"
        f"{account}\n"
        f"{email}\n"
        f"{password}\n"
        f"{subs_lines}\n"
        f"🌍 Регион: {region}\n"
        f"🎮 Игры:\n{games_block}"
    )
    return card
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

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить клиента"), KeyboardButton(text="🔍 Найти клиента")],
        [KeyboardButton(text="📦 Выгрузить базу"), KeyboardButton(text="🧹 Очистить чат")]
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

# --- FSM States ---
class AddClientFSM(StatesGroup):
    number_or_telegram = State()
    birthdate = State()
    console = State()
    account = State()
    region = State()
    subs_count = State()
    sub1_type = State()
    sub1_term = State()
    sub1_date = State()
    sub2_type = State()
    sub2_term = State()
    sub2_date = State()
    games_q = State()
    games_list = State()
    reserve_q = State()
    reserve_photo = State()

class EditClientFSM(StatesGroup):
    edit_field = State()
    number_or_telegram = State()
    birthdate = State()
    console = State()
    account = State()
    region = State()
    subs_count = State()
    sub1_type = State()
    sub1_term = State()
    sub1_date = State()
    sub2_type = State()
    sub2_term = State()
    sub2_date = State()
    games_q = State()
    games_list = State()
    reserve_photo = State()

class SearchClientFSM(StatesGroup):
    search = State()

# --- UTILITIES ---

def pretty_card(client):
    # Оформление карточки клиента — адаптируй под свой стиль!
    number = f"📞 {client['number']}" if client['number'] else f"🆔 {client['telegram']}"
    birth = f"{client['birthdate']}" if client.get("birthdate", "отсутствует") != "отсутствует" else "—"
    console = f"({client['console']})" if client.get("console") else ""
    acc = client.get("account", "")
    passw = client.get("password", "")
    emailpass = client.get("emailpass", "")
    acc_line = f"<b>🔐 {acc}</b> ; <b>{passw}</b>" if acc or passw else ""
    email_line = f"📧 Почта: {emailpass}" if emailpass else ""
    subs_lines = ""
    if client.get("subscriptions") and client["subscriptions"][0]["name"] != "отсутствует":
        for sub in client["subscriptions"]:
            subs_lines += f"💳 {sub['name']} {sub.get('term','')}\n"
            subs_lines += f"📆{sub.get('date_start','')} → {sub.get('date_end','')}\n"
    else:
        subs_lines = "💳 (отсутствует)\n"
    region_line = f"🌎 Регион: {client.get('region','')}"
    games = client.get("games", [])
    games_str = "\n".join([f"– {g}" for g in games]) if games else "–"
    games_line = f"🕹 Игры:\n{games_str}"

    card = (
        f"{number} | {birth} {console}\n"
        f"{acc_line}\n"
        f"{email_line}\n\n"
        f"{subs_lines}"
        f"{region_line}\n"
        f"{games_line}"
    )
    return card.strip()

def get_edit_kb(client_id):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📞 Изменить номер/TG", callback_data=f"edit_{client_id}_number"),
        InlineKeyboardButton(text="🎂 Изменить дату рождения", callback_data=f"edit_{client_id}_birthdate"),
        InlineKeyboardButton(text="🎮 Изменить консоль", callback_data=f"edit_{client_id}_console")
    )
    kb.row(
        InlineKeyboardButton(text="🔐 Изменить данные", callback_data=f"edit_{client_id}_account"),
        InlineKeyboardButton(text="🌎 Изменить регион", callback_data=f"edit_{client_id}_region")
    )
    kb.row(
        InlineKeyboardButton(text="🖼 Изменить резерв коды", callback_data=f"edit_{client_id}_reserve"),
        InlineKeyboardButton(text="💳 Изменить подписку", callback_data=f"edit_{client_id}_subscription"),
        InlineKeyboardButton(text="🕹 Изменить игры", callback_data=f"edit_{client_id}_games")
    )
    kb.row(
        InlineKeyboardButton(text="✅ Сохранить", callback_data=f"edit_{client_id}_save"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"edit_{client_id}_delete")
    )
    return kb.as_markup()

# --- START ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа!")
        return
    await message.answer("Главное меню", reply_markup=main_kb)
    await state.clear()

# === ДОБАВЛЕНИЕ КЛИЕНТА ===
@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await message.answer("Шаг 1: Введите номер телефона или Telegram (@...)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.number_or_telegram)

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
    await message.answer("Шаг 2: Введите дату рождения (дд.мм.гггг) или 'нет'", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.birthdate)

@dp.message(AddClientFSM.birthdate)
async def add_step_2(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if txt.lower() in ["нет", "отсутствует"]:
        await state.update_data(birthdate="отсутствует")
    else:
        try:
            datetime.strptime(txt, "%d.%m.%Y")
            await state.update_data(birthdate=txt)
        except:
            await message.answer("Некорректная дата. Введите дд.мм.гггг или 'нет'.")
            return
    await message.answer("Шаг 3: Выберите консоль", reply_markup=console_kb)
    await state.set_state(AddClientFSM.console)

@dp.message(AddClientFSM.console)
async def add_step_3(message: types.Message, state: FSMContext):
    cons = message.text
    if cons == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if cons not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите вариант", reply_markup=console_kb)
        return
    await state.update_data(console=cons)
    await message.answer("Шаг 4: Введите аккаунт (логин, пароль, почта-пароль, каждое с новой строки)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.account)

@dp.message(AddClientFSM.account)
async def add_step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    lines = message.text.strip().split('\n')
    account = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    emailpass = lines[2] if len(lines) > 2 else ""
    await state.update_data(account=account, password=password, emailpass=emailpass)
    await message.answer("Шаг 5: Выберите регион аккаунта", reply_markup=region_kb)
    await state.set_state(AddClientFSM.region)

@dp.message(AddClientFSM.region)
async def add_step_5(message: types.Message, state: FSMContext):
    reg = message.text.lower()
    if reg == "❌ отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if reg not in ["укр", "тур", "другой"]:
        await message.answer("Выберите регион", reply_markup=region_kb)
        return
    await state.update_data(region=reg)
    await message.answer("Шаг 6: Сколько подписок?", reply_markup=one_two_none_kb)
    await state.set_state(AddClientFSM.subs_count)

@dp.message(AddClientFSM.subs_count)
async def add_step_6(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if txt.lower() == "отсутствует":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await message.answer("Шаг 7: Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(AddClientFSM.games_q)
        return
    if txt not in ["Одна", "Две"]:
        await message.answer("Выберите вариант", reply_markup=one_two_none_kb)
        return
    await state.update_data(subs_count=txt)
    await message.answer("Выберите подписку", reply_markup=subs_kb)
    await state.set_state(AddClientFSM.sub1_type)

@dp.message(AddClientFSM.sub1_type)
async def add_sub1_type(message: types.Message, state: FSMContext):
    name = message.text
    if name == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    if name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Выберите вариант", reply_markup=subs_kb)
        return
    await state.update_data(sub1_name=name)
    if name.startswith("PS Plus"):
        await message.answer("Срок подписки?", reply_markup=plus_terms_kb)
    else:
        await message.answer("Срок подписки?", reply_markup=ea_terms_kb)
    await state.set_state(AddClientFSM.sub1_term)

@dp.message(AddClientFSM.sub1_term)
async def add_sub1_term(message: types.Message, state: FSMContext):
    term = message.text
    if term == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    name = data.get("sub1_name", "")
    if name.startswith("PS Plus") and term not in ["1 мес", "3 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=plus_terms_kb)
        return
    if name == "EA Play" and term not in ["1 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=ea_terms_kb)
        return
    await state.update_data(sub1_term=term)
    await message.answer("Дата оформления подписки? (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.sub1_date)

@dp.message(AddClientFSM.sub1_date)
async def add_sub1_date(message: types.Message, state: FSMContext):
    date_txt = message.text.strip()
    if date_txt == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата. Введите дд.мм.гггг", reply_markup=cancel_kb)
        return
    data = await state.get_data()
    count = data.get("subs_count")
    sub1 = {
        "name": data.get("sub1_name"),
        "term": data.get("sub1_term"),
        "date_start": date_txt
    }
    add_months = {"1 мес": 1, "3 мес": 3, "12 мес": 12}
    months = add_months.get(sub1["term"], 1)
    date_end = (d + timedelta(days=months*30)).strftime("%d.%m.%Y")
    sub1["date_end"] = date_end
    if count == "Одна":
        await state.update_data(subscriptions=[sub1])
        await message.answer("Шаг 7: Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(AddClientFSM.games_q)
        return
    await state.update_data(sub1=sub1)
    if sub1["name"] == "EA Play":
        await message.answer("Выберите вторую подписку (PS Plus Deluxe, Extra, Essential)", reply_markup=subs_kb)
    else:
        await message.answer("Вторая подписка — EA Play", reply_markup=subs_kb)
    await state.set_state(AddClientFSM.sub2_type)

@dp.message(AddClientFSM.sub2_type)
async def add_sub2_type(message: types.Message, state: FSMContext):
    name = message.text
    if name == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    cat1 = data.get("sub1_name", "")
    if cat1 == "EA Play" and name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        await message.answer("Выберите PS Plus подписку", reply_markup=subs_kb)
        return
    if cat1 != "EA Play" and name != "EA Play":
        await message.answer("Выберите EA Play", reply_markup=subs_kb)
        return
    await state.update_data(sub2_name=name)
    if name.startswith("PS Plus"):
        await message.answer("Срок подписки?", reply_markup=plus_terms_kb)
    else:
        await message.answer("Срок подписки?", reply_markup=ea_terms_kb)
    await state.set_state(AddClientFSM.sub2_term)

@dp.message(AddClientFSM.sub2_term)
async def add_sub2_term(message: types.Message, state: FSMContext):
    term = message.text
    if term == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    name = data.get("sub2_name", "")
    if name.startswith("PS Plus") and term not in ["1 мес", "3 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=plus_terms_kb)
        return
    if name == "EA Play" and term not in ["1 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=ea_terms_kb)
        return
    await state.update_data(sub2_term=term)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.sub2_date)

@dp.message(AddClientFSM.sub2_date)
async def add_sub2_date(message: types.Message, state: FSMContext):
    date_txt = message.text.strip()
    if date_txt == "❌ Отмена":
        await message.answer("Добавление отменено", reply_markup=main_kb)
        await state.clear()
        return
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата. Введите дд.мм.гггг", reply_markup=cancel_kb)
        return
    data = await state.get_data()
    sub1 = data.get("sub1")
    sub2 = {
        "name": data.get("sub2_name"),
        "term": data.get("sub2_term"),
        "date_start": date_txt
    }
    add_months = {"1 мес": 1, "3 мес": 3, "12 мес": 12}
    months = add_months.get(sub2["term"], 1)
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
    await message.answer("Отправьте фото или ❌ Отмена", reply_markup=cancel_kb)

async def finalize_add(message, state: FSMContext):
    data = await state.get_data()
    new_id = get_next_id()
    client = {
        "id": new_id,
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "console": data.get("console", ""),
        "account": data.get("account", ""),
        "password": data.get("password", ""),
        "emailpass": data.get("emailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id")
    }
    add_client(client)
    text = "✅ Клиент добавлен!\n\n" + pretty_card(client)
    kb = get_edit_kb(client["id"])
    if client["reserve_photo_id"]:
        msg = await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
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
    text = pretty_card(client)
    if client.get("reserve_photo_id"):
        msg = await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        msg = await message.answer(text, reply_markup=kb)
    await state.update_data(edit_client_id=client["id"])
    await state.set_state(EditClientFSM.edit_field)
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass
    await message.answer("Главное меню", reply_markup=main_kb)
    await state.clear()

from aiogram.types import CallbackQuery

# === РЕДАКТИРОВАНИЕ КЛИЕНТА ===
@dp.callback_query(EditClientFSM.edit_field)
async def edit_choose(call: CallbackQuery, state: FSMContext):
    data = call.data
    client_id = int(data.split("_")[1])
    field = data.split("_")[2]
    await state.update_data(edit_client_id=client_id)
    client = get_client_by_id(client_id)
    if field == "save":
        update_client(client)
        await call.answer("Изменения сохранены!")
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
        await call.message.answer("Введите дату рождения (дд.мм.гггг) или 'нет'", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.birthdate)
        return
    if field == "console":
        await call.message.answer("Выберите консоль", reply_markup=console_kb)
        await state.set_state(EditClientFSM.console)
        return
    if field == "account":
        await call.message.answer("Введите аккаунт (логин, пароль, почта-пароль, каждое с новой строки)", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.account)
        return
    if field == "region":
        await call.message.answer("Выберите регион", reply_markup=region_kb)
        await state.set_state(EditClientFSM.region)
        return
    if field == "reserve":
        await call.message.answer("Загрузите новое фото резервных кодов", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.reserve_photo)
        return
    if field == "subscription":
        await call.message.answer("Сколько подписок?", reply_markup=one_two_none_kb)
        await state.set_state(EditClientFSM.subs_count)
        return
    if field == "games":
        await call.message.answer("Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(EditClientFSM.games_q)
        return

@dp.message(EditClientFSM.number_or_telegram)
async def edit_number(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    if txt.startswith("@"):
        client["number"] = ""
        client["telegram"] = txt
    else:
        client["number"] = txt
        client["telegram"] = ""
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.birthdate)
async def edit_birthdate(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    if txt.lower() in ["нет", "отсутствует"]:
        client["birthdate"] = "отсутствует"
    else:
        try:
            datetime.strptime(txt, "%d.%m.%Y")
            client["birthdate"] = txt
        except:
            await message.answer("Некорректная дата. Введите дд.мм.гггг или 'нет'.")
            return
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.console)
async def edit_console(message: types.Message, state: FSMContext):
    cons = message.text
    if cons == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    if cons not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите вариант", reply_markup=console_kb)
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["console"] = cons
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

@dp.message(EditClientFSM.account)
async def edit_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
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
    reg = message.text.lower()
    if reg == "❌ отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    if reg not in ["укр", "тур", "другой"]:
        await message.answer("Выберите регион", reply_markup=region_kb)
        return
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["region"] = reg
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
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    await message.answer("Отправьте фото или ❌ Отмена", reply_markup=cancel_kb)

@dp.message(EditClientFSM.games_q)
async def edit_games_q(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
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

@dp.message(EditClientFSM.subs_count)
async def edit_subs_count(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    if txt.lower() == "отсутствует":
        data = await state.get_data()
        client_id = data.get("edit_client_id")
        client = get_client_by_id(client_id)
        client["subscriptions"] = [{"name": "отсутствует"}]
        update_client(client)
        await send_edit_card(message, client)
        await state.set_state(EditClientFSM.edit_field)
        return
    if txt not in ["Одна", "Две"]:
        await message.answer("Выберите вариант", reply_markup=one_two_none_kb)
        return
    await state.update_data(subs_count=txt)
    await message.answer("Выберите подписку", reply_markup=subs_kb)
    await state.set_state(EditClientFSM.sub1_type)

@dp.message(EditClientFSM.sub1_type)
async def edit_sub1_type(message: types.Message, state: FSMContext):
    name = message.text
    if name == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    if name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Выберите вариант", reply_markup=subs_kb)
        return
    await state.update_data(sub1_name=name)
    if name.startswith("PS Plus"):
        await message.answer("Срок подписки?", reply_markup=plus_terms_kb)
    else:
        await message.answer("Срок подписки?", reply_markup=ea_terms_kb)
    await state.set_state(EditClientFSM.sub1_term)

@dp.message(EditClientFSM.sub1_term)
async def edit_sub1_term(message: types.Message, state: FSMContext):
    term = message.text
    if term == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    name = data.get("sub1_name", "")
    if name.startswith("PS Plus") and term not in ["1 мес", "3 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=plus_terms_kb)
        return
    if name == "EA Play" and term not in ["1 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=ea_terms_kb)
        return
    await state.update_data(sub1_term=term)
    await message.answer("Дата оформления подписки? (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(EditClientFSM.sub1_date)

@dp.message(EditClientFSM.sub1_date)
async def edit_sub1_date(message: types.Message, state: FSMContext):
    date_txt = message.text.strip()
    if date_txt == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата. Введите дд.мм.гггг", reply_markup=cancel_kb)
        return
    data = await state.get_data()
    count = data.get("subs_count")
    sub1 = {
        "name": data.get("sub1_name"),
        "term": data.get("sub1_term"),
        "date_start": date_txt
    }
    add_months = {"1 мес": 1, "3 мес": 3, "12 мес": 12}
    months = add_months.get(sub1["term"], 1)
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
        await message.answer("Выберите вторую подписку (PS Plus Deluxe, Extra, Essential)", reply_markup=subs_kb)
    else:
        await message.answer("Вторая подписка — EA Play", reply_markup=subs_kb)
    await state.set_state(EditClientFSM.sub2_type)

@dp.message(EditClientFSM.sub2_type)
async def edit_sub2_type(message: types.Message, state: FSMContext):
    name = message.text
    if name == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    cat1 = data.get("sub1_name", "")
    if cat1 == "EA Play" and name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        await message.answer("Выберите PS Plus подписку", reply_markup=subs_kb)
        return
    if cat1 != "EA Play" and name != "EA Play":
        await message.answer("Выберите EA Play", reply_markup=subs_kb)
        return
    await state.update_data(sub2_name=name)
    if name.startswith("PS Plus"):
        await message.answer("Срок подписки?", reply_markup=plus_terms_kb)
    else:
        await message.answer("Срок подписки?", reply_markup=ea_terms_kb)
    await state.set_state(EditClientFSM.sub2_term)

@dp.message(EditClientFSM.sub2_term)
async def edit_sub2_term(message: types.Message, state: FSMContext):
    term = message.text
    if term == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    data = await state.get_data()
    name = data.get("sub2_name", "")
    if name.startswith("PS Plus") and term not in ["1 мес", "3 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=plus_terms_kb)
        return
    if name == "EA Play" and term not in ["1 мес", "12 мес"]:
        await message.answer("Выберите срок", reply_markup=ea_terms_kb)
        return
    await state.update_data(sub2_term=term)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг)", reply_markup=cancel_kb)
    await state.set_state(EditClientFSM.sub2_date)

@dp.message(EditClientFSM.sub2_date)
async def edit_sub2_date(message: types.Message, state: FSMContext):
    date_txt = message.text.strip()
    if date_txt == "❌ Отмена":
        await message.answer("Редактирование отменено", reply_markup=main_kb)
        await state.clear()
        return
    try:
        d = datetime.strptime(date_txt, "%d.%m.%Y")
    except:
        await message.answer("Некорректная дата. Введите дд.мм.гггг", reply_markup=cancel_kb)
        return
    data = await state.get_data()
    sub1 = data.get("sub1")
    sub2 = {
        "name": data.get("sub2_name"),
        "term": data.get("sub2_term"),
        "date_start": date_txt
    }
    add_months = {"1 мес": 1, "3 мес": 3, "12 мес": 12}
    months = add_months.get(sub2["term"], 1)
    date_end = (d + timedelta(days=months*30)).strftime("%d.%m.%Y")
    sub2["date_end"] = date_end
    data = await state.get_data()
    client_id = data.get("edit_client_id")
    client = get_client_by_id(client_id)
    client["subscriptions"] = [sub1, sub2]
    update_client(client)
    await send_edit_card(message, client)
    await state.set_state(EditClientFSM.edit_field)

async def send_edit_card(message, client):
    kb = get_edit_kb(client["id"])
    text = "Изменения обновлены!\n\n" + pretty_card(client)
    if client.get("reserve_photo_id"):
        await message.answer_photo(client["reserve_photo_id"], text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

# === ВЫГРУЗИТЬ БАЗУ ===
@dp.message(F.text == "📦 Выгрузить базу")
async def export_base(message: types.Message):
    path = export_db()
    if not path or not os.path.exists(path):
        await message.answer("База не найдена!", reply_markup=main_kb)
        return
    with open(path, "rb") as f:
        await message.answer_document(types.BufferedInputFile(f.read(), filename=os.path.basename(path)), caption="Текущая база клиентов", reply_markup=main_kb)

# === ОЧИСТИТЬ ЧАТ ===
@dp.message(F.text == "🧹 Очистить чат")
async def clear_chat_cmd(message: types.Message, state: FSMContext):
    for i in range(message.message_id, 0, -1):
        try:
            await bot.delete_message(message.chat.id, i)
        except:
            pass
    await bot.send_message(message.chat.id, "Чат очищен.", reply_markup=main_kb)
    await state.clear()

# ==== Запуск уведомлений ====
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
                        text = f"🎉 У клиента {'@'+c['telegram'] if c['telegram'] else c['number']} сегодня день рождения!\n\n{pretty_card(c)}"
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
                    text = f"⚠️ Завтра у клиента {'@'+c['telegram'] if c['telegram'] else c['number']} заканчивается подписка:\n\n{pretty_card(c)}"
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
    asyncio.run(dp.start_polling(bot))
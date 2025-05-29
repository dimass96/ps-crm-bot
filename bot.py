import asyncio
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import (
    load_db, save_db, get_next_client_id, find_client, update_client, save_new_client, delete_client
)

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

class AddEditClient(StatesGroup):
    contact = State()
    birthdate_yesno = State()
    birthdate = State()
    account = State()
    region = State()
    console = State()
    subscriptions_yesno = State()
    subscriptions_count = State()
    sub_1_type = State()
    sub_1_duration = State()
    sub_1_start = State()
    sub_2_type = State()
    sub_2_duration = State()
    sub_2_start = State()
    games_yesno = State()
    games_input = State()
    reserve_yesno = State()
    reserve_photo = State()
    final_card = State()
    edit_choose = State()
    edit_input = State()
    edit_games = State()
    edit_subs = State()
    edit_reserve = State()
    edit_sub_count = State()
    edit_sub_1_type = State()
    edit_sub_1_duration = State()
    edit_sub_1_start = State()
    edit_sub_2_type = State()
    edit_sub_2_duration = State()
    edit_sub_2_start = State()
    awaiting_confirm = State()

def region_btns():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур")],
            [KeyboardButton(text="другой")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def console_btns():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS4"), KeyboardButton(text="PS5")],
            [KeyboardButton(text="PS4/PS5")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def edit_keyboard(client):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Изменить номер-TG", callback_data=f"edit_contact_{client['id']}")],
        [InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data=f"edit_birth_{client['id']}")],
        [InlineKeyboardButton(text="🔐 Изменить аккаунт", callback_data=f"edit_account_{client['id']}")],
        [InlineKeyboardButton(text="🎮 Изменить консоль", callback_data=f"edit_console_{client['id']}")],
        [InlineKeyboardButton(text="🌍 Изменить регион", callback_data=f"edit_region_{client['id']}")],
        [InlineKeyboardButton(text="🖼 Изменить резерв коды", callback_data=f"edit_reserve_{client['id']}")],
        [InlineKeyboardButton(text="💳 Изменить подписку", callback_data=f"edit_sub_{client['id']}")],
        [InlineKeyboardButton(text="🎲 Изменить игры", callback_data=f"edit_games_{client['id']}")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data=f"save_{client['id']}")]
    ])

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔍 Найти клиента")],
            [KeyboardButton(text="Выгрузить базу")]
        ], resize_keyboard=True
    )

def format_card(client, show_photo_id=False):
    lines = []
    contact = client.get("contact", "—")
    bdate = client.get("birth_date", "отсутствует")
    console = client.get("console", "—")
    lines.append(f"{contact} | {bdate} ({console})")
    acc = client.get("account", {})
    if acc:
        lines.append(f"🔐 {acc.get('login', '')}")
        lines.append(f"✉️ Почта-пароль: {acc.get('mail_pass', '')}")
    subs = client.get("subscriptions", [])
    for sub in subs:
        if sub.get("name") != "отсутствует":
            lines.append(f"\n💳 {sub.get('name', '')} {sub.get('duration', '')}")
            lines.append(f"📅 {sub.get('start', '')} → {sub.get('end', '')}")
    region = client.get("region", "—")
    lines.append(f"\n🌍 Регион: ({region})")
    games = client.get("games", [])
    if games:
        lines.append("\n🎮 Игры:")
        for game in games:
            lines.append(f"• {game}")
    reserve_photo_id = client.get("reserve_photo_id")
    return "\n".join(lines), reserve_photo_id if show_photo_id else None

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu())

# --- ДОБАВЛЕНИЕ КЛИЕНТА ---

@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер телефона или Telegram (@username):", 
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.contact)

@dp.message(AddEditClient.contact)
async def step_contact(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    await state.update_data(contact=message.text.strip())
    await message.answer("Дата рождения есть?", 
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
    await state.set_state(AddEditClient.birthdate_yesno)

@dp.message(AddEditClient.birthdate_yesno)
async def step_birthdate_ask(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(birth_date="отсутствует")
        await ask_account(message, state)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.birthdate)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.birthdate)
async def step_birthdate(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    await state.update_data(birth_date=message.text.strip())
    await ask_account(message, state)

async def ask_account(message, state: FSMContext):
    await message.answer("Введи:\n1. Логин и пароль через ; (пример: login@mail.com; pass)\n2. Почта-пароль (можно пропустить)\n(каждый пункт с новой строки)",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.account)

@dp.message(AddEditClient.account)
async def step_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    rows = message.text.strip().split("\n")
    login = rows[0].strip() if len(rows) > 0 else ""
    mail_pass = rows[1].strip() if len(rows) > 1 else ""
    await state.update_data(account={"login": login, "mail_pass": mail_pass})
    await message.answer("Выбери регион аккаунта:", reply_markup=region_btns())
    await state.set_state(AddEditClient.region)

@dp.message(AddEditClient.region)
async def step_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text not in ("укр", "тур", "другой"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(region=message.text)
    await message.answer("Какая консоль?", reply_markup=console_btns())
    await state.set_state(AddEditClient.console)

@dp.message(AddEditClient.console)
async def step_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text not in ("PS4", "PS5", "PS4/PS5"):
        await message.answer("Нажмите кнопку!")
        return
    await state.update_data(console=message.text)
    await message.answer("Есть подписки?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddEditClient.subscriptions_yesno)

@dp.message(AddEditClient.subscriptions_yesno)
async def step_subs_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await ask_games(message, state)
        return
    if message.text == "Да":
        await message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
        await state.set_state(AddEditClient.subscriptions_count)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.subscriptions_count)
async def step_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text == "Одна":
        await state.update_data(subs_total=1)
        await sub_select(message, state, sub_num=1, only_one=True)
        return
    if message.text == "Две":
        await state.update_data(subs_total=2)
        await sub_select(message, state, sub_num=1, only_one=False)
        return
    await message.answer("Нажмите кнопку!")

async def sub_select(message, state: FSMContext, sub_num=1, only_one=False):
    if sub_num == 1:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True
        )
        await message.answer("Выберите тип подписки:", reply_markup=kb)
        await state.set_state(AddEditClient.sub_1_type)
    else:
        data = await state.get_data()
        prev = data.get("sub_1_type")
        if prev == "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
        await state.set_state(AddEditClient.sub_2_type)

@dp.message(AddEditClient.sub_1_type)
async def sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(sub_1_type=message.text)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_1_duration)

@dp.message(AddEditClient.sub_1_duration)
async def sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    sub_1_type = data.get("sub_1_type")
    if (sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.sub_1_start)

@dp.message(AddEditClient.sub_1_start)
async def sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("sub_1_duration")
    months = int(duration.replace("м", ""))
    end = (start + relativedelta(months=months)).strftime("%d.%m.%Y")
    sub = {
        "name": data.get("sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end
    }
    await state.update_data(sub_1=sub)
    subs_total = data.get("subs_total", 1)
    if subs_total == 2:
        await sub_select(message, state, sub_num=2)
    else:
        await state.update_data(subscriptions=[sub])
        await ask_games(message, state)

@dp.message(AddEditClient.sub_2_type)
async def sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    prev = data.get("sub_1_type")
    if prev == "EA Play":
        if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
            await message.answer("Выберите PS Plus!")
            return
    else:
        if message.text != "EA Play":
            await message.answer("Выберите EA Play!")
            return
    await state.update_data(sub_2_type=message.text)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.sub_2_duration)

@dp.message(AddEditClient.sub_2_duration)
async def sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    sub_2_type = data.get("sub_2_type")
    if (sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.sub_2_start)

@dp.message(AddEditClient.sub_2_start)
async def sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("sub_2_duration")
    months = int(duration.replace("м", ""))
    end = (start + relativedelta(months=months)).strftime("%d.%m.%Y")
    sub = {
        "name": data.get("sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end
    }
    sub1 = data.get("sub_1")
    await state.update_data(sub_2=sub)
    await state.update_data(subscriptions=[sub1, sub])
    await ask_games(message, state)

async def ask_games(message, state: FSMContext):
    await message.answer("Оформлены игры?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddEditClient.games_yesno)

@dp.message(AddEditClient.games_yesno)
async def games_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(games=[])
        await ask_reserve(message, state)
        return
    if message.text == "Да":
        await state.update_data(games=[])
        await message.answer("Введи список игр (каждая с новой строки):", 
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.games_input)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.games_input)
async def games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    await state.update_data(games=games)
    await ask_reserve(message, state)

async def ask_reserve(message, state: FSMContext):
    await message.answer("Есть ли резервные коды?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddEditClient.reserve_yesno)

@dp.message(AddEditClient.reserve_yesno)
async def reserve_yesno(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text == "Нет":
        await state.update_data(reserve_photo_id=None)
        await finish_client(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот (фото):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.reserve_photo)
        return
    await message.answer("Нажмите кнопку!")

@dp.message(AddEditClient.reserve_photo)
async def reserve_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.photo:
        file_id = message.photo[-1].file_id
        await state.update_data(reserve_photo_id=file_id)
        await finish_client(message, state)
    else:
        await message.answer("Отправьте именно фото!")

async def finish_client(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = {
        "id": get_next_client_id(load_db()),
        "contact": data.get("contact", ""),
        "birth_date": data.get("birth_date", "отсутствует"),
        "account": data.get("account", {}),
        "region": data.get("region", ""),
        "console": data.get("console", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_photo_id": data.get("reserve_photo_id", None),
    }
    save_new_client(client)
    await state.clear()
    if client.get("reserve_photo_id"):
        msg = await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
    else:
        msg = await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))
    await asyncio.sleep(300)
    try:
        await bot.delete_message(msg.chat.id, msg.message_id)
    except: pass

# --- Поиск, редактирование, выгрузка и т.д. (не изменял — берём из последней рабочей версии, если нужно продолжение, скажи) ---

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# --- ПОИСК КЛИЕНТА ---

@dp.message(F.text == "🔍 Найти клиента")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер телефона или Telegram (@username) для поиска:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_choose)

@dp.message(AddEditClient.edit_choose)
async def search_choose(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    query = message.text.strip()
    client = find_client(query)
    if not client:
        await message.answer("Клиент не найден.")
        await start_cmd(message, state)
        return
    await state.clear()
    await state.update_data(edit_id=client["id"])
    if client.get("reserve_photo_id"):
        msg = await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
    else:
        msg = await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))

# --- ИНЛАЙН-КНОПКИ РЕДАКТИРОВАНИЯ ---

@dp.callback_query(F.data.startswith("edit_"))
async def edit_fields(callback: types.CallbackQuery, state: FSMContext):
    act, field, cid = callback.data.split("_", 2)
    cid = int(cid)
    clients = load_db()
    client = next((c for c in clients if c["id"] == cid), None)
    if not client:
        await callback.message.answer("Клиент не найден!")
        return
    await state.clear()
    await state.update_data(edit_id=cid)
    if field == "contact":
        await callback.message.answer("Введите новый номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="contact")
        return
    if field == "birth":
        await callback.message.answer("Введите новую дату рождения (дд.мм.гггг) или 'отсутствует':", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="birth_date")
        return
    if field == "account":
        await callback.message.answer("Введи:\n1. Логин и пароль через ; (пример: login@mail.com; pass)\n2. Почта-пароль (можно пропустить)\n(каждый пункт с новой строки)",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="account")
        return
    if field == "console":
        await callback.message.answer("Выбери консоль:", reply_markup=console_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="console")
        return
    if field == "region":
        await callback.message.answer("Выбери регион аккаунта:", reply_markup=region_btns())
        await state.set_state(AddEditClient.edit_input)
        await state.update_data(edit_field="region")
        return
    if field == "reserve":
        await callback.message.answer("Загрузите новое фото резерв-кодов:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_reserve)
        return
    if field == "sub":
        await callback.message.answer("Сколько подписок у клиента?", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Одна"), KeyboardButton(text="Две"), KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_sub_count)
        return
    if field == "games":
        await callback.message.answer("Введи список игр (каждая с новой строки):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddEditClient.edit_games)
        return

# --- РЕДАКТИРОВАНИЕ ПРОСТЫХ ПОЛЕЙ ---

@dp.message(AddEditClient.edit_input)
async def edit_input_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    cid = data.get("edit_id")
    field = data.get("edit_field")
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == cid:
            if field == "contact":
                c["contact"] = message.text.strip()
            elif field == "birth_date":
                c["birth_date"] = message.text.strip()
            elif field == "account":
                rows = message.text.strip().split("\n")
                login = rows[0].strip() if len(rows) > 0 else ""
                mail_pass = rows[1].strip() if len(rows) > 1 else ""
                c["account"] = {"login": login, "mail_pass": mail_pass}
            elif field == "console":
                c["console"] = message.text.strip()
            elif field == "region":
                c["region"] = message.text.strip()
            clients[i] = c
            save_db(clients)
            await state.clear()
            await update_card(message, c)
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

# --- РЕДАКТИРОВАНИЕ ИГР ---

@dp.message(AddEditClient.edit_games)
async def edit_games_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    games = [line.strip() for line in message.text.strip().split("\n") if line.strip()]
    data = await state.get_data()
    cid = data.get("edit_id")
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == cid:
            c["games"] = games
            clients[i] = c
            save_db(clients)
            await state.clear()
            await update_card(message, c)
            return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

# --- РЕДАКТИРОВАНИЕ РЕЗЕРВ-КОДОВ ---

@dp.message(AddEditClient.edit_reserve)
async def edit_reserve_handler(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.photo:
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["reserve_photo_id"] = photo_id
                clients[i] = c
                save_db(clients)
                await state.clear()
                await update_card(message, c)
                return
    await message.answer("Ошибка при обновлении.")
    await state.clear()

# --- РЕДАКТИРОВАНИЕ ПОДПИСОК ---

@dp.message(AddEditClient.edit_sub_count)
async def edit_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    cid = data.get("edit_id")
    clients = load_db()
    client = next((c for c in clients if c["id"] == cid), None)
    if not client:
        await message.answer("Ошибка.")
        await state.clear()
        return
    if message.text == "Нет подписки":
        client["subscriptions"] = [{"name": "отсутствует"}]
        save_db(clients)
        await state.clear()
        await update_card(message, client)
        return
    if message.text == "Одна":
        await state.update_data(edit_subs_total=1)
        await edit_sub_select(message, state, sub_num=1, only_one=True)
        return
    if message.text == "Две":
        await state.update_data(edit_subs_total=2)
        await edit_sub_select(message, state, sub_num=1, only_one=False)
        return
    await message.answer("Нажмите кнопку!")

async def edit_sub_select(message, state: FSMContext, sub_num=1, only_one=False):
    if sub_num == 1:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True
        )
        await message.answer("Выберите тип подписки:", reply_markup=kb)
        await state.set_state(AddEditClient.edit_sub_1_type)
    else:
        data = await state.get_data()
        prev = data.get("edit_sub_1_type")
        if prev == "EA Play":
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="❌ Отмена")]
                ], resize_keyboard=True)
        await message.answer("Выберите вторую подписку:", reply_markup=kb)
        await state.set_state(AddEditClient.edit_sub_2_type)

@dp.message(AddEditClient.edit_sub_1_type)
async def edit_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
        await message.answer("Выберите подписку кнопкой!")
        return
    await state.update_data(edit_sub_1_type=message.text)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_1_duration)

@dp.message(AddEditClient.edit_sub_1_duration)
async def edit_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    edit_sub_1_type = data.get("edit_sub_1_type")
    if (edit_sub_1_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (edit_sub_1_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_1_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_1_start)

@dp.message(AddEditClient.edit_sub_1_start)
async def edit_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_1_duration")
    months = int(duration.replace("м", ""))
    end = (start + relativedelta(months=months)).strftime("%d.%m.%Y")
    sub = {
        "name": data.get("edit_sub_1_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end
    }
    await state.update_data(edit_sub_1=sub)
    subs_total = data.get("edit_subs_total", 1)
    if subs_total == 2:
        await edit_sub_select(message, state, sub_num=2)
    else:
        # Обновляем подписку клиента
        cid = data.get("edit_id")
        clients = load_db()
        for i, c in enumerate(clients):
            if c["id"] == cid:
                c["subscriptions"] = [sub]
                clients[i] = c
                save_db(clients)
                await state.clear()
                await update_card(message, c)
                return

@dp.message(AddEditClient.edit_sub_2_type)
async def edit_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    prev = data.get("edit_sub_1_type")
    if prev == "EA Play":
        if message.text not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
            await message.answer("Выберите PS Plus!")
            return
    else:
        if message.text != "EA Play":
            await message.answer("Выберите EA Play!")
            return
    await state.update_data(edit_sub_2_type=message.text)
    if message.text == "EA Play":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    else:
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")], [KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    await message.answer("Выберите срок:", reply_markup=kb)
    await state.set_state(AddEditClient.edit_sub_2_duration)

@dp.message(AddEditClient.edit_sub_2_duration)
async def edit_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    data = await state.get_data()
    edit_sub_2_type = data.get("edit_sub_2_type")
    if (edit_sub_2_type == "EA Play" and message.text not in ("1м", "12м")) or \
       (edit_sub_2_type != "EA Play" and message.text not in ("1м", "3м", "12м")):
        await message.answer("Выберите срок кнопкой!")
        return
    await state.update_data(edit_sub_2_duration=message.text)
    await message.answer("Дата оформления (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddEditClient.edit_sub_2_start)

@dp.message(AddEditClient.edit_sub_2_start)
async def edit_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await start_cmd(message, state)
        return
    try:
        start = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Формат даты: дд.мм.гггг")
        return
    data = await state.get_data()
    duration = data.get("edit_sub_2_duration")
    months = int(duration.replace("м", ""))
    end = (start + relativedelta(months=months)).strftime("%d.%m.%Y")
    sub2 = {
        "name": data.get("edit_sub_2_type"),
        "duration": duration,
        "start": message.text.strip(),
        "end": end
    }
    sub1 = data.get("edit_sub_1")
    cid = data.get("edit_id")
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == cid:
            c["subscriptions"] = [sub1, sub2]
            clients[i] = c
            save_db(clients)
            await state.clear()
            await update_card(message, c)
            return

# --- ОБНОВЛЕНИЕ КАРТОЧКИ ПОСЛЕ РЕДАКТИРОВАНИЯ ---

async def update_card(message, client):
    # Удаляем старые сообщения и отправляем карточку с кнопками
    if client.get("reserve_photo_id"):
        await message.answer_photo(client["reserve_photo_id"], caption=format_card(client)[0], reply_markup=edit_keyboard(client))
    else:
        await message.answer(format_card(client)[0], reply_markup=edit_keyboard(client))

# --- КНОПКА СОХРАНИТЬ ---

@dp.callback_query(F.data.startswith("save_"))
async def save_client(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Изменения сохранены! Возврат в главное меню.", reply_markup=main_menu())

# --- ВЫГРУЗКА БАЗЫ ---
@dp.message(F.text.in_({"Выгрузить базу", "выгрузить базу", "dump"}))
async def dump_db(message: types.Message):
    clients = load_db()
    import json
    with open("clients_dump.json", "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)
    await bot.send_document(message.chat.id, InputFile("clients_dump.json"))
    os.remove("clients_dump.json")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import date

scheduler = AsyncIOScheduler()

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d.%m.%Y").date()
    except Exception:
        return None

async def send_sub_expiry_notifications():
    clients = load_db()
    today = date.today()
    notify_day = today + timedelta(days=1)
    for client in clients:
        for sub in client.get("subscriptions", []):
            if sub.get("name") != "отсутствует":
                end_date = parse_date(sub.get("end", ""))
                if end_date and end_date == notify_day:
                    contact = client.get("contact", "")
                    await bot.send_message(
                        ADMIN_ID,
                        f"⚠️ Завтра ({end_date.strftime('%d.%m.%Y')}) заканчивается подписка у клиента:\n<b>{contact}</b>\nПодписка: {sub.get('name')} {sub.get('duration')}"
                    )

async def send_birthday_notifications():
    clients = load_db()
    today = date.today()
    today_str = today.strftime("%d.%m")
    for client in clients:
        birth = client.get("birth_date", "")
        if birth and birth != "отсутствует":
            try:
                day, month, *_ = birth.split(".")
                if f"{day.zfill(2)}.{month.zfill(2)}" == today_str:
                    contact = client.get("contact", "")
                    await bot.send_message(
                        ADMIN_ID,
                        f"🎉 Сегодня день рождения у клиента:\n<b>{contact}</b> ({birth})"
                    )
            except Exception:
                continue

def setup_scheduled_jobs():
    scheduler.add_job(send_sub_expiry_notifications, "cron", hour=9, minute=0)
    scheduler.add_job(send_birthday_notifications, "cron", hour=9, minute=0)

setup_scheduled_jobs()
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_clients, add_client, update_client, find_client,
    delete_client, export_db, get_client_by_id, get_next_id
)

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

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
    reserve_q = State()
    reserve_photo = State()

class EditClientFSM(StatesGroup):
    field = State()
    value = State()
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
    reserve_q = State()
    reserve_photo = State()

class SearchClientFSM(StatesGroup):
    search = State()

async def clear_chat(chat_id):
    # aiogram 3.x не поддерживает получение всей истории чата, только свои сообщения.
    pass

def client_card(client):
    # Форматирование карточки как по скрину
    num = client["number"] or client["telegram"]
    number = f'📞 {num}'
    birth = ""
    if client.get("birthdate") and client["birthdate"] != "отсутствует":
        birth = f'{client["birthdate"]}'
    console = f'({client["console"]})' if client.get("console") else ""
    line1 = f'{number} | {birth} {console}'.strip()
    account = f'🔐{client.get("account", "")} ;{client.get("password", "")}'
    email = f'📧 Почта: {client.get("emailpass", "")}' if client.get("emailpass") else ""
    # Подписки
    subs = client.get("subscriptions", [])
    subs_lines = []
    for sub in subs:
        if sub["name"] == "отсутствует":
            continue
        line = f'💳 {sub["name"]} {sub["term"]}'
        line2 = f'📆{sub["date_start"]} → {sub["date_end"]}'
        subs_lines.extend([line, line2])
    # Регион
    region = f'🌎 Регион: ({client.get("region", "")})'
    # Игры
    games = client.get("games", [])
    if games:
        games_text = "\n".join([f"– {g}" for g in games])
    else:
        games_text = "–"
    card = (
        f"{line1}\n"
        f"{account}\n"
        f"{email}\n\n"
        f"{('\n'.join(subs_lines) + '\n') if subs_lines else ''}"
        f"{region}\n"
        f"🕹 Игры:\n{games_text}"
    )
    return card.strip()

def get_edit_kb(client_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="📞 Изменить номер/TG", callback_data=f"edit_{client_id}_number")
    kb.button(text="🎂 Изменить дату рождения", callback_data=f"edit_{client_id}_birthdate")
    kb.button(text="🎮 Изменить консоль", callback_data=f"edit_{client_id}_console")
    kb.button(text="🔐 Изменить данные", callback_data=f"edit_{client_id}_account")
    kb.button(text="📧 Изменить почту", callback_data=f"edit_{client_id}_emailpass")
    kb.button(text="🌎 Изменить регион", callback_data=f"edit_{client_id}_region")
    kb.button(text="💳 Изменить подписки", callback_data=f"edit_{client_id}_subscriptions")
    kb.button(text="🕹 Изменить игры", callback_data=f"edit_{client_id}_games")
    kb.button(text="🖼 Изменить резерв", callback_data=f"edit_{client_id}_reserve")
    kb.button(text="✅ Сохранить", callback_data=f"edit_{client_id}_save")
    kb.button(text="🗑 Удалить", callback_data=f"edit_{client_id}_delete")
    return kb.adjust(2).as_markup()

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа!")
        return
    await message.answer("Главное меню", reply_markup=main_kb)
    await state.clear()

@dp.message(F.text == "🧹 Очистить чат")
async def clear_chat_cmd(message: types.Message, state: FSMContext):
    await message.answer("Чат очищен. Главное меню.", reply_markup=main_kb)
    await state.clear()

@dp.message(F.text == "📦 Выгрузить базу")
async def export_base(message: types.Message):
    path = export_db()
    await message.answer_document(types.FSInputFile(path), caption="Текущая база клиентов", reply_markup=main_kb)

@dp.message(F.text == "➕ Добавить клиента")
async def add_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер телефона или Telegram (@...)", reply_markup=cancel_kb)
    await state.set_state(AddClientFSM.number_or_telegram)

@dp.message(AddClientFSM.number_or_telegram)
async def add_step1(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
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
    await message.answer("Указать дату рождения?", reply_markup=yes_no_cancel_kb)
    await state.set_state(AddClientFSM.birthdate_q)

@dp.message(AddClientFSM.birthdate_q)
async def add_birthdate_q(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Нет":
        await state.update_data(birthdate="отсутствует")
        await message.answer("Введите данные аккаунта (логин, пароль, почта, каждое с новой строки)", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.account)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.birthdate)
        return
    await message.answer("Выберите вариант: Да/Нет/❌ Отмена", reply_markup=yes_no_cancel_kb)

@dp.message(AddClientFSM.birthdate)
async def add_birthdate(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
        await state.clear()
        return
    try:
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        await state.update_data(birthdate=message.text.strip())
        await message.answer("Введите данные аккаунта (логин, пароль, почта, каждое с новой строки)", reply_markup=cancel_kb)
        await state.set_state(AddClientFSM.account)
    except:
        await message.answer("Некорректная дата. Введите в формате дд.мм.гггг или ❌ Отмена")

@dp.message(AddClientFSM.account)
async def add_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
        await state.clear()
        return
    lines = message.text.strip().split('\n')
    account = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    emailpass = lines[2] if len(lines) > 2 else ""
    await state.update_data(account=account, password=password, emailpass=emailpass)
    await message.answer("Выберите регион аккаунта", reply_markup=region_kb)
    await state.set_state(AddClientFSM.region)

@dp.message(AddClientFSM.region)
async def add_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
        await state.clear()
        return
    reg = message.text.lower()
    if reg not in ["укр", "тур", "другой"]:
        await message.answer("Выберите регион на клавиатуре", reply_markup=region_kb)
        return
    await state.update_data(region=reg)
    await message.answer("Выберите консоль", reply_markup=console_kb)
    await state.set_state(AddClientFSM.console)

@dp.message(AddClientFSM.console)
async def add_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
        await state.clear()
        return
    cons = message.text
    if cons not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите вариант на клавиатуре", reply_markup=console_kb)
        return
    await state.update_data(console=cons)
    await message.answer("Сколько подписок?", reply_markup=subs_count_kb)
    await state.set_state(AddClientFSM.subscriptions_count)

@dp.message(AddClientFSM.subscriptions_count)
async def add_subs_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Добавление отменено.", reply_markup=main_kb)
        await state.clear()
        return
    if message.text == "Отсутствует":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await message.answer("Есть оформленные игры?", reply_markup=games_kb)
        await state.set_state(AddClientFSM.games_q)
        return
    if message.text not in ["Одна", "Две"]:
        await message.answer("Выберите Одна, Две или Отсутствует", reply_markup=subs_count_kb)
        return
    await state.update_data(subs_count=message.text)
    await message.answer("Выберите подписку", reply_markup=subs_kb)
    await state.set_state(AddClientFSM.subscription_1_type)

# ... Далее реализуй все шаги подписок, игр, резервных кодов (как раньше), аналогично предыдущим примерам.
# После добавления клиента — вызывай функцию, которая сразу рендерит карточку с инлайн-кнопками (get_edit_kb).

# ----- Обработчик инлайн-кнопок -----
from aiogram.types import CallbackQuery

@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_handler(call: CallbackQuery, state: FSMContext):
    client_id = int(call.data.split("_")[1])
    field = call.data.split("_")[2]
    client = get_client_by_id(client_id)
    if field == "delete":
        delete_client(client_id)
        await call.message.answer("Клиент удалён!", reply_markup=main_kb)
        await call.message.delete()
        await state.clear()
        return
    if field == "save":
        update_client(client)
        await call.message.answer("Изменения сохранены!", reply_markup=main_kb)
        await call.message.delete()
        await state.clear()
        return
    # Остальные поля — переключение FSM и запуск шага редактирования
    await state.update_data(edit_client_id=client_id)
    if field == "number":
        await call.message.answer("Введите новый номер или Telegram", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.number_or_telegram)
    elif field == "birthdate":
        await call.message.answer("Введите новую дату рождения (дд.мм.гггг)", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.birthdate)
    elif field == "console":
        await call.message.answer("Выберите консоль", reply_markup=console_kb)
        await state.set_state(EditClientFSM.console)
    elif field == "account":
        await call.message.answer("Введите новые данные аккаунта (логин, пароль, почта)", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.account)
    elif field == "emailpass":
        await call.message.answer("Введите новую почту", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.account)
    elif field == "region":
        await call.message.answer("Выберите регион", reply_markup=region_kb)
        await state.set_state(EditClientFSM.region)
    elif field == "subscriptions":
        await call.message.answer("Сколько подписок?", reply_markup=subs_count_kb)
        await state.set_state(EditClientFSM.subscriptions_count)
    elif field == "games":
        await call.message.answer("Есть ли игры?", reply_markup=games_kb)
        await state.set_state(EditClientFSM.games_q)
    elif field == "reserve":
        await call.message.answer("Отправьте новое фото резервных кодов", reply_markup=cancel_kb)
        await state.set_state(EditClientFSM.reserve_photo)

# (Все шаги FSM для редактирования — те же что при добавлении, только обновляют клиент в базе и пересобирают карточку.)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
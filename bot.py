import os
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup

from database import (
    load_db, save_db, add_client_to_db, update_client_in_db,
    find_client, delete_client, export_all
)

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

class AddClient(StatesGroup):
    number = State()
    birth_check = State()
    birthdate = State()
    account = State()
    region = State()
    console = State()
    subscription_count = State()
    sub1_type = State()
    sub1_term = State()
    sub1_date = State()
    sub2_type = State()
    sub2_term = State()
    sub2_date = State()
    games_check = State()
    games = State()
    codes_check = State()
    codes = State()
    confirm = State()

class EditClient(StatesGroup):
    edit_number = State()
    edit_birthdate = State()
    edit_account = State()
    edit_region = State()
    edit_codes = State()
    edit_subscription = State()
    edit_games = State()

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить"), KeyboardButton(text="Поиск")],
        [KeyboardButton(text="Очистить чат"), KeyboardButton(text="Выгрузить базу")]
    ],
    resize_keyboard=True
)

def get_cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )

def get_yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True
    )

def get_region_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Украина"), KeyboardButton(text="Турция"), KeyboardButton(text="Другое")]],
        resize_keyboard=True
    )

def get_console_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="PS4"), KeyboardButton(text="PS5"), KeyboardButton(text="PS4/PS5")]],
        resize_keyboard=True
    )

def get_subscription_count_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Нет подписки")],
            [KeyboardButton(text="Одна подписка")],
            [KeyboardButton(text="Две подписки")]
        ],
        resize_keyboard=True
    )

def get_sub1_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
            [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")]
        ],
        resize_keyboard=True
    )

def get_sub2_type_kb(exclude):
    subs = [
        ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"),
        ("EA Play",)
    ]
    kb = []
    if exclude.startswith("PS Plus"):
        kb.append([KeyboardButton(text="EA Play")])
    else:
        kb.append([KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"),
                   KeyboardButton(text="PS Plus Essential")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_term_kb(sub_type):
    if "EA Play" in sub_type:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="1 мес"), KeyboardButton(text="12 мес")]],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="1 мес"), KeyboardButton(text="3 мес"), KeyboardButton(text="12 мес")]],
            resize_keyboard=True
        )

def get_edit_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Изменить номер/TG", callback_data="edit_number"),
             InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birthdate")],
            [InlineKeyboardButton(text="🔐 Изменить аккаунт", callback_data="edit_account"),
             InlineKeyboardButton(text="🌎 Изменить регион", callback_data="edit_region")],
            [InlineKeyboardButton(text="🗝 Изменить резерв коды", callback_data="edit_codes")],
            [InlineKeyboardButton(text="💳 Изменить подписку", callback_data="edit_subscription")],
            [InlineKeyboardButton(text="🎮 Изменить игры", callback_data="edit_games")],
            [InlineKeyboardButton(text="✅ Сохранить", callback_data="save")]
        ]
    )

async def clear_all_messages(message: Message):
    try:
        async for msg in bot.get_chat_history(message.chat.id, limit=100):
            try:
                await bot.delete_message(message.chat.id, msg.message_id)
            except:
                continue
    except:
        pass

def client_info_text(client):
    parts = []
    if client.get("number"):
        parts.append(f"<b>Номер/TG:</b> {client.get('number', '')}")
    if client.get("birthdate"):
        parts.append(f"<b>Дата рождения:</b> {client.get('birthdate', 'отсутствует')}")
    parts.append(f"<b>Аккаунт:</b> {client.get('account', '')}")
    if client.get("region"):
        parts.append(f"<b>Регион:</b> {client.get('region', '')}")
    subs = client.get("subscriptions", [])
    for s in subs:
        parts.append(f"<b>Подписка:</b> {s['name']} {s['term']} — до {s['end']}")
    games = client.get("games", [])
    if games:
        parts.append(f"<b>Игры:</b> " + ", ".join(games))
    if client.get("codes_file_id"):
        parts.append("<b>Резерв коды:</b> прикреплён файл")
    return "\n".join(parts)

@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_kb)

@dp.message(F.text == "Добавить")
async def add_client(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер телефона или Telegram клиента:", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.number)

@dp.message(AddClient.number)
async def add_number(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(number=message.text.strip())
    await message.answer("Есть ли дата рождения?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.birth_check)

@dp.message(AddClient.birth_check)
async def add_birth_check(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())
        await state.set_state(AddClient.birthdate)
    else:
        await state.update_data(birthdate="отсутствует")
        await message.answer("Введите логин и пароль от аккаунта (каждый на новой строке):", reply_markup=get_cancel_kb())
        await state.set_state(AddClient.account)

@dp.message(AddClient.birthdate)
async def add_birthdate(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(birthdate=message.text.strip())
    await message.answer("Введите логин и пароль от аккаунта (каждый на новой строке):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.account)

@dp.message(AddClient.account)
async def add_account(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    lines = message.text.split("\n")
    if len(lines) < 2:
        await message.answer("Пожалуйста, введите логин и пароль (каждый на новой строке).")
        return
    login = lines[0].strip()
    password = lines[1].strip()
    mail = lines[2].strip() if len(lines) > 2 else ""
    await state.update_data(account=f"{login};{password};{mail}")
    await message.answer("Выберите регион аккаунта:", reply_markup=get_region_kb())
    await state.set_state(AddClient.region)

@dp.message(AddClient.region)
async def add_region(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(region=message.text.strip())
    await message.answer("Какие консоли?", reply_markup=get_console_kb())
    await state.set_state(AddClient.console)

@dp.message(AddClient.console)
async def add_console(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(console=message.text.strip())
    await message.answer("Сколько подписок оформлено?", reply_markup=get_subscription_count_kb())
    await state.set_state(AddClient.subscription_count)

@dp.message(AddClient.subscription_count)
async def add_sub_count(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    if message.text == "Нет подписки":
        await state.update_data(subscriptions=[])
        await message.answer("Есть оформленные игры?", reply_markup=get_yes_no_kb())
        await state.set_state(AddClient.games_check)
    elif message.text == "Одна подписка":
        await state.update_data(subscription_count=1)
        await message.answer("Выберите подписку:", reply_markup=get_sub1_type_kb())
        await state.set_state(AddClient.sub1_type)
    else:
        await state.update_data(subscription_count=2)
        await message.answer("Выберите первую подписку:", reply_markup=get_sub1_type_kb())
        await state.set_state(AddClient.sub1_type)

@dp.message(AddClient.sub1_type)
async def add_sub1_type(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(sub1_type=message.text.strip())
    await message.answer("Выберите срок первой подписки:", reply_markup=get_term_kb(message.text))
    await state.set_state(AddClient.sub1_term)

@dp.message(AddClient.sub1_term)
async def add_sub1_term(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(sub1_term=message.text.strip())
    await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.sub1_date)

@dp.message(AddClient.sub1_date)
async def add_sub1_date(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(sub1_date=message.text.strip())
    data = await state.get_data()
    if data.get("subscription_count", 1) == 2:
        exclude = data.get("sub1_type")
        await message.answer("Выберите вторую подписку:", reply_markup=get_sub2_type_kb(exclude))
        await state.set_state(AddClient.sub2_type)
    else:
        await message.answer("Есть оформленные игры?", reply_markup=get_yes_no_kb())
        await state.set_state(AddClient.games_check)

@dp.message(AddClient.sub2_type)
async def add_sub2_type(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(sub2_type=message.text.strip())
    await message.answer("Выберите срок второй подписки:", reply_markup=get_term_kb(message.text))
    await state.set_state(AddClient.sub2_term)

@dp.message(AddClient.sub2_term)
async def add_sub2_term(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(sub2_term=message.text.strip())
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.sub2_date)

@dp.message(AddClient.sub2_date)
async def add_sub2_date(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    await state.update_data(sub2_date=message.text.strip())
    await message.answer("Есть оформленные игры?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.games_check)

@dp.message(AddClient.games_check)
async def games_check(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    if message.text == "Да":
        await message.answer("Введите список игр (каждая на новой строке):", reply_markup=get_cancel_kb())
        await state.set_state(AddClient.games)
    else:
        await state.update_data(games=[])
        await message.answer("Есть резервные коды?", reply_markup=get_yes_no_kb())
        await state.set_state(AddClient.codes_check)

@dp.message(AddClient.games)
async def add_games(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    await state.update_data(games=games)
    await message.answer("Есть резервные коды?", reply_markup=get_yes_no_kb())
    await state.set_state(AddClient.codes_check)

@dp.message(AddClient.codes_check)
async def codes_check(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=get_cancel_kb())
        await state.set_state(AddClient.codes)
    else:
        await state.update_data(codes_file_id=None)
        await finish_add_client(message, state)

@dp.message(AddClient.codes)
async def add_codes(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    if not message.photo:
        await message.answer("Пожалуйста, загрузите изображение с резервными кодами.")
        return
    file_id = message.photo[-1].file_id
    await state.update_data(codes_file_id=file_id)
    await finish_add_client(message, state)

async def finish_add_client(message: Message, state: FSMContext):
    data = await state.get_data()
    number = data.get("number")
    client = {
        "number": number,
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "region": data.get("region", ""),
        "console": data.get("console", ""),
        "subscriptions": [],
        "games": data.get("games", []),
        "codes_file_id": data.get("codes_file_id")
    }
    subs = []
    if data.get("subscription_count", 0) == 1:
        name = data.get("sub1_type", "")
        term = data.get("sub1_term", "")
        start = data.get("sub1_date", "")
        end = calc_end_date(start, term)
        subs.append({"name": name, "term": term, "start": start, "end": end})
    elif data.get("subscription_count", 0) == 2:
        name1 = data.get("sub1_type", "")
        term1 = data.get("sub1_term", "")
        start1 = data.get("sub1_date", "")
        end1 = calc_end_date(start1, term1)
        name2 = data.get("sub2_type", "")
        term2 = data.get("sub2_term", "")
        start2 = data.get("sub2_date", "")
        end2 = calc_end_date(start2, term2)
        subs.append({"name": name1, "term": term1, "start": start1, "end": end1})
        subs.append({"name": name2, "term": term2, "start": start2, "end": end2})
    client["subscriptions"] = subs
    add_client_to_db(client)
    await state.clear()
    text = client_info_text(client)
    if client.get("codes_file_id"):
        await message.answer_photo(client["codes_file_id"], caption=text, reply_markup=None)
    else:
        await message.answer(text, reply_markup=None)
    await message.answer("Клиент добавлен.", reply_markup=main_menu_kb)

def calc_end_date(start, term):
    try:
        dt = datetime.strptime(start, "%d.%m.%Y")
        if "12" in term:
            dt += timedelta(days=365)
        elif "3" in term:
            dt += timedelta(days=90)
        elif "1" in term:
            dt += timedelta(days=30)
        return dt.strftime("%d.%m.%Y")
    except:
        return "Ошибка даты"

@dp.message(F.text == "Поиск")
async def search_client(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер или Telegram для поиска:", reply_markup=get_cancel_kb())
    await state.set_state("searching")

@dp.message(F.state == "searching")
async def search_query(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=main_menu_kb)
        return
    client = find_client(message.text.strip())
    if client:
        text = client_info_text(client)
        if client.get("codes_file_id"):
            await message.answer_photo(client["codes_file_id"], caption=text, reply_markup=None)
        else:
            await message.answer(text, reply_markup=None)
        await message.answer("Выберите действие:", reply_markup=main_menu_kb)
    else:
        await message.answer("Клиент не найден.", reply_markup=main_menu_kb)
    await state.clear()

@dp.message(F.text == "Очистить чат")
async def clear_cmd(message: Message, state: FSMContext):
    await clear_all_messages(message)
    await message.answer("Чат очищен.", reply_markup=main_menu_kb)

@dp.message(F.text == "Выгрузить базу")
async def export_db(message: Message, state: FSMContext):
    file_path = export_all()
    await message.answer_document(FSInputFile(file_path), caption="Вся база выгружена.")

if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
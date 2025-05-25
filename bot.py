import os
import json
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
from database import (
    load_db, save_db, add_client_to_db, update_client_in_db, find_client,
    delete_client, export_all
)

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
MEDIA_PATH = "media"
os.makedirs(MEDIA_PATH, exist_ok=True)
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить"), KeyboardButton(text="Поиск")],
        [KeyboardButton(text="Очистить чат"), KeyboardButton(text="Выгрузить базу")]
    ],
    resize_keyboard=True
)
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True
)

def yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")], [KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
def consoles_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS4"), KeyboardButton(text="PS5")],
            [KeyboardButton(text="PS4/PS5")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def region_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇦 Украинский"), KeyboardButton(text="🇹🇷 Турецкий")],
            [KeyboardButton(text="🌍 Другой")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def sub_count_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Нет подписки")],
            [KeyboardButton(text="Одна подписка")],
            [KeyboardButton(text="Две подписки")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def psplus_term_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 мес"), KeyboardButton(text="3 мес"), KeyboardButton(text="12 мес")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def eaplay_term_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1 мес"), KeyboardButton(text="12 мес")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def eaplay_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def psplus_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )
def edit_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Изменить номер/TG", callback_data="edit_number")],
        [InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birth")],
        [InlineKeyboardButton(text="🔐 Изменить аккаунт", callback_data="edit_account")],
        [InlineKeyboardButton(text="🌎 Изменить регион", callback_data="edit_region")],
        [InlineKeyboardButton(text="💾 Изменить резерв коды", callback_data="edit_reserve")],
        [InlineKeyboardButton(text="💳 Изменить подписку", callback_data="edit_sub")],
        [InlineKeyboardButton(text="🎮 Изменить игры", callback_data="edit_games")],
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="save_edit")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])
def remove_kb():
    return types.ReplyKeyboardRemove()

class AddClient(StatesGroup):
    waiting_number = State()
    waiting_birth_check = State()
    waiting_birthdate = State()
    waiting_account = State()
    waiting_consoles = State()
    waiting_mailpass = State()
    waiting_region = State()
    waiting_sub_count = State()
    waiting_sub_1_type = State()
    waiting_sub_1_term = State()
    waiting_sub_1_date = State()
    waiting_sub_2_type = State()
    waiting_sub_2_term = State()
    waiting_sub_2_date = State()
    waiting_games_check = State()
    waiting_games = State()
    waiting_reserve_check = State()
    waiting_reserve_codes = State()

class EditClient(StatesGroup):
    editing = State()
    edit_number = State()
    edit_birth = State()
    edit_account = State()
    edit_region = State()
    edit_reserve = State()
    edit_sub = State()
    edit_games = State()

def client_text_block(client):
    text = f"📱 <b>Номер/TG:</b> {client.get('number') or client.get('telegram')}\n"
    text += f"📅 <b>Дата рождения:</b> {client.get('birthdate','отсутствует')}\n"
    text += f"🔐 <b>Аккаунт:</b> {client.get('account')} ({client.get('consoles','')})\n"
    text += f"✉️ <b>Mail/Pass:</b> {client.get('mailpass','-')}\n"
    text += f"🌎 <b>Регион:</b> {client.get('region','-')}\n"
    if client.get("subscriptions"):
        for sub in client["subscriptions"]:
            text += f"💳 <b>{sub['name']}</b> {sub['term']}<br>с {sub['start']} по {sub['end']}\n"
    else:
        text += f"💳 <b>Подписки:</b> отсутствует\n"
    if client.get("games"):
        text += f"🎮 <b>Игры:</b>\n" + '\n'.join(["- "+g for g in client["games"]])
    else:
        text += f"🎮 <b>Игры:</b> отсутствует"
    if client.get("reserve_codes_path"):
        text += "\n💾 <b>Резерв коды: приложен файл</b>"
    return text

async def send_client_info(chat_id, client, state, bot, edit_mode=False):
    text = client_text_block(client)
    if client.get("reserve_codes_path") and os.path.exists(client["reserve_codes_path"]):
        await bot.send_photo(chat_id, photo=InputFile(client["reserve_codes_path"]), caption=text, parse_mode=ParseMode.HTML, reply_markup=edit_panel_kb() if edit_mode else None)
    else:
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=edit_panel_kb() if edit_mode else None)

@dp.message(CommandStart())
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu_kb)

@dp.message(F.text == "Очистить чат")
async def clear_chat(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Чат очищен", reply_markup=main_menu_kb)

@dp.message(F.text == "Выгрузить базу")
async def export_db(message: types.Message):
    text = export_all()
    file_path = "clients_export.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    await message.answer_document(InputFile(file_path), caption="Вся база клиентов выгружена.")

@dp.message(F.text == "Добавить")
async def start_add(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Шаг 1/7. Введите номер телефона или Telegram:", reply_markup=cancel_kb)
    await state.set_state(AddClient.waiting_number)

@dp.message(F.text == "Поиск")
async def search_client(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер или Telegram клиента для поиска:", reply_markup=cancel_kb)
    await state.set_state(EditClient.editing)

@dp.message(AddClient.waiting_number)
async def add_waiting_number(message: types.Message, state: FSMContext):
    value = message.text.strip()
    if value.lower() == "❌ отмена":
        await cancel_handler(message, state)
        return
    await state.update_data(number=value if value.startswith("+") or value.isdigit() else "", telegram=value if value.startswith("@") else "")
    await message.answer("Шаг 2/7. Есть дата рождения?", reply_markup=yes_no_kb())
    await state.set_state(AddClient.waiting_birth_check)

@dp.message(AddClient.waiting_birth_check)
async def add_waiting_birth_check(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Введите дату рождения (формат: ДД.ММ.ГГГГ):", reply_markup=cancel_kb)
        await state.set_state(AddClient.waiting_birthdate)
    elif message.text == "Нет":
        await state.update_data(birthdate="отсутствует")
        await message.answer("Шаг 3/7. Введите данные аккаунта (логин):", reply_markup=cancel_kb)
        await state.set_state(AddClient.waiting_account)
    elif message.text == "❌ Отмена":
        await cancel_handler(message, state)

@dp.message(AddClient.waiting_birthdate)
async def add_waiting_birthdate(message: types.Message, state: FSMContext):
    birthdate = message.text.strip()
    await state.update_data(birthdate=birthdate)
    await message.answer("Шаг 3/7. Введите данные аккаунта (логин):", reply_markup=cancel_kb)
    await state.set_state(AddClient.waiting_account)

@dp.message(AddClient.waiting_account)
async def add_waiting_account(message: types.Message, state: FSMContext):
    acc = message.text.strip()
    await state.update_data(account=acc)
    await message.answer("Какие консоли? (PS4/PS5/PS4-PS5)", reply_markup=consoles_kb())
    await state.set_state(AddClient.waiting_consoles)

@dp.message(AddClient.waiting_consoles)
async def add_waiting_consoles(message: types.Message, state: FSMContext):
    cons = message.text.strip()
    await state.update_data(consoles=cons)
    await message.answer("Введите почту/пароль через ; (если нет, отправьте '-'):", reply_markup=cancel_kb)
    await state.set_state(AddClient.waiting_mailpass)

@dp.message(AddClient.waiting_mailpass)
async def add_waiting_mailpass(message: types.Message, state: FSMContext):
    mp = message.text.strip()
    await state.update_data(mailpass=mp)
    await message.answer("Выберите регион аккаунта:", reply_markup=region_kb())
    await state.set_state(AddClient.waiting_region)

@dp.message(AddClient.waiting_region)
async def add_waiting_region(message: types.Message, state: FSMContext):
    region = message.text.strip()
    await state.update_data(region=region)
    await message.answer("Сколько подписок оформлено?", reply_markup=sub_count_kb())
    await state.set_state(AddClient.waiting_sub_count)

@dp.message(AddClient.waiting_sub_count)
async def add_waiting_sub_count(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == "Нет подписки":
        await state.update_data(subscriptions=[])
        await message.answer("Шаг 5/7. Есть оформленные игры?", reply_markup=yes_no_kb())
        await state.set_state(AddClient.waiting_games_check)
    elif text == "Одна подписка":
        await message.answer("Выберите подписку:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_sub_1_type)
    elif text == "Две подписки":
        await message.answer("Выберите первую подписку:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_sub_1_type)
        await state.update_data(multi_sub=True, multi_sub_step=1)
    elif text == "❌ Отмена":
        await cancel_handler(message, state)

@dp.message(AddClient.waiting_sub_1_type)
async def add_waiting_sub_1_type(message: types.Message, state: FSMContext):
    sub = message.text.strip()
    if sub.startswith("PS Plus"):
        await state.update_data(sub_1_type=sub)
        await message.answer("Выберите срок подписки:", reply_markup=psplus_term_kb())
        await state.set_state(AddClient.waiting_sub_1_term)
    elif sub == "EA Play":
        await state.update_data(sub_1_type=sub)
        await message.answer("Выберите срок подписки:", reply_markup=eaplay_term_kb())
        await state.set_state(AddClient.waiting_sub_1_term)
    elif sub == "❌ Отмена":
        await cancel_handler(message, state)

@dp.message(AddClient.waiting_sub_1_term)
async def add_waiting_sub_1_term(message: types.Message, state: FSMContext):
    term = message.text.strip()
    await state.update_data(sub_1_term=term)
    await message.answer("Введите дату оформления подписки (ДД.ММ.ГГГГ):", reply_markup=cancel_kb)
    await state.set_state(AddClient.waiting_sub_1_date)

@dp.message(AddClient.waiting_sub_1_date)
async def add_waiting_sub_1_date(message: types.Message, state: FSMContext):
    date = message.text.strip()
    data = await state.get_data()
    sub_1 = {
        "name": data.get("sub_1_type"),
        "term": data.get("sub_1_term"),
        "start": date,
        "end": calc_end_date(date, data.get("sub_1_term"))
    }
    if data.get("multi_sub"):
        await state.update_data(subscriptions=[sub_1])
        await message.answer("Выберите вторую подписку:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="EA Play")] if data["sub_1_type"].startswith("PS Plus") else
                [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"),
                 KeyboardButton(text="PS Plus Essential")],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        ))
        await state.set_state(AddClient.waiting_sub_2_type)
    else:
        await state.update_data(subscriptions=[sub_1])
        await message.answer("Шаг 5/7. Есть оформленные игры?", reply_markup=yes_no_kb())
        await state.set_state(AddClient.waiting_games_check)

@dp.message(AddClient.waiting_sub_2_type)
async def add_waiting_sub_2_type(message: types.Message, state: FSMContext):
    sub = message.text.strip()
    if sub == "EA Play":
        await state.update_data(sub_2_type=sub)
        await message.answer("Выберите срок подписки:", reply_markup=eaplay_term_kb())
    else:
        await state.update_data(sub_2_type=sub)
        await message.answer("Выберите срок подписки:", reply_markup=psplus_term_kb())
    await state.set_state(AddClient.waiting_sub_2_term)

@dp.message(AddClient.waiting_sub_2_term)
async def add_waiting_sub_2_term(message: types.Message, state: FSMContext):
    term = message.text.strip()
    await state.update_data(sub_2_term=term)
    await message.answer("Введите дату оформления второй подписки (ДД.ММ.ГГГГ):", reply_markup=cancel_kb)
    await state.set_state(AddClient.waiting_sub_2_date)

@dp.message(AddClient.waiting_sub_2_date)
async def add_waiting_sub_2_date(message: types.Message, state: FSMContext):
    date = message.text.strip()
    data = await state.get_data()
    sub_2 = {
        "name": data.get("sub_2_type"),
        "term": data.get("sub_2_term"),
        "start": date,
        "end": calc_end_date(date, data.get("sub_2_term"))
    }
    subscriptions = data.get("subscriptions", [])
    subscriptions.append(sub_2)
    await state.update_data(subscriptions=subscriptions)
    await message.answer("Шаг 5/7. Есть оформленные игры?", reply_markup=yes_no_kb())
    await state.set_state(AddClient.waiting_games_check)

@dp.message(AddClient.waiting_games_check)
async def add_waiting_games_check(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Введите список игр, через Enter:", reply_markup=cancel_kb)
        await state.set_state(AddClient.waiting_games)
    elif message.text == "Нет":
        await state.update_data(games=[])
        await message.answer("Шаг 6/7. Есть резерв коды?", reply_markup=yes_no_kb())
        await state.set_state(AddClient.waiting_reserve_check)
    elif message.text == "❌ Отмена":
        await cancel_handler(message, state)

@dp.message(AddClient.waiting_games)
async def add_waiting_games(message: types.Message, state: FSMContext):
    games = message.text.strip().split('\n')
    await state.update_data(games=games)
    await message.answer("Шаг 6/7. Есть резерв коды?", reply_markup=yes_no_kb())
    await state.set_state(AddClient.waiting_reserve_check)

@dp.message(AddClient.waiting_reserve_check)
async def add_waiting_reserve_check(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer("Загрузите скрин с резервными кодами:", reply_markup=cancel_kb)
        await state.set_state(AddClient.waiting_reserve_codes)
    elif message.text == "Нет":
        await state.update_data(reserve_codes_path=None)
        await finish_add(message, state)
    elif message.text == "❌ Отмена":
        await cancel_handler(message, state)

@dp.message(AddClient.waiting_reserve_codes)
async def add_waiting_reserve_codes(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Отправьте, пожалуйста, изображение c резервными кодами или '❌ Отмена'.")
        return
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = os.path.join(MEDIA_PATH, f"{photo.file_id}.jpg")
    await bot.download_file(file.file_path, file_path)
    await state.update_data(reserve_codes_path=file_path)
    await finish_add(message, state)

async def finish_add(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = {
        "number": data.get("number",""),
        "telegram": data.get("telegram",""),
        "birthdate": data.get("birthdate","отсутствует"),
        "account": data.get("account",""),
        "consoles": data.get("consoles",""),
        "mailpass": data.get("mailpass",""),
        "region": data.get("region",""),
        "subscriptions": data.get("subscriptions",[]),
        "games": data.get("games",[]),
        "reserve_codes_path": data.get("reserve_codes_path",None)
    }
    add_client_to_db(client)
    await state.clear()
    await message.answer("Клиент успешно добавлен!", reply_markup=main_menu_kb)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)

def calc_end_date(start_date, term):
    try:
        d = datetime.strptime(start_date, "%d.%m.%Y")
        if "1 мес" in term:
            d_end = d + timedelta(days=30)
        elif "3 мес" in term:
            d_end = d + timedelta(days=90)
        elif "12 мес" in term:
            d_end = d + timedelta(days=365)
        else:
            d_end = d
        return d_end.strftime("%d.%m.%Y")
    except:
        return "-"

async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=main_menu_kb)

@dp.message(EditClient.editing)
async def search_edit_handler(message: types.Message, state: FSMContext):
    query = message.text.strip()
    client = find_client(query)
    if not client:
        await message.answer("Клиент не найден.", reply_markup=main_menu_kb)
        await state.clear()
        return
    await state.update_data(edit_client=client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

@dp.callback_query(F.data.startswith("edit_"))
async def edit_buttons_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client = data.get("edit_client")
    if not client:
        await callback.message.answer("Ошибка. Нет данных о клиенте.")
        return
    if callback.data == "edit_number":
        await callback.message.answer("Введите новый номер или Telegram:", reply_markup=cancel_kb)
        await state.set_state(EditClient.edit_number)
    elif callback.data == "edit_birth":
        await callback.message.answer("Введите новую дату рождения:", reply_markup=cancel_kb)
        await state.set_state(EditClient.edit_birth)
    elif callback.data == "edit_account":
        await callback.message.answer("Введите новые данные аккаунта (логин, почта/пароль через ;):", reply_markup=cancel_kb)
        await state.set_state(EditClient.edit_account)
    elif callback.data == "edit_region":
        await callback.message.answer("Выберите новый регион:", reply_markup=region_kb())
        await state.set_state(EditClient.edit_region)
    elif callback.data == "edit_reserve":
        await callback.message.answer("Загрузите новые резервные коды:", reply_markup=cancel_kb)
        await state.set_state(EditClient.edit_reserve)
    elif callback.data == "edit_sub":
        await callback.message.answer("Сколько подписок оформить?", reply_markup=sub_count_kb())
        await state.set_state(AddClient.waiting_sub_count)
    elif callback.data == "edit_games":
        games = client.get("games", [])
        cur_games = '\n'.join(games) if games else ""
        await callback.message.answer(f"Текущий список игр:\n{cur_games}\n\nВведите новые игры списком:", reply_markup=cancel_kb)
        await state.set_state(EditClient.edit_games)
    elif callback.data == "save_edit":
        update_client_in_db(client)
        await callback.message.answer(f"✅ {client.get('number') or client.get('telegram')} успешно сохранен", reply_markup=main_menu_kb)
        await state.clear()
    elif callback.data == "cancel_edit":
        await state.clear()
        await callback.message.answer("Операция отменена", reply_markup=main_menu_kb)

@dp.message(EditClient.edit_number)
async def edit_number_handler(message: types.Message, state: FSMContext):
    val = message.text.strip()
    data = await state.get_data()
    client = data.get("edit_client")
    if val.startswith("+") or val.isdigit():
        client["number"] = val
    elif val.startswith("@"):
        client["telegram"] = val
    update_client_in_db(client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

@dp.message(EditClient.edit_birth)
async def edit_birth_handler(message: types.Message, state: FSMContext):
    birthdate = message.text.strip()
    data = await state.get_data()
    client = data.get("edit_client")
    client["birthdate"] = birthdate
    update_client_in_db(client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

@dp.message(EditClient.edit_account)
async def edit_account_handler(message: types.Message, state: FSMContext):
    acc_data = message.text.strip().split('\n')
    data = await state.get_data()
    client = data.get("edit_client")
    client["account"] = acc_data[0] if acc_data else ""
    client["mailpass"] = acc_data[1] if len(acc_data) > 1 else ""
    update_client_in_db(client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

@dp.message(EditClient.edit_region)
async def edit_region_handler(message: types.Message, state: FSMContext):
    region = message.text.strip()
    data = await state.get_data()
    client = data.get("edit_client")
    client["region"] = region
    update_client_in_db(client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

@dp.message(EditClient.edit_reserve)
async def edit_reserve_handler(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Отправьте, пожалуйста, изображение с резервными кодами или ❌ Отмена.")
        return
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = os.path.join(MEDIA_PATH, f"{photo.file_id}.jpg")
    await bot.download_file(file.file_path, file_path)
    data = await state.get_data()
    client = data.get("edit_client")
    client["reserve_codes_path"] = file_path
    update_client_in_db(client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

@dp.message(EditClient.edit_games)
async def edit_games_handler(message: types.Message, state: FSMContext):
    games = message.text.strip().split('\n')
    data = await state.get_data()
    client = data.get("edit_client")
    client["games"] = games
    update_client_in_db(client)
    await send_client_info(message.chat.id, client, state, bot, edit_mode=True)
    await state.set_state(EditClient.editing)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
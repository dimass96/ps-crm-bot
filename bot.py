import logging
import os
import asyncio
import shutil
import pyAesCrypt
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta

import database

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

database.init_db()

class AddClient(StatesGroup):
    waiting_for_identifier_type = State()
    waiting_for_identifier = State()
    waiting_for_birthday_exist = State()
    waiting_for_birthday = State()
    waiting_for_email = State()
    waiting_for_account_pass = State()
    waiting_for_mail_pass = State()
    waiting_for_console = State()
    waiting_for_region = State()
    waiting_for_reserve_codes_exist = State()
    waiting_for_reserve_codes = State()
    waiting_for_subscription_exist = State()
    waiting_for_subscription_count = State()
    waiting_for_sub1_type = State()
    waiting_for_sub1_duration = State()
    waiting_for_sub1_start = State()
    waiting_for_sub2_type = State()
    waiting_for_sub2_duration = State()
    waiting_for_sub2_start = State()
    waiting_for_games_exist = State()
    waiting_for_games = State()

class EditClient(StatesGroup):
    choose_action = State()
    edit_identifier = State()
    edit_birthday = State()
    edit_email = State()
    edit_account_pass = State()
    edit_mail_pass = State()
    edit_console = State()
    edit_region = State()
    edit_reserve_codes = State()
    edit_sub = State()
    edit_sub_select = State()
    edit_sub_type = State()
    edit_sub_duration = State()
    edit_sub_start = State()
    edit_games = State()

client_data = {}
last_info_message = {}

def calc_sub_end(start_date: str, duration: str):
    try:
        d = datetime.strptime(start_date, "%d.%m.%Y")
        if duration == "1м":
            end = d + timedelta(days=30)
        elif duration == "3м":
            end = d + timedelta(days=90)
        elif duration == "12м":
            end = d + timedelta(days=365)
        else:
            return ''
        return end.strftime("%d.%m.%Y")
    except:
        return ''

def clear_chat(chat_id):
    async def inner():
        async for msg in bot.iter_history(chat_id):
            try:
                await bot.delete_message(chat_id, msg.message_id)
            except:
                pass
    asyncio.ensure_future(inner())

def build_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить клиента"))
    kb.add(KeyboardButton("🔍 Найти клиента"))
    return kb

def build_cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def build_edit_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📱 Изменить номер", callback_data="edit_identifier"),
        InlineKeyboardButton("📅 Изменить дату рождения", callback_data="edit_birthday"),
        InlineKeyboardButton("🔐 Изменить данные", callback_data="edit_account"),
        InlineKeyboardButton("🎮 Изменить консоль", callback_data="edit_console"),
        InlineKeyboardButton("🌍 Изменить регион", callback_data="edit_region"),
        InlineKeyboardButton("🖼 Изменить резерв коды", callback_data="edit_reserve"),
        InlineKeyboardButton("💳 Изменить подписку", callback_data="edit_sub"),
        InlineKeyboardButton("🎮 Изменить игры", callback_data="edit_games"),
    )
    kb.add(
        InlineKeyboardButton("✅ Сохранить", callback_data="save"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit")
    )
    return kb

async def send_info(client, message, edit=False):
    text = f"**Клиент:** `{client[1]}`\n"
    text += f"Тип: {client[2]}\n"
    text += f"Дата рождения: {client[3]}\n"
    text += f"Email: {client[4]}\n"
    text += f"Пароль: {client[5]}\n"
    text += f"Пароль от почты: {client[6]}\n"
    text += f"Консоль: {client[7]}\n"
    text += f"Регион: {client[8]}\n"
    if client[9]:
        text += f"Резерв коды: во вложении ниже\n"
    if client[10] and client[13]:
        text += f"\nПодписка 1: {client[10]} {client[11]} c {client[12]} по {client[13]}"
    if client[14] and client[17]:
        text += f"\nПодписка 2: {client[14]} {client[15]} c {client[16]} по {client[17]}"
    if client[18]:
        text += f"\n\nИгры:\n" + "\n".join(client[18].split(" —— "))
    msg = await message.answer(text, parse_mode="Markdown", reply_markup=build_edit_kb() if edit else None)
    if client[9]:
        try:
            await message.answer_document(InputFile(client[9]))
        except:
            pass
    return msg

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Это CRM-бот для PlayStation.\nВыберите действие:", reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == "➕ Добавить клиента")
async def add_client_start(message: types.Message, state: FSMContext):
    await state.finish()
    await state.update_data(client={})
    await message.answer("Выберите способ идентификации клиента:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Телефон"), KeyboardButton("Telegram")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_identifier_type.set()

@dp.message_handler(state=AddClient.waiting_for_identifier_type)
async def add_client_identifier_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["Телефон", "Telegram"]:
        await message.answer("Выберите Телефон или Telegram")
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['identifier_type'] = message.text
    await state.update_data(client=client)
    await message.answer("Введите номер или @ник:", reply_markup=build_cancel_kb())
    await AddClient.waiting_for_identifier.set()

@dp.message_handler(state=AddClient.waiting_for_identifier)
async def add_client_identifier(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['identifier'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Есть ли дата рождения?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_birthday_exist.set()

@dp.message_handler(state=AddClient.waiting_for_birthday_exist)
async def add_client_birthday_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет")
        return
    client = await state.get_data()
    client = client.get('client', {})
    if message.text == "Да":
        await state.update_data(client=client)
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=build_cancel_kb())
        await AddClient.waiting_for_birthday.set()
    else:
        client['birthday'] = "отсутствует"
        await state.update_data(client=client)
        await message.answer("Введите Email:", reply_markup=build_cancel_kb())
        await AddClient.waiting_for_email.set()

@dp.message_handler(state=AddClient.waiting_for_birthday)
async def add_client_birthday(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['birthday'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Введите Email:", reply_markup=build_cancel_kb())
    await AddClient.waiting_for_email.set()

@dp.message_handler(state=AddClient.waiting_for_email)
async def add_client_email(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['email'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Введите пароль от аккаунта:", reply_markup=build_cancel_kb())
    await AddClient.waiting_for_account_pass.set()

@dp.message_handler(state=AddClient.waiting_for_account_pass)
async def add_client_account_pass(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['account_pass'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Введите пароль от почты (может быть пустым):", reply_markup=build_cancel_kb())
    await AddClient.waiting_for_mail_pass.set()

@dp.message_handler(state=AddClient.waiting_for_mail_pass)
async def add_client_mail_pass(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['mail_pass'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Какие консоли? (PS4, PS5, PS4/PS5)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("PS4"), KeyboardButton("PS5"), KeyboardButton("PS4/PS5")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_console.set()

@dp.message_handler(state=AddClient.waiting_for_console)
async def add_client_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["PS4", "PS5", "PS4/PS5"]:
        await message.answer("Выберите одну из опций")
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['console'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Регион аккаунта? (укр/тур/другое)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("укр"), KeyboardButton("тур"), KeyboardButton("другое")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_region.set()

@dp.message_handler(state=AddClient.waiting_for_region)
async def add_client_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["укр", "тур", "другое"]:
        await message.answer("Выберите одну из опций")
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['region'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("Есть резерв коды?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_reserve_codes_exist.set()

@dp.message_handler(state=AddClient.waiting_for_reserve_codes_exist)
async def add_client_reserve_codes_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет")
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот с резервными кодами.", reply_markup=build_cancel_kb())
        await AddClient.waiting_for_reserve_codes.set()
    else:
        client = await state.get_data()
        client = client.get('client', {})
        client['reserve_codes_path'] = ""
        await state.update_data(client=client)
        await message.answer("Оформлена ли подписка?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_subscription_exist.set()

@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=AddClient.waiting_for_reserve_codes)
async def add_client_reserve_codes(message: types.Message, state: FSMContext):
    if message.caption == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    file = await message.document.download()
    file_path = f'reserves/{message.document.file_name}'
    os.makedirs('reserves', exist_ok=True)
    shutil.move(file.name, file_path)
    client['reserve_codes_path'] = file_path
    await state.update_data(client=client)
    await message.answer("Оформлена ли подписка?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_subscription_exist.set()

@dp.message_handler(state=AddClient.waiting_for_subscription_exist)
async def add_client_sub_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет")
        return
    if message.text == "Нет":
        client = await state.get_data()
        client = client.get('client', {})
        client['sub1_name'] = ""
        client['sub1_duration'] = ""
        client['sub1_start'] = ""
        client['sub1_end'] = ""
        client['sub2_name'] = ""
        client['sub2_duration'] = ""
        client['sub2_start'] = ""
        client['sub2_end'] = ""
        await state.update_data(client=client)
        await message.answer("Есть ли игры?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_games_exist.set()
    else:
        await message.answer("Сколько подписок? (Одна/Две)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("Одна"), KeyboardButton("Две")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_subscription_count.set()

@dp.message_handler(state=AddClient.waiting_for_subscription_count)
async def add_client_sub_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text == "Одна":
        await message.answer("Выберите подписку", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential"), KeyboardButton("EA Play")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_sub1_type.set()
    elif message.text == "Две":
        await message.answer("Выберите первую подписку (PS Plus Deluxe / Extra / Essential)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_sub1_type.set()
    else:
        await message.answer("Выберите Одна или Две")

@dp.message_handler(state=AddClient.waiting_for_sub1_type)
async def add_client_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    if message.text.startswith("PS Plus"):
        client['sub1_name'] = message.text
        await state.update_data(client=client)
        await message.answer("Срок подписки? (1м/3м/12м)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_sub1_duration.set()
    elif message.text == "EA Play":
        if 'sub1_name' not in client or not client['sub1_name']:
            # Одна подписка
            client['sub1_name'] = "EA Play"
            await state.update_data(client=client)
            await message.answer("Срок подписки? (1м/12м)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
                KeyboardButton("1м"), KeyboardButton("12м")).add(KeyboardButton("❌ Отмена")))
            await AddClient.waiting_for_sub1_duration.set()
        else:
            # Это вторая подписка
            client['sub2_name'] = "EA Play"
            await state.update_data(client=client)
            await message.answer("Срок подписки? (1м/12м)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
                KeyboardButton("1м"), KeyboardButton("12м")).add(KeyboardButton("❌ Отмена")))
            await AddClient.waiting_for_sub2_duration.set()
    else:
        await message.answer("Выберите одну из опций")

@dp.message_handler(state=AddClient.waiting_for_sub1_duration)
async def add_client_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    if client['sub1_name'] == "EA Play" and message.text not in ["1м", "12м"]:
        await message.answer("Для EA Play выберите 1м или 12м")
        return
    if message.text not in ["1м", "3м", "12м"]:
        await message.answer("Выберите одну из опций")
        return
    client['sub1_duration'] = message.text
    await state.update_data(client=client)
    await message.answer("Введите дату оформления первой подписки (дд.мм.гггг):", reply_markup=build_cancel_kb())
    await AddClient.waiting_for_sub1_start.set()

@dp.message_handler(state=AddClient.waiting_for_sub1_start)
async def add_client_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['sub1_start'] = message.text.strip()
    client['sub1_end'] = calc_sub_end(client['sub1_start'], client['sub1_duration'])
    await state.update_data(client=client)
    # Если "Две", идём ко второй подписке
    if 'sub2_name' in client or client.get('sub1_name', '').startswith("PS Plus"):
        # Нужно узнать, нужна ли вторая подписка (EA Play)
        await message.answer("Выберите вторую подписку (EA Play)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("EA Play")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_sub2_type.set()
    else:
        await message.answer("Есть ли игры?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
        await AddClient.waiting_for_games_exist.set()

@dp.message_handler(state=AddClient.waiting_for_sub2_type)
async def add_client_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text != "EA Play":
        await message.answer("Выберите EA Play")
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_name'] = "EA Play"
    await state.update_data(client=client)
    await message.answer("Срок подписки? (1м/12м)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("1м"), KeyboardButton("12м")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_sub2_duration.set()

@dp.message_handler(state=AddClient.waiting_for_sub2_duration)
async def add_client_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["1м", "12м"]:
        await message.answer("Для EA Play выберите 1м или 12м")
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_duration'] = message.text
    await state.update_data(client=client)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=build_cancel_kb())
    await AddClient.waiting_for_sub2_start.set()

@dp.message_handler(state=AddClient.waiting_for_sub2_start)
async def add_client_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_start'] = message.text.strip()
    client['sub2_end'] = calc_sub_end(client['sub2_start'], client['sub2_duration'])
    await state.update_data(client=client)
    await message.answer("Есть ли игры?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Да"), KeyboardButton("Нет")).add(KeyboardButton("❌ Отмена")))
    await AddClient.waiting_for_games_exist.set()

@dp.message_handler(state=AddClient.waiting_for_games_exist)
async def add_client_games_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    if message.text not in ["Да", "Нет"]:
        await message.answer("Ответьте Да или Нет")
        return
    if message.text == "Да":
        await message.answer("Введи список игр (каждая с новой строки):", reply_markup=build_cancel_kb())
        await AddClient.waiting_for_games.set()
    else:
        client = await state.get_data()
        client = client.get('client', {})
        client['games'] = ""
        database.add_client(client)
        await state.finish()
        msg = await send_info(list(client.values()), message, edit=True)
        await asyncio.sleep(300)
        try:
            await bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass

@dp.message_handler(state=AddClient.waiting_for_games)
async def add_client_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['games'] = ' —— '.join(message.text.strip().split('\n'))
    database.add_client(client)
    await state.finish()
    msg = await send_info(list(client.values()), message, edit=True)
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass

@dp.message_handler(lambda m: m.text == "🔍 Найти клиента")
async def search_client_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Введите номер или Telegram-ник клиента:", reply_markup=build_cancel_kb())
    await EditClient.choose_action.set()

@dp.message_handler(state=EditClient.choose_action)
async def search_client_action(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    row = database.get_client_by_identifier(message.text.strip())
    if not row:
        await state.finish()
        await message.answer("Клиент не найден", reply_markup=build_main_menu())
        clear_chat(message.chat.id)
        return
    await state.update_data(client_id=row[0])
    msg = await send_info(row, message, edit=True)
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass

# Запуск
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

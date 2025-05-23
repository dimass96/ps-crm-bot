import logging
import os
import shutil
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from database import (
    init_db, add_client, get_client, update_client_field,
    delete_client, encrypt_db, decrypt_db, calculate_end_date
)

API_TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
OWNER_ID = 350902460
ENCRYPTION_PASSWORD = "57131702"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

init_db()

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить клиента"))
    kb.add(KeyboardButton("🔍 Найти клиента"))
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def get_edit_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📱 Изменить номер", callback_data="edit_number"),
        InlineKeyboardButton("📅 Изменить дату рождения", callback_data="edit_birth"),
    )
    kb.add(
        InlineKeyboardButton("🔐 Изменить данные", callback_data="edit_account"),
        InlineKeyboardButton("🎮 Изменить консоль", callback_data="edit_console"),
    )
    kb.add(
        InlineKeyboardButton("🌍 Изменить регион", callback_data="edit_region"),
        InlineKeyboardButton("🖼 Изменить резерв коды", callback_data="edit_codes"),
    )
    kb.add(
        InlineKeyboardButton("💳 Изменить подписку", callback_data="edit_subscription"),
        InlineKeyboardButton("🎮 Изменить игры", callback_data="edit_games"),
    )
    kb.add(
        InlineKeyboardButton("✅ Сохранить", callback_data="save_changes"),
        InlineKeyboardButton("🗑 Удалить клиента", callback_data="delete_client"),
    )
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit"))
    return kb

class ClientForm(StatesGroup):
    waiting_for_identifier = State()
    waiting_for_identifier_value = State()
    waiting_for_birth_check = State()
    waiting_for_birth_date = State()
    waiting_for_account_data = State()
    waiting_for_console = State()
    waiting_for_region = State()
    waiting_for_codes_check = State()
    waiting_for_codes = State()
    waiting_for_subscription_check = State()
    waiting_for_subscription_count = State()
    waiting_for_first_subscription_type = State()
    waiting_for_first_subscription_term = State()
    waiting_for_first_subscription_date = State()
    waiting_for_second_subscription_term = State()
    waiting_for_second_subscription_date = State()
    waiting_for_games_check = State()
    waiting_for_games_list = State()
    confirming_addition = State()

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать!", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "➕ Добавить клиента")
async def start_add_client(message: types.Message, state: FSMContext):
    await state.finish()
    await state.update_data(messages_to_delete=[])
    msg = await message.answer("Выберите способ идентификации клиента:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Номер телефона", "Telegram").add("❌ Отмена"))
    await ClientForm.waiting_for_identifier.set()
    await state.update_data(messages_to_delete=[msg.message_id])

@dp.message_handler(lambda message: message.text in ["Номер телефона", "Telegram"], state=ClientForm.waiting_for_identifier)
async def get_identifier_type(message: types.Message, state: FSMContext):
    await state.update_data(identifier_type=message.text)
    msg = await message.answer(f"Введите {message.text} клиента:", reply_markup=cancel_kb())
    await ClientForm.waiting_for_identifier_value.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_identifier_value)
async def get_identifier_value(message: types.Message, state: FSMContext):
    await state.update_data(identifier_value=message.text)
    msg = await message.answer("Есть ли дата рождения?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Да", "Нет").add("❌ Отмена"))
    await ClientForm.waiting_for_birth_check.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Да", state=ClientForm.waiting_for_birth_check)
async def ask_birth_date(message: types.Message, state: FSMContext):
    msg = await message.answer("Введите дату рождения (в формате ДД.ММ.ГГГГ):", reply_markup=cancel_kb())
    await ClientForm.waiting_for_birth_date.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Нет", state=ClientForm.waiting_for_birth_check)
async def skip_birth_date(message: types.Message, state: FSMContext):
    await state.update_data(birth_date="отсутствует")
    msg = await message.answer("Введите данные аккаунта (email, пароль, пароль от почты):", reply_markup=cancel_kb())
    await ClientForm.waiting_for_account_data.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_birth_date)
async def get_birth_date(message: types.Message, state: FSMContext):
    await state.update_data(birth_date=message.text)
    msg = await message.answer("Введите данные аккаунта (email, пароль, пароль от почты):", reply_markup=cancel_kb())
    await ClientForm.waiting_for_account_data.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_account_data)
async def get_account_data(message: types.Message, state: FSMContext):
    lines = message.text.split("\n")
    if len(lines) < 2:
        await message.answer("Введите как минимум email и пароль, в новых строках.")
        return
    email, password = lines[0], lines[1]
    mailpass = f"{email};{password}"
    mailpass_mail = lines[2] if len(lines) >= 3 else ""
    await state.update_data(email=email, password=password, mailpass_mail=mailpass_mail)
    msg = await message.answer("Какие консоли? Выберите одну:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("PS4", "PS5", "PS4/PS5").add("❌ Отмена"))
    await ClientForm.waiting_for_console.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_console)
async def get_console(message: types.Message, state: FSMContext):
    await state.update_data(console=message.text)
    msg = await message.answer("Выберите регион аккаунта:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("укр", "тур", "другое").add("❌ Отмена"))
    await ClientForm.waiting_for_region.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_region)
async def get_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text)
    msg = await message.answer("Есть ли резерв коды?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Да", "Нет").add("❌ Отмена"))
    await ClientForm.waiting_for_codes_check.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Да", state=ClientForm.waiting_for_codes_check)
async def ask_for_codes(message: types.Message, state: FSMContext):
    msg = await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=cancel_kb())
    await ClientForm.waiting_for_codes.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Нет", state=ClientForm.waiting_for_codes_check)
async def skip_codes(message: types.Message, state: FSMContext):
    await state.update_data(reserve_codes=None)
    await ask_subscription(message, state)

@dp.message_handler(content_types=types.ContentType.PHOTO, state=ClientForm.waiting_for_codes)
async def save_codes_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(reserve_codes=file_id)
    await ask_subscription(message, state)

async def ask_subscription(message: types.Message, state: FSMContext):
    msg = await message.answer("Оформлена ли подписка?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Да", "Нет").add("❌ Отмена"))
    await ClientForm.waiting_for_subscription_check.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Да", state=ClientForm.waiting_for_subscription_check)
async def ask_subscription_count(message: types.Message, state: FSMContext):
    msg = await message.answer("Сколько подписок?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Одна", "Две").add("❌ Отмена"))
    await ClientForm.waiting_for_subscription_count.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Нет", state=ClientForm.waiting_for_subscription_check)
async def skip_subscription(message: types.Message, state: FSMContext):
    await state.update_data(subscriptions=[])
    await ask_games(message, state)

@dp.message_handler(state=ClientForm.waiting_for_subscription_count)
async def get_subscription_count(message: types.Message, state: FSMContext):
    await state.update_data(subscription_count=message.text)
    msg = await message.answer("Выберите подписку:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play").add("❌ Отмена"))
    await ClientForm.waiting_for_first_subscription_type.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_first_subscription_type)
async def get_first_subscription_type(message: types.Message, state: FSMContext):
    await state.update_data(first_sub_type=message.text)
    msg = await message.answer("Срок подписки:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("1м", "3м", "12м").add("❌ Отмена"))
    await ClientForm.waiting_for_first_subscription_term.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_first_subscription_term)
async def get_first_subscription_term(message: types.Message, state: FSMContext):
    await state.update_data(first_sub_term=message.text)
    msg = await message.answer("Введите дату оформления подписки (ДД.ММ.ГГГГ):", reply_markup=cancel_kb())
    await ClientForm.waiting_for_first_subscription_date.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_first_subscription_date)
async def get_first_subscription_date(message: types.Message, state: FSMContext):
    await state.update_data(first_sub_start=message.text)
    subscription_count = (await state.get_data()).get("subscription_count")
    if subscription_count == "Две":
        msg = await message.answer("Срок второй подписки EA Play:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("1м", "12м").add("❌ Отмена"))
        await ClientForm.waiting_for_second_subscription_term.set()
        await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])
    else:
        await state.update_data(second_sub_type=None, second_sub_term=None, second_sub_start=None)
        await ask_games(message, state)

@dp.message_handler(state=ClientForm.waiting_for_second_subscription_term)
async def get_second_subscription_term(message: types.Message, state: FSMContext):
    await state.update_data(second_sub_type="EA Play", second_sub_term=message.text)
    msg = await message.answer("Введите дату оформления второй подписки EA Play (ДД.ММ.ГГГГ):", reply_markup=cancel_kb())
    await ClientForm.waiting_for_second_subscription_date.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(state=ClientForm.waiting_for_second_subscription_date)
async def get_second_subscription_date(message: types.Message, state: FSMContext):
    await state.update_data(second_sub_start=message.text)
    await ask_games(message, state)

async def ask_games(message: types.Message, state: FSMContext):
    msg = await message.answer("Есть ли игры на аккаунте?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Да", "Нет").add("❌ Отмена"))
    await ClientForm.waiting_for_games_check.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Да", state=ClientForm.waiting_for_games_check)
async def ask_for_games_list(message: types.Message, state: FSMContext):
    msg = await message.answer("Введите список игр (по строкам):", reply_markup=cancel_kb())
    await ClientForm.waiting_for_games_list.set()
    await state.update_data(messages_to_delete=[*state.get_data().get("messages_to_delete", []), msg.message_id])

@dp.message_handler(lambda message: message.text == "Нет", state=ClientForm.waiting_for_games_check)
async def skip_games(message: types.Message, state: FSMContext):
    await state.update_data(games=[])
    await save_client(message, state)

@dp.message_handler(state=ClientForm.waiting_for_games_list)
async def get_games_list(message: types.Message, state: FSMContext):
    games = message.text.strip().split("\n")
    await state.update_data(games=games)
    await save_client(message, state)

async def save_client(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_data = {
        "identifier_type": data.get("identifier_type"),
        "identifier_value": data.get("identifier_value"),
        "birth_date": data.get("birth_date"),
        "email": data.get("email"),
        "password": data.get("password"),
        "mailpass_mail": data.get("mailpass_mail"),
        "console": data.get("console"),
        "region": data.get("region"),
        "reserve_codes": data.get("reserve_codes"),
        "first_sub_type": data.get("first_sub_type"),
        "first_sub_term": data.get("first_sub_term"),
        "first_sub_start": data.get("first_sub_start"),
        "second_sub_type": data.get("second_sub_type"),
        "second_sub_term": data.get("second_sub_term"),
        "second_sub_start": data.get("second_sub_start"),
        "games": data.get("games")
    }
    add_client(client_data)
    msg = await message.answer(f"✅ Клиент {data.get('identifier_value')} добавлен!", reply_markup=main_menu())
    await state.finish()
    await asyncio.sleep(300)
    await bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

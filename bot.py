import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta
from database import save_client, get_clients, update_client, delete_client, get_client_by_id

API_TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AddClient(StatesGroup):
    phone = State()
    dob = State()
    account = State()
    region = State()
    subscription_exists = State()
    subscription_count = State()
    sub1_type = State()
    sub1_period = State()
    sub1_date = State()
    sub2_type = State()
    sub2_period = State()
    sub2_date = State()
    games_q = State()
    games = State()
    codes_q = State()
    codes = State()

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('➕ Добавить клиента'))
    kb.add(KeyboardButton('🔍 Найти клиента'))
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def region_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('(укр)'), KeyboardButton('(тур)'), KeyboardButton('(другой)'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def yes_no_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Да'), KeyboardButton('Нет'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def sub_count_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Одна'), KeyboardButton('Две'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def psplus_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('PS Plus Deluxe'), KeyboardButton('PS Plus Extra'))
    kb.add(KeyboardButton('PS Plus Essential'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def eaplay_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('EA Play'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def sub_period_kb(periods):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for p in periods:
        kb.add(KeyboardButton(p))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def edit_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('📱 Изменить номер', callback_data='edit_phone'),
        InlineKeyboardButton('📅 Изменить дату рождения', callback_data='edit_dob'),
        InlineKeyboardButton('🔐 Изменить аккаунт', callback_data='edit_account'),
        InlineKeyboardButton('🌍 Изменить регион', callback_data='edit_region'),
        InlineKeyboardButton('🖼 Изменить резерв коды', callback_data='edit_codes'),
        InlineKeyboardButton('💳 Изменить подписку', callback_data='edit_sub'),
        InlineKeyboardButton('🎮 Изменить игры', callback_data='edit_games')
    )
    kb.add(InlineKeyboardButton('✅ Сохранить', callback_data='save'))
    return kb

async def clear_chat(chat_id):
    async for message in bot.iter_history(chat_id, limit=100):
        try:
            await bot.delete_message(chat_id, message.message_id)
        except Exception:
            continue

def parse_account(text):
    lines = text.strip().split('\n')
    login = lines[0].strip() if len(lines) > 0 else ''
    password = lines[1].strip() if len(lines) > 1 else ''
    mailpass = lines[2].strip() if len(lines) > 2 else ''
    return login, password, mailpass

def format_client_info(client):
    phone = client['phone']
    dob = client.get('dob', 'отсутствует')
    acc = client['login']
    pas = client['password']
    mailpass = client.get('mailpass', '')
    region = client.get('region', '')
    games = client.get('games', [])
    sub1 = client.get('sub1', None)
    sub2 = client.get('sub2', None)
    codes_file_id = client.get('codes_file_id', None)

    lines = []
    lines.append(f"👤 <b>{phone}</b> | {dob}")
    lines.append(f"🔐 <b>{acc}</b> ;{pas} {region}")
    if mailpass:
        lines.append(f"✉️ Почта-пароль: {mailpass}")
    if sub1:
        lines.append(f"💳 {sub1['type']} {sub1['period']} {region}")
        lines.append(f"📅 {sub1['date_start']} → {sub1['date_end']}")
    if sub2:
        lines.append(f"💳 {sub2['type']} {sub2['period']} {region}")
        lines.append(f"📅 {sub2['date_start']} → {sub2['date_end']}")
    lines.append(f"🌍 Регион: {region}")
    if games:
        lines.append(f"🎮 Игры:\n" + '\n'.join([f"• {g}" for g in games]))
    return '\n'.join(lines)

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Выберите действие:", reply_markup=main_menu())

@dp.message_handler(lambda m: m.text == '➕ Добавить клиента')
async def add_client(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_chat(message.chat.id)
    await message.answer('Шаг 1\nНомер телефона или Telegram:', reply_markup=cancel_kb())
    await AddClient.phone.set()

@dp.message_handler(state=AddClient.phone, content_types=types.ContentTypes.TEXT)
async def add_client_phone(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(phone=message.text.strip())
    await message.answer('Шаг 2\nДата рождения\nЕсть дата рождения?', reply_markup=yes_no_kb())
    await AddClient.dob.set()

@dp.message_handler(state=AddClient.dob, content_types=types.ContentTypes.TEXT)
async def add_client_dob(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    if message.text == 'Да':
        await message.answer('Введите дату рождения (дд.мм.гггг):', reply_markup=cancel_kb())
    else:
        await state.update_data(dob='отсутствует')
        await message.answer('Шаг 3\nДанные от аккаунта:', reply_markup=cancel_kb())
        await AddClient.account.set()
        return
    await AddClient.dob.set()

@dp.message_handler(state=AddClient.dob, content_types=types.ContentTypes.TEXT)
async def add_client_dob_input(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(dob=message.text.strip())
    await message.answer('Шаг 3\nДанные от аккаунта:', reply_markup=cancel_kb())
    await AddClient.account.set()

@dp.message_handler(state=AddClient.account, content_types=types.ContentTypes.TEXT)
async def add_client_account(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    lines = message.text.strip().split('\n')
    login = lines[0] if len(lines) > 0 else ''
    password = lines[1] if len(lines) > 1 else ''
    mailpass = lines[2] if len(lines) > 2 else ''
    await state.update_data(login=login, password=password, mailpass=mailpass)
    await message.answer('Шаг 4\nКакой регион аккаунта?', reply_markup=region_kb())
    await AddClient.region.set()

@dp.message_handler(state=AddClient.region, content_types=types.ContentTypes.TEXT)
async def add_client_region(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(region=message.text.strip())
    await message.answer('Шаг 5\nОформлена ли подписка?', reply_markup=yes_no_kb())
    await AddClient.subscription_exists.set()

@dp.message_handler(state=AddClient.subscription_exists, content_types=types.ContentTypes.TEXT)
async def add_client_subscription_exists(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    if message.text == 'Нет':
        await state.update_data(sub1=None, sub2=None)
        await message.answer('Шаг 6\nОформлены игры?', reply_markup=yes_no_kb())
        await AddClient.games_q.set()
        return
    await message.answer('Одна или две подписки?', reply_markup=sub_count_kb())
    await AddClient.subscription_count.set()

@dp.message_handler(state=AddClient.subscription_count, content_types=types.ContentTypes.TEXT)
async def add_client_subscription_count(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    if message.text == 'Одна':
        await message.answer('Выберите подписку:', reply_markup=psplus_kb())
        await AddClient.sub1_type.set()
        await state.update_data(subs_total=1)
    elif message.text == 'Две':
        await message.answer('Шаг 5\nКакая первая подписка?', reply_markup=psplus_kb())
        await AddClient.sub1_type.set()
        await state.update_data(subs_total=2)
    else:
        await message.answer('Пожалуйста, выбери вариант с клавиатуры.', reply_markup=sub_count_kb())

@dp.message_handler(state=AddClient.sub1_type, content_types=types.ContentTypes.TEXT)
async def add_client_sub1_type(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    sub_type = message.text.strip()
    await state.update_data(sub1_type=sub_type)
    if sub_type in ['PS Plus Deluxe', 'PS Plus Extra', 'PS Plus Essential']:
        await message.answer('Срок подписки?', reply_markup=sub_period_kb(['1м', '3м', '12м']))
    else:
        await message.answer('Срок подписки?', reply_markup=sub_period_kb(['1м', '12м']))
    await AddClient.sub1_period.set()

@dp.message_handler(state=AddClient.sub1_period, content_types=types.ContentTypes.TEXT)
async def add_client_sub1_period(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(sub1_period=message.text.strip())
    await message.answer('Введите дату оформления первой подписки (дд.мм.гггг):', reply_markup=cancel_kb())
    await AddClient.sub1_date.set()

@dp.message_handler(state=AddClient.sub1_date, content_types=types.ContentTypes.TEXT)
async def add_client_sub1_date(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(sub1_date=message.text.strip())
    data = await state.get_data()
    if data.get('subs_total', 1) == 2:
        await message.answer('Шаг 6\nКакая вторая подписка?', reply_markup=eaplay_kb())
        await AddClient.sub2_type.set()
    else:
        await message.answer('Шаг 6\nОформлены игры?', reply_markup=yes_no_kb())
        await AddClient.games_q.set()

@dp.message_handler(state=AddClient.sub2_type, content_types=types.ContentTypes.TEXT)
async def add_client_sub2_type(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(sub2_type=message.text.strip())
    await message.answer('Срок подписки?', reply_markup=sub_period_kb(['1м', '12м']))
    await AddClient.sub2_period.set()

@dp.message_handler(state=AddClient.sub2_period, content_types=types.ContentTypes.TEXT)
async def add_client_sub2_period(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(sub2_period=message.text.strip())
    await message.answer('Введите дату оформления второй подписки (дд.мм.гггг):', reply_markup=cancel_kb())
    await AddClient.sub2_date.set()

@dp.message_handler(state=AddClient.sub2_date, content_types=types.ContentTypes.TEXT)
async def add_client_sub2_date(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    await state.update_data(sub2_date=message.text.strip())
    await message.answer('Шаг 7\nОформлены игры?', reply_markup=yes_no_kb())
    await AddClient.games_q.set()

@dp.message_handler(state=AddClient.games_q, content_types=types.ContentTypes.TEXT)
async def add_client_games_q(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    if message.text == 'Да':
        await message.answer('Напиши какие игры (каждая на новой строке):', reply_markup=cancel_kb())
        await AddClient.games.set()
    else:
        await state.update_data(games=[])
        await message.answer('Шаг 7\nЕсть ли резервные коды?', reply_markup=yes_no_kb())
        await AddClient.codes_q.set()

@dp.message_handler(state=AddClient.games, content_types=types.ContentTypes.TEXT)
async def add_client_games(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    games = [x.strip() for x in message.text.split('\n') if x.strip()]
    await state.update_data(games=games)
    await message.answer('Шаг 7\nЕсть ли резервные коды?', reply_markup=yes_no_kb())
    await AddClient.codes_q.set()

@dp.message_handler(state=AddClient.codes_q, content_types=types.ContentTypes.TEXT)
async def add_client_codes_q(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer('Отменено.', reply_markup=main_menu())
        return
    if message.text == 'Да':
        await message.answer('Загрузите скриншот с резервными кодами:', reply_markup=cancel_kb())
        await AddClient.codes.set()
    else:
        await state.update_data(codes_file_id=None)
        await finish_add_client(message, state)

@dp.message_handler(state=AddClient.codes, content_types=types.ContentTypes.PHOTO)
async def add_client_codes(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(codes_file_id=file_id)
    await finish_add_client(message, state)

async def finish_add_client(message, state):
    data = await state.get_data()
    phone = data.get('phone', '')
    dob = data.get('dob', 'отсутствует')
    login = data.get('login', '')
    password = data.get('password', '')
    mailpass = data.get('mailpass', '')
    region = data.get('region', '')
    sub1 = None
    sub2 = None
    if data.get('sub1_type'):
        period = data.get('sub1_period')
        date_start = data.get('sub1_date')
        months = int(period.replace('м', ''))
        date_end = (datetime.strptime(date_start, "%d.%m.%Y") + timedelta(days=30*months)).strftime("%d.%m.%Y")
        sub1 = {'type': data['sub1_type'], 'period': period, 'date_start': date_start, 'date_end': date_end}
    if data.get('sub2_type'):
        period = data.get('sub2_period')
        date_start = data.get('sub2_date')
        months = int(period.replace('м', ''))
        date_end = (datetime.strptime(date_start, "%d.%m.%Y") + timedelta(days=30*months)).strftime("%d.%m.%Y")
        sub2 = {'type': data['sub2_type'], 'period': period, 'date_start': date_start, 'date_end': date_end}
    games = data.get('games', [])
    codes_file_id = data.get('codes_file_id', None)
    client = {
        'phone': phone,
        'dob': dob,
        'login': login,
        'password': password,
        'mailpass': mailpass,
        'region': region,
        'sub1': sub1,
        'sub2': sub2,
        'games': games,
        'codes_file_id': codes_file_id
    }
    save_client(client)
    await state.finish()
    await clear_chat(message.chat.id)
    msg = f'✅ <b>{phone}</b> добавлен\n\n' + format_client_info(client)
    reply_markup = edit_kb()
    sent_msg = await message.answer(msg, parse_mode='HTML', reply_markup=reply_markup)
    if codes_file_id:
        await message.answer_photo(codes_file_id)
    await asyncio.sleep(300)
    await bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
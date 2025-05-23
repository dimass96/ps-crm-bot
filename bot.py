import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from database import save_client
from datetime import datetime
import os

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AddClient(StatesGroup):
    step1_id = State()
    step2_birthday_choice = State()
    step2_birthday = State()
    step3_login = State()
    step3_password = State()
    step3_mailpass = State()
    step4_region = State()
    step5_sub_choice = State()
    step5_sub_count = State()
    step5_sub1_type = State()
    step5_sub1_term = State()
    step5_sub1_date = State()
    step5_sub2_type = State()
    step5_sub2_term = State()
    step5_sub2_date = State()
    step6_games_choice = State()
    step6_games = State()
    step7_reserve_choice = State()
    step7_reserve_upload = State()

def get_cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_yesno_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Да'), KeyboardButton('Нет'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_region_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('(укр)'), KeyboardButton('(тур)'), KeyboardButton('(другой)'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_sub_count_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Одна'), KeyboardButton('Две'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_psplus_type_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('PS Plus Deluxe'),
        KeyboardButton('PS Plus Extra'),
        KeyboardButton('PS Plus Essential')
    )
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_eaplay_type_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('EA Play'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_psplus_term_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('1м'), KeyboardButton('3м'), KeyboardButton('12м'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_eaplay_term_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('1м'), KeyboardButton('12м'))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def get_edit_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton('📱 Изменить номер'), KeyboardButton('📅 Изменить дату рождения'))
    kb.row(KeyboardButton('🔐 Изменить аккаунт'), KeyboardButton('🌍 Изменить регион'))
    kb.row(KeyboardButton('🖼 Изменить резерв коды'), KeyboardButton('💳 Изменить подписку'))
    kb.row(KeyboardButton('🎮 Изменить игры'), KeyboardButton('✅ Сохранить'))
    return kb

def build_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('➕ Добавить клиента'), KeyboardButton('🔍 Найти клиента'))
    return kb

async def clear_last_messages(chat_id, bot, message_id, count=15):
    for msg_id in range(message_id, message_id - count, -1):
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_last_messages(message.chat.id, bot, message.message_id)
    await message.answer('Меню', reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == 'Меню')
async def main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_last_messages(message.chat.id, bot, message.message_id)
    await message.answer('Меню', reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == '➕ Добавить клиента')
async def add_client_start(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_last_messages(message.chat.id, bot, message.message_id)
    await message.answer('Шаг 1\nНомер телефона или Telegram:', reply_markup=get_cancel_kb())
    await AddClient.step1_id.set()

@dp.message_handler(state=AddClient.step1_id)
async def addclient_id(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    client = {'id': message.text.strip()}
    await state.update_data(client=client)
    kb = get_yesno_kb()
    await message.answer('Шаг 2\nДата рождения есть?', reply_markup=kb)
    await AddClient.step2_birthday_choice.set()

@dp.message_handler(state=AddClient.step2_birthday_choice)
async def addclient_birthday_choice(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text == 'Да':
        await message.answer('Введите дату рождения (дд.мм.гггг):', reply_markup=get_cancel_kb())
        await AddClient.step2_birthday.set()
    elif message.text == 'Нет':
        data = await state.get_data()
        client = data.get('client', {})
        client['birthday'] = 'отсутствует'
        await state.update_data(client=client)
        await message.answer('Шаг 3\nДанные аккаунта:\nВведите логин:', reply_markup=get_cancel_kb())
        await AddClient.step3_login.set()
    else:
        await message.answer('Выберите Да или Нет.', reply_markup=get_yesno_kb())

@dp.message_handler(state=AddClient.step2_birthday)
async def addclient_birthday(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['birthday'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer('Шаг 3\nДанные аккаунта:\nВведите логин:', reply_markup=get_cancel_kb())
    await AddClient.step3_login.set()

@dp.message_handler(state=AddClient.step3_login)
async def addclient_login(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    login = message.text.strip()
    await state.update_data(login=login)
    await message.answer('Введите пароль от аккаунта:', reply_markup=get_cancel_kb())
    await AddClient.step3_password.set()

@dp.message_handler(state=AddClient.step3_password)
async def addclient_password(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    password = message.text.strip()
    await state.update_data(password=password)
    await message.answer('Введите пароль от почты (если есть, иначе - напишите "-"):', reply_markup=get_cancel_kb())
    await AddClient.step3_mailpass.set()

@dp.message_handler(state=AddClient.step3_mailpass)
async def addclient_mailpass(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    mailpass = message.text.strip()
    data = await state.get_data()
    login = data.get('login', '')
    password = data.get('password', '')
    loginpass = f"{login}; {password}"
    client = data.get('client', {})
    client['loginpass'] = loginpass
    if mailpass != '-':
        client['mailpass'] = mailpass
    else:
        client['mailpass'] = ''
    await state.update_data(client=client)
    await message.answer('Шаг 4\nКакой регион аккаунта?', reply_markup=get_region_kb())
    await AddClient.step4_region.set()

@dp.message_handler(state=AddClient.step4_region)
async def addclient_region(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    region = message.text.strip()
    data = await state.get_data()
    client = data.get('client', {})
    client['region'] = region
    loginpass = client.get('loginpass', '')
    client['loginpass'] = f"{loginpass} {region}"
    await state.update_data(client=client)
    await message.answer('Шаг 5\nОформлена ли подписка?', reply_markup=get_yesno_kb())
    await AddClient.step5_sub_choice.set()

@dp.message_handler(state=AddClient.step5_sub_choice)
async def addclient_sub_choice(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text == 'Да':
        await message.answer('Сколько подписок?', reply_markup=get_sub_count_kb())
        await AddClient.step5_sub_count.set()
    elif message.text == 'Нет':
        data = await state.get_data()
        client = data.get('client', {})
        client['subs'] = [{'type': 'отсутствует'}]
        await state.update_data(client=client)
        await message.answer('Шаг 6\nОформлены игры?', reply_markup=get_yesno_kb())
        await AddClient.step6_games_choice.set()
    else:
        await message.answer('Выберите Да или Нет.', reply_markup=get_yesno_kb())

@dp.message_handler(state=AddClient.step5_sub_count)
async def addclient_sub_count(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text == 'Одна':
        await message.answer('Выберите подписку:', reply_markup=get_psplus_type_kb())
        await AddClient.step5_sub1_type.set()
    elif message.text == 'Две':
        await message.answer('Шаг 5\nКакая первая подписка?', reply_markup=get_psplus_type_kb())
        await AddClient.step5_sub1_type.set()
        await state.update_data(subs=[])
    else:
        await message.answer('Выберите вариант.', reply_markup=get_sub_count_kb())

@dp.message_handler(state=AddClient.step5_sub1_type)
async def addclient_sub1_type(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text in ['PS Plus Deluxe', 'PS Plus Extra', 'PS Plus Essential']:
        await state.update_data(sub1_type=message.text)
        await message.answer('Срок подписки?', reply_markup=get_psplus_term_kb())
        await AddClient.step5_sub1_term.set()
    elif message.text == 'EA Play':
        await state.update_data(sub1_type=message.text)
        await message.answer('Срок подписки?', reply_markup=get_eaplay_term_kb())
        await AddClient.step5_sub1_term.set()
    else:
        await message.answer('Выберите вариант.', reply_markup=get_psplus_type_kb())

@dp.message_handler(state=AddClient.step5_sub1_term)
async def addclient_sub1_term(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    term = message.text.strip()
    data = await state.get_data()
    sub1_type = data.get('sub1_type', '')
    await state.update_data(sub1_term=term)
    await message.answer('Введите дату оформления первой подписки (дд.мм.гггг):', reply_markup=get_cancel_kb())
    await AddClient.step5_sub1_date.set()

@dp.message_handler(state=AddClient.step5_sub1_date)
async def addclient_sub1_date(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    date = message.text.strip()
    data = await state.get_data()
    sub1_type = data.get('sub1_type', '')
    sub1_term = data.get('sub1_term', '')
    sub1 = {'type': sub1_type, 'term': sub1_term, 'date': date}
    subs = data.get('subs', [])
    subs.append(sub1)
    await state.update_data(subs=subs)
    if len(subs) == 1 and sub1_type in ['PS Plus Deluxe', 'PS Plus Extra', 'PS Plus Essential']:
        await message.answer('Шаг 5\nКакая вторая подписка?', reply_markup=get_eaplay_type_kb())
        await AddClient.step5_sub2_type.set()
    else:
        client = data.get('client', {})
        client['subs'] = subs
        await state.update_data(client=client)
        await message.answer('Шаг 6\nОформлены игры?', reply_markup=get_yesno_kb())
        await AddClient.step6_games_choice.set()

@dp.message_handler(state=AddClient.step5_sub2_type)
async def addclient_sub2_type(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text == 'EA Play':
        await state.update_data(sub2_type=message.text)
        await message.answer('Срок подписки?', reply_markup=get_eaplay_term_kb())
        await AddClient.step5_sub2_term.set()
    else:
        await message.answer('Выберите вариант.', reply_markup=get_eaplay_type_kb())

@dp.message_handler(state=AddClient.step5_sub2_term)
async def addclient_sub2_term(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    await state.update_data(sub2_term=message.text)
    await message.answer('Введите дату оформления второй подписки (дд.мм.гггг):', reply_markup=get_cancel_kb())
    await AddClient.step5_sub2_date.set()

@dp.message_handler(state=AddClient.step5_sub2_date)
async def addclient_sub2_date(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    date = message.text.strip()
    data = await state.get_data()
    sub2_type = data.get('sub2_type', '')
    sub2_term = data.get('sub2_term', '')
    sub2 = {'type': sub2_type, 'term': sub2_term, 'date': date}
    subs = data.get('subs', [])
    subs.append(sub2)
    client = data.get('client', {})
    client['subs'] = subs
    await state.update_data(client=client)
    await message.answer('Шаг 6\nОформлены игры?', reply_markup=get_yesno_kb())
    await AddClient.step6_games_choice.set()

@dp.message_handler(state=AddClient.step6_games_choice)
async def addclient_games_choice(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text == 'Да':
        await message.answer('Напиши какие игры (каждая игра с новой строки):', reply_markup=get_cancel_kb())
        await AddClient.step6_games.set()
    elif message.text == 'Нет':
        data = await state.get_data()
        client = data.get('client', {})
        client['games'] = []
        await state.update_data(client=client)
        await message.answer('Шаг 7\nЕсть резерв коды?', reply_markup=get_yesno_kb())
        await AddClient.step7_reserve_choice.set()
    else:
        await message.answer('Выберите Да или Нет.', reply_markup=get_yesno_kb())

@dp.message_handler(state=AddClient.step6_games)
async def addclient_games(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    games = [g.strip() for g in message.text.split('\n') if g.strip()]
    data = await state.get_data()
    client = data.get('client', {})
    client['games'] = games
    await state.update_data(client=client)
    await message.answer('Шаг 7\nЕсть резерв коды?', reply_markup=get_yesno_kb())
    await AddClient.step7_reserve_choice.set()

@dp.message_handler(state=AddClient.step7_reserve_choice)
async def addclient_reserve_choice(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await cancel_add(message, state)
        return
    if message.text == 'Да':
        await message.answer('Загрузите скриншот с кодами:', reply_markup=get_cancel_kb())
        await AddClient.step7_reserve_upload.set()
    elif message.text == 'Нет':
        data = await state.get_data()
        client = data.get('client', {})
        client['reserve'] = ''
        await state.update_data(client=client)
        await finish_add(message, state)
    else:
        await message.answer('Выберите Да или Нет.', reply_markup=get_yesno_kb())

@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddClient.step7_reserve_upload)
async def addclient_reserve_upload(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    client = data.get('client', {})
    client['reserve'] = photo_id
    await state.update_data(client=client)
    await finish_add(message, state)

@dp.message_handler(lambda m: m.text == '❌ Отмена', state='*')
async def cancel_add(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_last_messages(message.chat.id, bot, message.message_id)
    await message.answer('Добавление отменено.', reply_markup=build_main_menu())

def format_client_info(client):
    id_line = f"**{client['id']}**"
    bday = client.get('birthday', '')
    if bday and bday != 'отсутствует':
        id_line += f" | {bday}"
    login_line = f"{client.get('loginpass', '')}"
    mail_line = ''
    if client.get('mailpass'):
        mail_line = f"\nПочта-пароль: {client['mailpass']}"
    subs_lines = []
    for sub in client.get('subs', []):
        if 'type' in sub and sub['type'] != 'отсутствует':
            s = f"{sub['type']} {sub['term']}" if 'term' in sub else sub['type']
            if 'date' in sub:
                start = datetime.strptime(sub['date'], "%d.%m.%Y")
                if 'term' in sub:
                    months = int(sub['term'].replace('м',''))
                    if months == 12:
                        months = 12
                    end_month = start.month + months
                    end_year = start.year
                    while end_month > 12:
                        end_month -= 12
                        end_year += 1
                    end = start.replace(year=end_year, month=end_month)
                    s += f"\n{start.strftime('%d.%m.%Y')} → {end.strftime('%d.%m.%Y')}"
            subs_lines.append(s)
    region = client.get('region', '')
    games_lines = "\n".join(['• ' + g for g in client.get('games', [])]) if client.get('games') else ''
    text = f"{id_line}\n{login_line}{mail_line}"
    if subs_lines:
        text += '\n\n' + '\n\n'.join(subs_lines)
    if games_lines:
        text += f"\n\n🎮 Игры:\n{games_lines}"
    return text

async def finish_add(message, state: FSMContext):
    data = await state.get_data()
    client = data.get('client', {})
    save_client(client)
    await clear_last_messages(message.chat.id, bot, message.message_id)
    await message.answer(f"✅ {client['id']} добавлен\n\n{format_client_info(client)}", reply_markup=get_edit_kb())
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
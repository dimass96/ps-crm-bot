import logging
import os
import shutil
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import database

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

database.init_db()

class AddClient(StatesGroup):
    step_identifier = State()
    step_birthday_exist = State()
    step_birthday = State()
    step_account_data = State()
    step_region = State()
    step_sub_exist = State()
    step_sub_count = State()
    step_sub1_type = State()
    step_sub1_duration = State()
    step_sub1_start = State()
    step_sub2_type = State()
    step_sub2_duration = State()
    step_sub2_start = State()
    step_games = State()
    step_reserve_exist = State()
    step_reserve_upload = State()

def build_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить клиента"))
    kb.add(KeyboardButton("🔍 Найти клиента"))
    return kb

def cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))

def region_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("🇺🇦 Укр"), KeyboardButton("🇹🇷 Тур"), KeyboardButton("🌍 Другое")
    ).add(KeyboardButton("❌ Отмена"))

def yes_no_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Есть"), KeyboardButton("Нету")
    ).add(KeyboardButton("❌ Отмена"))

def sub_count_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Одна"), KeyboardButton("Две")
    ).add(KeyboardButton("❌ Отмена"))

def sub_type1_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"),
        KeyboardButton("PS Plus Essential"), KeyboardButton("EA Play")
    ).add(KeyboardButton("❌ Отмена"))

def sub_type2_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("EA Play")
    ).add(KeyboardButton("❌ Отмена"))

def sub_duration_ps_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м")
    ).add(KeyboardButton("❌ Отмена"))

def sub_duration_ea_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("1м"), KeyboardButton("12м")
    ).add(KeyboardButton("❌ Отмена"))

def remove_kb():
    return ReplyKeyboardRemove()

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

async def clear_chat(chat_id):
    await asyncio.sleep(0.5)
    async for msg in bot.iter_history(chat_id):
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except:
            pass

def format_info(client):
    emoji = {
        "identifier": "👤",
        "birthday": "🎂",
        "account": "🔐",
        "mailpass": "✉️",
        "sub": "🗓️",
        "region": "🌍",
        "games": "🎮",
        "codes": "📷"
    }
    text = ""
    identifier = client.get('identifier', '')
    birthday = client.get('birthday', 'отсутствует')
    if not birthday: birthday = "отсутствует"
    text += f"{emoji['identifier']} <b>{identifier}</b> | <i>{birthday}</i>\n"
    email = client.get('email', '')
    accpass = client.get('account_pass', '')
    region = client.get('region', '')
    reg_txt = ''
    if region:
        if region == "🇺🇦 Укр": reg_txt = "(укр)"
        elif region == "🇹🇷 Тур": reg_txt = "(тур)"
        else: reg_txt = "(другой)"
    text += f"{emoji['account']} {email};{accpass} {reg_txt}\n"
    mailpass = client.get('mail_pass', '')
    text += f"{emoji['mailpass']} Почта-пароль: {mailpass}\n"
    sub1 = client.get('sub1_name', '')
    sub1_dur = client.get('sub1_duration', '')
    sub1_start = client.get('sub1_start', '')
    sub1_end = client.get('sub1_end', '')
    sub1_reg = reg_txt
    sub2 = client.get('sub2_name', '')
    sub2_dur = client.get('sub2_duration', '')
    sub2_start = client.get('sub2_start', '')
    sub2_end = client.get('sub2_end', '')
    if sub1 and sub1_end:
        text += f"\n{emoji['sub']} {sub1} {sub1_dur} {sub1_reg}\n"
        text += f"🗓️ {sub1_start} → {sub1_end}\n"
    if sub2 and sub2_end:
        text += f"\n{emoji['sub']} {sub2} {sub2_dur} {sub1_reg}\n"
        text += f"🗓️ {sub2_start} → {sub2_end}\n"
    if region:
        text += f"\n{emoji['region']} Регион: {reg_txt.replace('(','').replace(')','')}\n"
    games = client.get('games', '')
    if games:
        games_list = [g.strip() for g in games.split(' —— ') if g.strip()]
        text += f"\n{emoji['games']} <b>Игры:</b>\n"
        for g in games_list:
            text += f"• {g}\n"
    return text

def info_from_db_row(row):
    keys = [
        'id','identifier','identifier_type','birthday','email','account_pass','mail_pass','console','region','reserve_codes_path',
        'sub1_name','sub1_duration','sub1_start','sub1_end','sub2_name','sub2_duration','sub2_start','sub2_end','games'
    ]
    return dict(zip(keys,row))

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(" ", reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == "➕ Добавить клиента")
async def addclient_step1(message: types.Message, state: FSMContext):
    await state.finish()
    await state.update_data(client={})
    await message.answer("<b>Шаг 1</b>\nВведите <b>номер телефона</b> или <b>Telegram-ник</b> клиента:", reply_markup=cancel_kb())
    await AddClient.step_identifier.set()

@dp.message_handler(state=AddClient.step_identifier)
async def addclient_step2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['identifier'] = message.text.strip()
    await state.update_data(client=client)
    kb = yes_no_kb()
    await message.answer("<b>Шаг 2</b>\nЕсть ли <b>дата рождения</b> клиента?", reply_markup=kb)
    await AddClient.step_birthday_exist.set()

@dp.message_handler(state=AddClient.step_birthday_exist)
async def addclient_step2_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("<b>Шаг 2</b>\nВведите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb())
        await AddClient.step_birthday.set()
    elif message.text == "Нету":
        client = await state.get_data()
        client = client.get('client', {})
        client['birthday'] = "отсутствует"
        await state.update_data(client=client)
        await message.answer("<b>Шаг 3</b>\n<b>Данные аккаунта</b>:\n\nВ одной строке — логин/пароль\nВо второй — почта-пароль\n\nПример:\nskdjdj@hotmail.com;Sishdhjsis\nПочта-пароль:Sjsjjsjd", reply_markup=cancel_kb())
        await AddClient.step_account_data.set()
    else:
        await message.answer("Выберите: Есть / Нету", reply_markup=yes_no_kb())

@dp.message_handler(state=AddClient.step_birthday)
async def addclient_step3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['birthday'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("<b>Шаг 3</b>\n<b>Данные аккаунта</b>:\n\nВ одной строке — логин/пароль\nВо второй — почта-пароль\n\nПример:\nskdjdj@hotmail.com;Sishdhjsis\nПочта-пароль:Sjsjjsjd", reply_markup=cancel_kb())
    await AddClient.step_account_data.set()

@dp.message_handler(state=AddClient.step_account_data)
async def addclient_step4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    lines = message.text.strip().split("\n")
    if len(lines) < 2:
        await message.answer("Введите <b>две строки</b> — сначала логин/пароль, затем почта-пароль!", reply_markup=cancel_kb())
        return
    email_pass = lines[0]
    mail_pass = lines[1]
    if ';' not in email_pass:
        await message.answer("Первая строка: <b>логин;пароль</b> (через ; )", reply_markup=cancel_kb())
        return
    email, accpass = email_pass.split(';', 1)
    mailpass = mail_pass.replace("Почта-пароль:", "").strip()
    client = await state.get_data()
    client = client.get('client', {})
    client['email'] = email.strip()
    client['account_pass'] = accpass.strip()
    client['mail_pass'] = mailpass.strip()
    await state.update_data(client=client)
    await message.answer("<b>Шаг 4</b>\nКакой <b>регион аккаунта</b>?", reply_markup=region_kb())
    await AddClient.step_region.set()

@dp.message_handler(state=AddClient.step_region)
async def addclient_step5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    region = message.text.strip()
    if region not in ["🇺🇦 Укр", "🇹🇷 Тур", "🌍 Другое"]:
        await message.answer("Выбери один из вариантов!", reply_markup=region_kb())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['region'] = region
    await state.update_data(client=client)
    await message.answer("<b>Шаг 5</b>\nОформлена ли <b>подписка</b>?", reply_markup=yes_no_kb())
    await AddClient.step_sub_exist.set()

@dp.message_handler(state=AddClient.step_sub_exist)
async def addclient_step6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("<b>Шаг 5</b>\nСколько подписок у клиента?", reply_markup=sub_count_kb())
        await AddClient.step_sub_count.set()
    elif message.text == "Нету":
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
        await message.answer("<b>Шаг 6</b>\nВпиши построчно <b>игры</b> клиента (каждая с новой строки):", reply_markup=cancel_kb())
        await AddClient.step_games.set()
    else:
        await message.answer("Выберите: Есть / Нету", reply_markup=yes_no_kb())

@dp.message_handler(state=AddClient.step_sub_count)
async def addclient_step6_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text == "Одна":
        await message.answer("<b>Шаг 5</b>\nВыбери тип подписки", reply_markup=sub_type1_kb())
        await AddClient.step_sub1_type.set()
    elif message.text == "Две":
        await message.answer("<b>Шаг 5</b>\nВыбери первую подписку (PS Plus)", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential")
        ).add(KeyboardButton("❌ Отмена")))
        await AddClient.step_sub1_type.set()
    else:
        await message.answer("Выберите: Одна / Две", reply_markup=sub_count_kb())

@dp.message_handler(state=AddClient.step_sub1_type)
async def addclient_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        client = await state.get_data()
        client = client.get('client', {})
        client['sub1_name'] = message.text
        await state.update_data(client=client)
        await message.answer("<b>Шаг 5</b>\nСрок подписки? (1м/3м/12м)", reply_markup=sub_duration_ps_kb())
        await AddClient.step_sub1_duration.set()
    elif message.text == "EA Play":
        client = await state.get_data()
        client = client.get('client', {})
        client['sub1_name'] = "EA Play"
        await state.update_data(client=client)
        await message.answer("<b>Шаг 5</b>\nСрок подписки? (1м/12м)", reply_markup=sub_duration_ea_kb())
        await AddClient.step_sub1_duration.set()
    else:
        await message.answer("Выбери тип подписки!", reply_markup=sub_type1_kb())

@dp.message_handler(state=AddClient.step_sub1_duration)
async def addclient_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    client = await state.get_data()
    client = client.get('client', {})
    if client['sub1_name'] == "EA Play" and message.text not in ["1м", "12м"]:
        await message.answer("Для EA Play — 1м или 12м!", reply_markup=sub_duration_ea_kb())
        return
    if client['sub1_name'] != "EA Play" and message.text not in ["1м", "3м", "12м"]:
        await message.answer("Для PS Plus — 1м, 3м или 12м!", reply_markup=sub_duration_ps_kb())
        return
    client['sub1_duration'] = message.text
    await state.update_data(client=client)
    await message.answer("<b>Шаг 5</b>\nВведите дату оформления первой подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.step_sub1_start.set()

@dp.message_handler(state=AddClient.step_sub1_start)
async def addclient_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    date = message.text.strip()
    client = await state.get_data()
    client = client.get('client', {})
    client['sub1_start'] = date
    client['sub1_end'] = calc_sub_end(date, client['sub1_duration'])
    await state.update_data(client=client)
    sub1type = client.get('sub1_name', '')
    if sub1type in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        await message.answer("<b>Шаг 5</b>\nВыбери вторую подписку (EA Play)", reply_markup=sub_type2_kb())
        await AddClient.step_sub2_type.set()
    else:
        await message.answer("<b>Шаг 6</b>\nВпиши построчно <b>игры</b> клиента (каждая с новой строки):", reply_markup=cancel_kb())
        await AddClient.step_games.set()

@dp.message_handler(state=AddClient.step_sub2_type)
async def addclient_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text == "EA Play":
        client = await state.get_data()
        client = client.get('client', {})
        client['sub2_name'] = "EA Play"
        await state.update_data(client=client)
        await message.answer("<b>Шаг 5</b>\nСрок подписки EA Play? (1м/12м)", reply_markup=sub_duration_ea_kb())
        await AddClient.step_sub2_duration.set()
    else:
        await message.answer("Вторая подписка только EA Play", reply_markup=sub_type2_kb())

@dp.message_handler(state=AddClient.step_sub2_duration)
async def addclient_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text not in ["1м", "12м"]:
        await message.answer("EA Play: только 1м или 12м!", reply_markup=sub_duration_ea_kb())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_duration'] = message.text
    await state.update_data(client=client)
    await message.answer("<b>Шаг 5</b>\nВведите дату оформления второй подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.step_sub2_start.set()

@dp.message_handler(state=AddClient.step_sub2_start)
async def addclient_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    date = message.text.strip()
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_start'] = date
    client['sub2_end'] = calc_sub_end(date, client['sub2_duration'])
    await state.update_data(client=client)
    await message.answer("<b>Шаг 6</b>\nВпиши построчно <b>игры</b> клиента (каждая с новой строки):", reply_markup=cancel_kb())
    await AddClient.step_games.set()

@dp.message_handler(state=AddClient.step_games)
async def addclient_step7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    games = message.text.strip().split('\n')
    games = [g.strip() for g in games if g.strip()]
    client = await state.get_data()
    client = client.get('client', {})
    client['games'] = ' —— '.join(games)
    await state.update_data(client=client)
    await message.answer("<b>Шаг 7</b>\nЕсть ли <b>резервные коды</b>?", reply_markup=yes_no_kb())
    await AddClient.step_reserve_exist.set()

@dp.message_handler(state=AddClient.step_reserve_exist)
async def addclient_reserve_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("<b>Шаг 7</b>\nЗагрузите скриншот с резервными кодами:", reply_markup=cancel_kb())
        await AddClient.step_reserve_upload.set()
    elif message.text == "Нету":
        client = await state.get_data()
        client = client.get('client', {})
        client['reserve_codes_path'] = ""
        database.add_client(client)
        await state.finish()
        await clear_chat(message.chat.id)
        text = "<b>✅ Клиент успешно добавлен!</b>\n\n"
        text += format_info(client)
        await show_success_info(message, text, None)
    else:
        await message.answer("Есть ли резервные коды? — выберите Есть или Нету", reply_markup=yes_no_kb())

@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=AddClient.step_reserve_upload)
async def addclient_reserve_upload(message: types.Message, state: FSMContext):
    if message.caption == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(" ", reply_markup=build_main_menu())
        return
    file = await message.document.download()
    file_path = f'reserves/{message.document.file_name}'
    os.makedirs('reserves', exist_ok=True)
    shutil.move(file.name, file_path)
    client = await state.get_data()
    client = client.get('client', {})
    client['reserve_codes_path'] = file_path
    database.add_client(client)
    await state.finish()
    await clear_chat(message.chat.id)
    text = "<b>✅ Клиент успешно добавлен!</b>\n\n"
    text += format_info(client)
    info_msg = await show_success_info(message, text, file_path)

async def show_success_info(message, text, doc_path):
    msg = await message.answer(text, reply_markup=remove_kb())
    if doc_path:
        try:
            await message.answer_document(InputFile(doc_path))
        except Exception as e:
            pass
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, msg.message_id)
    except:
        pass

@dp.message_handler(lambda m: m.text == "🔍 Найти клиента")
async def searchclient_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Введите номер или Telegram-ник для поиска:", reply_markup=cancel_kb())

@dp.message_handler()
async def fallback_handler(message: types.Message, state: FSMContext):
    await message.answer("Выберите действие из меню!", reply_markup=build_main_menu())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

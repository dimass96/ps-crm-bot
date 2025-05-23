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
    step1_identifier = State()
    step2_birthday_exist = State()
    step2_birthday = State()
    step3_account = State()
    step4_region = State()
    step5_sub_exist = State()
    step5_sub_count = State()
    step6_sub1_type = State()
    step6_sub1_duration = State()
    step6_sub1_start = State()
    step6_sub2_type = State()
    step6_sub2_duration = State()
    step6_sub2_start = State()
    step7_games_exist = State()
    step7_games = State()
    step8_reserve_exist = State()
    step8_reserve_upload = State()
    editing = State()
    edit_field = State()
    edit_value = State()

def build_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить клиента"))
    kb.add(KeyboardButton("🔍 Найти клиента"))
    return kb

def cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))

def region_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("(укр)"), KeyboardButton("(тур)"), KeyboardButton("(другой)")
    ).add(KeyboardButton("❌ Отмена"))

def yes_no_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("Да"), KeyboardButton("Нет")
    ).add(KeyboardButton("❌ Отмена"))

def yes_no_ru_kb():
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

def sub_type1_only_ps_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"),
        KeyboardButton("PS Plus Essential")
    ).add(KeyboardButton("❌ Отмена"))

def sub_type2_only_ea_kb():
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

def edit_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("📱 Изменить номер"), KeyboardButton("📅 Изменить дату рождения"),
        KeyboardButton("🔐 Изменить аккаунт"), KeyboardButton("🌍 Изменить регион"),
        KeyboardButton("🖼 Изменить резерв коды"), KeyboardButton("💳 Изменить подписку"),
        KeyboardButton("🎮 Изменить игры"),
        KeyboardButton("✅ Сохранить")
    )
    return kb

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
    text = ""
    identifier = client.get('identifier', '')
    birthday = client.get('birthday', 'отсутствует')
    if not birthday:
        birthday = "отсутствует"
    text += f"<b>👤 {identifier}</b>"
    if birthday != "отсутствует":
        text += f" | {birthday}"
    text += "\n"
    email = client.get('email', '')
    accpass = client.get('account_pass', '')
    if email and accpass:
        text += f"🔐 {email}; {accpass}\n"
    mailpass = client.get('mail_pass', '')
    if mailpass:
        text += f"✉️ Почта-пароль: {mailpass}\n"
    region = client.get('region', '')
    if region:
        text += f"🌍 Регион: {region.replace('(','').replace(')','')}\n"
    sub1 = client.get('sub1_name', '')
    sub1_dur = client.get('sub1_duration', '')
    sub1_start = client.get('sub1_start', '')
    sub1_end = client.get('sub1_end', '')
    sub2 = client.get('sub2_name', '')
    sub2_dur = client.get('sub2_duration', '')
    sub2_start = client.get('sub2_start', '')
    sub2_end = client.get('sub2_end', '')
    if sub1 and sub1_end:
        text += f"\n🗓️ {sub1} {sub1_dur}\n{sub1_start} → {sub1_end}\n"
    if sub2 and sub2_end:
        text += f"\n🗓️ {sub2} {sub2_dur}\n{sub2_start} → {sub2_end}\n"
    if not sub1 and not sub2:
        text += f"\n🗓️ (отсутствует)\n"
    games = client.get('games', '')
    if games:
        games_list = [g.strip() for g in games.replace(' —— ', '\n').split('\n') if g.strip()]
        text += f"\n🎮 Игры:\n"
        for g in games_list:
            text += f"• {g}\n"
    return text

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Главное меню:", reply_markup=build_main_menu())

@dp.message_handler(lambda m: m.text == "➕ Добавить клиента")
async def addclient_step1(message: types.Message, state: FSMContext):
    await state.finish()
    await state.update_data(client={})
    await message.answer("<b>Шаг 1</b>\nНомер телефона или Telegram:", reply_markup=cancel_kb())
    await AddClient.step1_identifier.set()

@dp.message_handler(state=AddClient.step1_identifier)
async def addclient_step2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['identifier'] = message.text.strip()
    await state.update_data(client=client)
    kb = yes_no_kb()
    await message.answer("<b>Шаг 2</b>\nЕсть ли дата рождения?", reply_markup=kb)
    await AddClient.step2_birthday_exist.set()

@dp.message_handler(state=AddClient.step2_birthday_exist)
async def addclient_step2_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text == "Да":
        await message.answer("<b>Шаг 2</b>\nВведите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb())
        await AddClient.step2_birthday.set()
    elif message.text == "Нет":
        client = await state.get_data()
        client = client.get('client', {})
        client['birthday'] = "отсутствует"
        await state.update_data(client=client)
        await message.answer("<b>Шаг 3</b>\nДанные аккаунта:\n\n1. Логин (почта)\n2. Пароль от аккаунта\n3. Пароль от почты (если есть, иначе оставьте пустым)", reply_markup=cancel_kb())
        await AddClient.step3_account.set()
    else:
        await message.answer("Выберите: Да / Нет", reply_markup=yes_no_kb())

@dp.message_handler(state=AddClient.step2_birthday)
async def addclient_step3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['birthday'] = message.text.strip()
    await state.update_data(client=client)
    await message.answer("<b>Шаг 3</b>\nДанные аккаунта:\n\n1. Логин (почта)\n2. Пароль от аккаунта\n3. Пароль от почты (если есть, иначе оставьте пустым)", reply_markup=cancel_kb())
    await AddClient.step3_account.set()

@dp.message_handler(state=AddClient.step3_account)
async def addclient_step4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    lines = message.text.strip().split("\n")
    if len(lines) < 2:
        await message.answer("Введите три строки:\nлогин\nпароль от аккаунта\nпароль от почты (если нет — оставьте пустым)", reply_markup=cancel_kb())
        return
    email = lines[0].strip()
    account_pass = lines[1].strip()
    mail_pass = lines[2].strip() if len(lines) > 2 else ""
    client = await state.get_data()
    client = client.get('client', {})
    client['email'] = email
    client['account_pass'] = account_pass
    client['mail_pass'] = mail_pass
    await state.update_data(client=client)
    await message.answer("<b>Шаг 4</b>\nКакой регион аккаунта?", reply_markup=region_kb())
    await AddClient.step4_region.set()

@dp.message_handler(state=AddClient.step4_region)
async def addclient_step5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    region = message.text.strip()
    if region not in ["(укр)", "(тур)", "(другой)"]:
        await message.answer("Выбери один из вариантов!", reply_markup=region_kb())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['region'] = region
    await state.update_data(client=client)
    await message.answer("<b>Шаг 5</b>\nОформлена ли подписка?", reply_markup=yes_no_kb())
    await AddClient.step5_sub_exist.set()

@dp.message_handler(state=AddClient.step5_sub_exist)
async def addclient_step5_sub_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text == "Да":
        await message.answer("<b>Шаг 6</b>\nСколько подписок?", reply_markup=sub_count_kb())
        await AddClient.step5_sub_count.set()
    elif message.text == "Нет":
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
        await message.answer("<b>Шаг 7</b>\nОформлены игры?", reply_markup=yes_no_kb())
        await AddClient.step7_games_exist.set()
    else:
        await message.answer("Выберите: Да / Нет", reply_markup=yes_no_kb())

@dp.message_handler(state=AddClient.step5_sub_count)
async def addclient_step6_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text == "Одна":
        await message.answer("<b>Шаг 6</b>\nВыберите подписку", reply_markup=sub_type1_kb())
        await AddClient.step6_sub1_type.set()
    elif message.text == "Две":
        await message.answer("<b>Шаг 6</b>\nКакая первая подписка?", reply_markup=sub_type1_only_ps_kb())
        await AddClient.step6_sub1_type.set()
    else:
        await message.answer("Выберите: Одна / Две", reply_markup=sub_count_kb())

@dp.message_handler(state=AddClient.step6_sub1_type)
async def addclient_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        client = await state.get_data()
        client = client.get('client', {})
        client['sub1_name'] = message.text
        await state.update_data(client=client)
        await message.answer("Срок подписки?", reply_markup=sub_duration_ps_kb())
        await AddClient.step6_sub1_duration.set()
    elif message.text == "EA Play":
        client = await state.get_data()
        client = client.get('client', {})
        client['sub1_name'] = "EA Play"
        await state.update_data(client=client)
        await message.answer("Срок подписки?", reply_markup=sub_duration_ea_kb())
        await AddClient.step6_sub1_duration.set()
    else:
        await message.answer("Выбери тип подписки!", reply_markup=sub_type1_kb())

@dp.message_handler(state=AddClient.step6_sub1_duration)
async def addclient_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    data = await state.get_data()
    client = data.get('client', {})
    if client['sub1_name'] == "EA Play" and message.text not in ["1м", "12м"]:
        await message.answer("Для EA Play — 1м или 12м!", reply_markup=sub_duration_ea_kb())
        return
    if client['sub1_name'] != "EA Play" and message.text not in ["1м", "3м", "12м"]:
        await message.answer("Для PS Plus — 1м, 3м или 12м!", reply_markup=sub_duration_ps_kb())
        return
    client['sub1_duration'] = message.text
    await state.update_data(client=client)
    await message.answer("Введите дату оформления первой подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.step6_sub1_start.set()

@dp.message_handler(state=AddClient.step6_sub1_start)
async def addclient_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    date = message.text.strip()
    client = await state.get_data()
    client = client.get('client', {})
    client['sub1_start'] = date
    client['sub1_end'] = calc_sub_end(date, client['sub1_duration'])
    await state.update_data(client=client)
    if client.get('sub1_name') in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        await message.answer("<b>Шаг 6</b>\nКакая вторая подписка?", reply_markup=sub_type2_only_ea_kb())
        await AddClient.step6_sub2_type.set()
    else:
        await message.answer("<b>Шаг 7</b>\nОформлены игры?", reply_markup=yes_no_kb())
        await AddClient.step7_games_exist.set()

@dp.message_handler(state=AddClient.step6_sub2_type)
async def addclient_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text == "EA Play":
        client = await state.get_data()
        client = client.get('client', {})
        client['sub2_name'] = "EA Play"
        await state.update_data(client=client)
        await message.answer("Срок подписки?", reply_markup=sub_duration_ea_kb())
        await AddClient.step6_sub2_duration.set()
    else:
        await message.answer("Вторая подписка только EA Play", reply_markup=sub_type2_only_ea_kb())

@dp.message_handler(state=AddClient.step6_sub2_duration)
async def addclient_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text not in ["1м", "12м"]:
        await message.answer("EA Play: только 1м или 12м!", reply_markup=sub_duration_ea_kb())
        return
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_duration'] = message.text
    await state.update_data(client=client)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.step6_sub2_start.set()

@dp.message_handler(state=AddClient.step6_sub2_start)
async def addclient_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    date = message.text.strip()
    client = await state.get_data()
    client = client.get('client', {})
    client['sub2_start'] = date
    client['sub2_end'] = calc_sub_end(date, client['sub2_duration'])
    await state.update_data(client=client)
    await message.answer("<b>Шаг 7</b>\nОформлены игры?", reply_markup=yes_no_kb())
    await AddClient.step7_games_exist.set()

@dp.message_handler(state=AddClient.step7_games_exist)
async def addclient_games_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text == "Да":
        await message.answer("Напиши какие игры:", reply_markup=cancel_kb())
        await AddClient.step7_games.set()
    elif message.text == "Нет":
        client = await state.get_data()
        client = client.get('client', {})
        client['games'] = ""
        await state.update_data(client=client)
        await message.answer("Есть ли резервные коды?", reply_markup=yes_no_ru_kb())
        await AddClient.step8_reserve_exist.set()
    else:
        await message.answer("Да или Нет?", reply_markup=yes_no_kb())

@dp.message_handler(state=AddClient.step7_games)
async def addclient_games_input(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    games = message.text.strip().replace('\n', ' —— ')
    client = await state.get_data()
    client = client.get('client', {})
    client['games'] = games
    await state.update_data(client=client)
    await message.answer("Есть ли резервные коды?", reply_markup=yes_no_ru_kb())
    await AddClient.step8_reserve_exist.set()

@dp.message_handler(state=AddClient.step8_reserve_exist)
async def addclient_reserve_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
        return
    if message.text == "Есть":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=cancel_kb())
        await AddClient.step8_reserve_upload.set()
    elif message.text == "Нету":
        client = await state.get_data()
        client = client.get('client', {})
        client['reserve_codes_path'] = ""
        database.add_client(client)
        await state.finish()
        await clear_chat(message.chat.id)
        text = f"✅ <b>{client.get('identifier','')}</b> добавлен\n\n"
        text += format_info(client)
        await show_edit_info(message, text, None, client)
    else:
        await message.answer("Есть или Нету?", reply_markup=yes_no_ru_kb())

@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=AddClient.step8_reserve_upload)
async def addclient_reserve_upload(message: types.Message, state: FSMContext):
    if message.caption == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Главное меню:", reply_markup=build_main_menu())
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
    text = f"✅ <b>{client.get('identifier','')}</b> добавлен\n\n"
    text += format_info(client)
    await show_edit_info(message, text, file_path, client)

async def show_edit_info(message, text, doc_path, client):
    msg = await message.answer(text, reply_markup=edit_kb())
    if doc_path:
        try:
            await message.answer_document(InputFile(doc_path))
        except Exception as e:
            pass
    await AddClient.editing.set()
    async with dp.current_state(user=message.from_user.id).proxy() as data:
        data['current_info'] = client
        data['main_msg'] = msg.message_id

@dp.message_handler(state=AddClient.editing)
async def edit_main(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get('current_info', {})
    if message.text == "✅ Сохранить":
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer(f"✅ <b>{client.get('identifier','')}</b> добавлен", reply_markup=build_main_menu())
        return
    edit_map = {
        "📱 Изменить номер": ("identifier", "Введите новый номер телефона или Telegram:"),
        "📅 Изменить дату рождения": ("birthday", "Введите новую дату рождения (дд.мм.гггг):"),
        "🔐 Изменить аккаунт": ("account", "Данные аккаунта:\n\n1. Логин (почта)\n2. Пароль от аккаунта\n3. Пароль от почты (если есть, иначе оставьте пустым)"),
        "🌍 Изменить регион": ("region", "Какой регион аккаунта?\n(укр) (тур) (другой)"),
        "🖼 Изменить резерв коды": ("reserve_codes_path", "Загрузите новый скриншот с резервными кодами:"),
        "💳 Изменить подписку": ("sub", "<b>Шаг 5</b>\nОформлена ли подписка?"),
        "🎮 Изменить игры": ("games", "Напиши какие игры:")
    }
    if message.text in edit_map:
        field, prompt = edit_map[message.text]
        await state.update_data(editing_field=field)
        await message.answer(prompt, reply_markup=cancel_kb())
        await AddClient.edit_field.set()
    else:
        await message.answer("Используйте кнопки для изменения или сохраните.", reply_markup=edit_kb())

@dp.message_handler(state=AddClient.edit_field, content_types=types.ContentTypes.ANY)
async def edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get('current_info', {})
    field = data.get('editing_field')
    if message.text == "❌ Отмена" or (getattr(message, 'caption', None) == "❌ Отмена"):
        await state.set_state(AddClient.editing.state)
        text = f"✅ <b>{client.get('identifier','')}</b> добавлен\n\n" + format_info(client)
        await clear_chat(message.chat.id)
        await show_edit_info(message, text, client.get('reserve_codes_path',''), client)
        return
    if field == "identifier":
        client['identifier'] = message.text.strip()
        msg_text = "Успешно обновлены номер/ник!"
    elif field == "birthday":
        client['birthday'] = message.text.strip()
        msg_text = "Успешно обновлена дата рождения!"
    elif field == "account":
        lines = message.text.strip().split("\n")
        if len(lines) < 2:
            await message.answer("Введите три строки:\nлогин\nпароль от аккаунта\nпароль от почты (если нет — оставьте пустым)", reply_markup=cancel_kb())
            return
        client['email'] = lines[0].strip()
        client['account_pass'] = lines[1].strip()
        client['mail_pass'] = lines[2].strip() if len(lines) > 2 else ""
        msg_text = "Успешно обновлены данные аккаунта!"
    elif field == "region":
        reg = message.text.strip()
        if reg not in ["(укр)", "(тур)", "(другой)"]:
            await message.answer("Выбери один из вариантов! (укр) (тур) (другой)", reply_markup=region_kb())
            return
        client['region'] = reg
        msg_text = "Успешно обновлен регион!"
    elif field == "reserve_codes_path":
        if message.document:
            file = await message.document.download()
            file_path = f'reserves/{message.document.file_name}'
            os.makedirs('reserves', exist_ok=True)
            shutil.move(file.name, file_path)
            client['reserve_codes_path'] = file_path
            msg_text = "Успешно обновлены резерв коды!"
        else:
            await message.answer("Загрузите документ-скриншот!", reply_markup=cancel_kb())
            return
    elif field == "sub":
        await message.answer("<b>Шаг 5</b>\nОформлена ли подписка?", reply_markup=yes_no_kb())
        await AddClient.step5_sub_exist.set()
        await state.update_data(current_info=client)
        return
    elif field == "games":
        client['games'] = message.text.strip().replace('\n', ' —— ')
        msg_text = "Успешно обновлены игры!"
    else:
        await message.answer("Ошибка поля.", reply_markup=edit_kb())
        return
    database.update_client(client)
    await state.update_data(current_info=client)
    await state.set_state(AddClient.editing.state)
    await clear_chat(message.chat.id)
    text = f"{msg_text}\n\n✅ <b>{client.get('identifier','')}</b> добавлен\n\n" + format_info(client)
    await show_edit_info(message, text, client.get('reserve_codes_path',''), client)

@dp.message_handler(lambda m: m.text == "🔍 Найти клиента")
async def searchclient_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Введите номер или Telegram-ник для поиска:", reply_markup=cancel_kb())

@dp.message_handler()
async def fallback_handler(message: types.Message, state: FSMContext):
    await message.answer("Выберите действие из меню!", reply_markup=build_main_menu())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
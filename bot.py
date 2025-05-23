import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import database

API_TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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

def build_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить клиента"))
    kb.add(KeyboardButton("🔍 Найти клиента"))
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def yes_no_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def yes_no_ru_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Есть"), KeyboardButton("Нету"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def region_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("(укр)"), KeyboardButton("(тур)"), KeyboardButton("(другой)"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_type1_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_type2_only_ea_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("EA Play"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_duration_ps_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_duration_ea_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("1м"), KeyboardButton("12м"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def edit_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📱 Изменить номер"), KeyboardButton("📅 Изменить дату рождения"))
    kb.add(KeyboardButton("🔐 Изменить аккаунт"), KeyboardButton("🌍 Изменить регион"))
    kb.add(KeyboardButton("🖼 Изменить резерв коды"), KeyboardButton("💳 Изменить подписку"))
    kb.add(KeyboardButton("🎮 Изменить игры"))
    kb.add(KeyboardButton("✅ Сохранить"))
    return kb

async def remember_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    messages = data.get('messages', [])
    messages.append(message.message_id)
    await state.update_data(messages=messages)

async def clear_chat(chat_id, state: FSMContext):
    data = await state.get_data()
    messages = data.get('messages', [])
    for msg_id in messages:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    await state.update_data(messages=[])

def calc_sub_end(date, duration):
    import datetime
    d, m, y = map(int, date.split('.'))
    dt = datetime.date(y, m, d)
    if duration == "1м":
        month = dt.month + 1
        year = dt.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(dt.day, [31,29 if year%4==0 else 28,31,30,31,30,31,31,30,31,30,31][month-1])
        dt2 = datetime.date(year, month, day)
    elif duration == "3м":
        month = dt.month + 3
        year = dt.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(dt.day, [31,29 if year%4==0 else 28,31,30,31,30,31,31,30,31,30,31][month-1])
        dt2 = datetime.date(year, month, day)
    elif duration == "12м":
        dt2 = datetime.date(dt.year + 1, dt.month, dt.day)
    else:
        dt2 = dt
    return dt.strftime('%d.%m.%Y') + ' → ' + dt2.strftime('%d.%m.%Y')

def format_info(client):
    result = ""
    idf = client.get('identifier', '')
    birthday = client.get('birthday', '')
    result += f"👤 <b>{idf}</b>"
    if birthday and birthday != "отсутствует":
        result += f" | {birthday}"
    result += "\n"
    email = client.get('email', '')
    acc_pass = client.get('account_pass', '')
    region = client.get('region', '')
    result += f"🔐 {email}; {acc_pass} {region}\n"
    mail_pass = client.get('mail_pass', '')
    if mail_pass:
        result += f"✉️ Почта-пароль: {mail_pass}\n"
    s1 = client.get('sub1_name', '')
    s1d = client.get('sub1_duration', '')
    s1e = client.get('sub1_end', '')
    s2 = client.get('sub2_name', '')
    s2d = client.get('sub2_duration', '')
    s2e = client.get('sub2_end', '')
    if s1:
        result += f"📅 {s1} {s1d}\n{s1e}\n"
    if s2:
        result += f"📅 {s2} {s2d}\n{s2e}\n"
    if not s1 and not s2:
        result += "📅 Подписки: отсутствует\n"
    result += f"🌍 Регион: {region}\n"
    games = client.get('games', '')
    if games:
        result += f"🎮 Игры:\n• " + "\n• ".join(games.replace(' —— ', '\n').split('\n'))
    return result.strip()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_chat(message.chat.id, state)
    msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
    await remember_message(msg, state)

@dp.message_handler(lambda m: m.text == "➕ Добавить клиента")
async def addclient_start(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_chat(message.chat.id, state)
    msg = await message.answer("<b>Шаг 1</b>\nНомер телефона или Telegram:", reply_markup=cancel_kb())
    await remember_message(msg, state)
    await AddClient.step1_identifier.set()

@dp.message_handler(state=AddClient.step1_identifier)
async def addclient_idf(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    client = {'identifier': message.text.strip()}
    await state.update_data(client=client)
    msg = await message.answer("<b>Шаг 2</b>\nДата рождения есть?", reply_markup=yes_no_kb())
    await remember_message(msg, state)
    await AddClient.step2_birthday_exist.set()

@dp.message_handler(state=AddClient.step2_birthday_exist)
async def addclient_birthday_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text == "Да":
        msg = await message.answer("<b>Шаг 2</b>\nВведите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb())
        await remember_message(msg, state)
        await AddClient.step2_birthday.set()
    elif message.text == "Нет":
        data = await state.get_data()
        client = data.get('client', {})
        client['birthday'] = "отсутствует"
        await state.update_data(client=client)
        msg = await message.answer("<b>Шаг 3</b>\nДанные аккаунта:\n\n1. Логин (почта)\n2. Пароль от аккаунта\n3. Пароль от почты (если есть, иначе оставьте пустым)", reply_markup=cancel_kb())
        await remember_message(msg, state)
        await AddClient.step3_account.set()
    else:
        msg = await message.answer("Да или Нет?", reply_markup=yes_no_kb())
        await remember_message(msg, state)

@dp.message_handler(state=AddClient.step2_birthday)
async def addclient_birthday(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['birthday'] = message.text.strip()
    await state.update_data(client=client)
    msg = await message.answer("<b>Шаг 3</b>\nДанные аккаунта:\n\n1. Логин (почта)\n2. Пароль от аккаунта\n3. Пароль от почты (если есть, иначе оставьте пустым)", reply_markup=cancel_kb())
    await remember_message(msg, state)
    await AddClient.step3_account.set()

@dp.message_handler(state=AddClient.step3_account)
async def addclient_account(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    lines = message.text.strip().split("\n")
    if len(lines) < 2:
        msg = await message.answer("Введите три строки:\nлогин\nпароль от аккаунта\nпароль от почты (если нет — оставьте пустым)", reply_markup=cancel_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['email'] = lines[0].strip()
    client['account_pass'] = lines[1].strip()
    client['mail_pass'] = lines[2].strip() if len(lines) > 2 else ""
    await state.update_data(client=client)
    msg = await message.answer("<b>Шаг 4</b>\nКакой регион аккаунта?", reply_markup=region_kb())
    await remember_message(msg, state)
    await AddClient.step4_region.set()

@dp.message_handler(state=AddClient.step4_region)
async def addclient_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    reg = message.text.strip()
    if reg not in ["(укр)", "(тур)", "(другой)"]:
        msg = await message.answer("Выбери один из вариантов! (укр) (тур) (другой)", reply_markup=region_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['region'] = reg
    await state.update_data(client=client)
    msg = await message.answer("<b>Шаг 5</b>\nОформлена ли подписка?", reply_markup=yes_no_kb())
    await remember_message(msg, state)
    await AddClient.step5_sub_exist.set()

@dp.message_handler(state=AddClient.step5_sub_exist)
async def addclient_sub_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text == "Да":
        msg = await message.answer("<b>Шаг 5</b>\nОдна или две подписки?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Одна"), KeyboardButton("Две")).add(KeyboardButton("❌ Отмена")))
        await remember_message(msg, state)
        await AddClient.step5_sub_count.set()
    elif message.text == "Нет":
        data = await state.get_data()
        client = data.get('client', {})
        client['sub1_name'] = ""
        client['sub1_duration'] = ""
        client['sub1_start'] = ""
        client['sub1_end'] = ""
        client['sub2_name'] = ""
        client['sub2_duration'] = ""
        client['sub2_start'] = ""
        client['sub2_end'] = ""
        await state.update_data(client=client)
        msg = await message.answer("<b>Шаг 6</b>\nОформлены игры?", reply_markup=yes_no_kb())
        await remember_message(msg, state)
        await AddClient.step7_games_exist.set()
    else:
        msg = await message.answer("Да или Нет?", reply_markup=yes_no_kb())
        await remember_message(msg, state)

@dp.message_handler(state=AddClient.step5_sub_count)
async def addclient_sub_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text == "Одна":
        msg = await message.answer("Выберите подписку:", reply_markup=sub_type1_kb())
        await remember_message(msg, state)
        await AddClient.step6_sub1_type.set()
    elif message.text == "Две":
        msg = await message.answer("Первая подписка:", reply_markup=sub_type1_kb())
        await remember_message(msg, state)
        await AddClient.step6_sub1_type.set()
    else:
        msg = await message.answer("Одна или Две?", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Одна"), KeyboardButton("Две")).add(KeyboardButton("❌ Отмена")))
        await remember_message(msg, state)

@dp.message_handler(state=AddClient.step6_sub1_type)
async def addclient_sub1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        msg = await message.answer("Выбери из списка", reply_markup=sub_type1_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['sub1_name'] = message.text
    await state.update_data(client=client)
    msg = await message.answer("Срок подписки?", reply_markup=sub_duration_ps_kb())
    await remember_message(msg, state)
    await AddClient.step6_sub1_duration.set()

@dp.message_handler(state=AddClient.step6_sub1_duration)
async def addclient_sub1_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text not in ["1м", "3м", "12м"]:
        msg = await message.answer("Выбери срок!", reply_markup=sub_duration_ps_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['sub1_duration'] = message.text
    await state.update_data(client=client)
    msg = await message.answer("Дата оформления первой подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await remember_message(msg, state)
    await AddClient.step6_sub1_start.set()

@dp.message_handler(state=AddClient.step6_sub1_start)
async def addclient_sub1_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    try:
        calc = calc_sub_end(message.text.strip(), (await state.get_data())["client"]["sub1_duration"])
    except:
        msg = await message.answer("Дата в формате дд.мм.гггг!", reply_markup=cancel_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['sub1_start'] = message.text.strip()
    client['sub1_end'] = calc
    await state.update_data(client=client)
    if data['client'].get('sub2_name') is not None or data['client'].get('sub2_duration') is not None:
        msg = await message.answer("Вторая подписка:", reply_markup=sub_type2_only_ea_kb())
        await remember_message(msg, state)
        await AddClient.step6_sub2_type.set()
    elif data.get('client', {}).get('sub2_name') is None:
        msg = await message.answer("<b>Шаг 6</b>\nОформлены игры?", reply_markup=yes_no_kb())
        await remember_message(msg, state)
        await AddClient.step7_games_exist.set()
    else:
        msg = await message.answer("Вторая подписка:", reply_markup=sub_type2_only_ea_kb())
        await remember_message(msg, state)
        await AddClient.step6_sub2_type.set()

@dp.message_handler(state=AddClient.step6_sub2_type)
async def addclient_sub2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text not in ["EA Play"]:
        msg = await message.answer("Выбери из списка", reply_markup=sub_type2_only_ea_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['sub2_name'] = message.text
    await state.update_data(client=client)
    msg = await message.answer("Срок подписки?", reply_markup=sub_duration_ea_kb())
    await remember_message(msg, state)
    await AddClient.step6_sub2_duration.set()

@dp.message_handler(state=AddClient.step6_sub2_duration)
async def addclient_sub2_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text not in ["1м", "12м"]:
        msg = await message.answer("Выбери срок!", reply_markup=sub_duration_ea_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['sub2_duration'] = message.text
    await state.update_data(client=client)
    msg = await message.answer("Дата оформления второй подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await remember_message(msg, state)
    await AddClient.step6_sub2_start.set()

@dp.message_handler(state=AddClient.step6_sub2_start)
async def addclient_sub2_start(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    try:
        calc = calc_sub_end(message.text.strip(), (await state.get_data())["client"]["sub2_duration"])
    except:
        msg = await message.answer("Дата в формате дд.мм.гггг!", reply_markup=cancel_kb())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['sub2_start'] = message.text.strip()
    client['sub2_end'] = calc
    await state.update_data(client=client)
    msg = await message.answer("<b>Шаг 6</b>\nОформлены игры?", reply_markup=yes_no_kb())
    await remember_message(msg, state)
    await AddClient.step7_games_exist.set()

@dp.message_handler(state=AddClient.step7_games_exist)
async def addclient_games_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text == "Да":
        msg = await message.answer("Напиши какие игры (каждая на новой строке):", reply_markup=cancel_kb())
        await remember_message(msg, state)
        await AddClient.step7_games.set()
    elif message.text == "Нет":
        data = await state.get_data()
        client = data.get('client', {})
        client['games'] = ""
        await state.update_data(client=client)
        msg = await message.answer("<b>Шаг 7</b>\nРезервные коды есть?", reply_markup=yes_no_ru_kb())
        await remember_message(msg, state)
        await AddClient.step8_reserve_exist.set()
    else:
        msg = await message.answer("Да или Нет?", reply_markup=yes_no_kb())
        await remember_message(msg, state)

@dp.message_handler(state=AddClient.step7_games)
async def addclient_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    data = await state.get_data()
    client = data.get('client', {})
    client['games'] = message.text.replace('\n', ' —— ')
    await state.update_data(client=client)
    msg = await message.answer("<b>Шаг 7</b>\nРезервные коды есть?", reply_markup=yes_no_ru_kb())
    await remember_message(msg, state)
    await AddClient.step8_reserve_exist.set()

@dp.message_handler(state=AddClient.step8_reserve_exist)
async def addclient_reserve_exist(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await clear_chat(message.chat.id, state)
        msg = await message.answer("Главное меню:", reply_markup=build_main_menu())
        await remember_message(msg, state)
        return
    if message.text == "Есть":
        msg = await message.answer("Загрузи скриншот с резервными кодами:", reply_markup=cancel_kb())
        await remember_message(msg, state)
        await AddClient.step8_reserve_upload.set()
    elif message.text == "Нету":
        data = await state.get_data()
        client = data.get('client', {})
        client['reserve'] = ""
        await state.update_data(client=client)
        await finish_add(message, state)
    else:
        msg = await message.answer("Есть или Нету?", reply_markup=yes_no_ru_kb())
        await remember_message(msg, state)

@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddClient.step8_reserve_upload)
async def addclient_reserve_upload(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    client = data.get('client', {})
    client['reserve'] = photo_id
    await state.update_data(client=client)
    await finish_add(message, state)

async def finish_add(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get('client', {})
    await clear_chat(message.chat.id, state)
    database.add_client(client)
    info = format_info(client)
    msg = await message.answer(f"✅ <b>{client['identifier']}</b> добавлен!\n\n{info}", reply_markup=edit_kb())
    await remember_message(msg, state)
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

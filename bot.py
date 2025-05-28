import json
import logging
import asyncio
from datetime import datetime, timedelta
from dateutil.parser import parse
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart

# Конфигурация бота
API_TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460
DB_FILE = 'clients_db.json'

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename='bot.log', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния FSM для добавления/редактирования клиента
class AddClient(StatesGroup):
    number_or_tg = State()
    birthdate_choice = State()
    birthdate = State()
    account_data = State()
    region = State()
    console = State()
    subscription_choice = State()
    subscription_count = State()
    subscription1_type = State()
    subscription1_term = State()
    subscription1_date = State()
    subscription2_type = State()
    subscription2_term = State()
    subscription2_date = State()
    games_choice = State()
    games = State()
    reserve_codes_choice = State()
    reserve_codes_photo = State()

class EditClient(StatesGroup):
    search = State()
    edit_field = State()
    new_value = State()

# Загрузка базы данных
def load_db():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON базы данных")
        return {}

# Сохранение базы данных
def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Очистка чата
async def clean_chat(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        message_ids = data.get('message_ids', [])
        for msg_id in message_ids:
            try:
                await bot.delete_message(message.chat.id, msg_id)
            except:
                pass
        await state.update_data(message_ids=[])
    except Exception as e:
        logger.error(f"Ошибка при очистке чата: {e}")

# Валидация формата даты
def validate_date(date_str):
    try:
        return parse(date_str, dayfirst=True).date()
    except:
        return None

# Расчёт даты окончания подписки
def calculate_end_date(start_date, term):
    start = parse(start_date, dayfirst=True).date()
    if term == '1 мес':
        return start + timedelta(days=30)
    elif term == '3 мес':
        return start + timedelta(days=90)
    elif term == '12 мес':
        return start + timedelta(days=365)
    return start

# Форматирование карточки клиента
def format_client_card(client):
    card = [
        f"📋 *Клиент*",
        f"📱 *Контакт*: {client.get('telegram', client.get('number', 'Не указан'))}",
        f"📅 *Дата рождения*: {client.get('birthdate', 'Отсутствует')}",
        f"🎮 *Консоль*: {client.get('console', 'Не указана')}",
        f"🔐 *Аккаунт*: {client.get('account', {}).get('login', 'Не указан')}",
        f"📧 *Почта-пароль*: {client.get('account', {}).get('email', 'Не указана')}",
        f"🌍 *Регион*: {client.get('region', 'Не указан')}",
        f"🎲 *Игры*: {', '.join(client.get('games', [])) if client.get('games') else 'Отсутствуют'}",
        f"🖼 *Резервные коды*: {'Есть' if client.get('reserve_photo_id') else 'Отсутствуют'}",
        f"💳 *Подписки*:"
    ]
    for sub in client.get('subscriptions', []):
        card.append(f"  - {sub['type']} ({sub['term']}, до {sub['end_date']})")
    return '\n'.join(card)

# Клавиатура главного меню
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("➕ Добавить клиента"), KeyboardButton("🔍 Найти клиента"))
    return keyboard

# Кнопка отмены
def get_cancel_button():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

# Инлайн-кнопки для редактирования
def get_edit_buttons():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("📱 Номер-TG", callback_data="edit_number"),
        InlineKeyboardButton("📅 Дата рождения", callback_data="edit_birthdate"),
        InlineKeyboardButton("🔐 Аккаунт", callback_data="edit_account"),
        InlineKeyboardButton("🎮 Консоль", callback_data="edit_console"),
        InlineKeyboardButton("🌍 Регион", callback_data="edit_region"),
        InlineKeyboardButton("🖼 Резерв коды", callback_data="edit_reserve"),
        InlineKeyboardButton("💳 Подписка", callback_data="edit_subscription"),
        InlineKeyboardButton("🎲 Игры", callback_data="edit_games"),
        InlineKeyboardButton("🗑 Удалить клиента", callback_data="delete_client"),
        InlineKeyboardButton("✅ Сохранить", callback_data="save_client")
    ]
    keyboard.add(*buttons)
    return keyboard

# Команда /start
@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Доступ запрещён.")
        return
    await clean_chat(message, state)
    msg = await message.answer("Главное меню", reply_markup=get_main_menu())
    await state.update_data(message_ids=[msg.message_id])

# Добавление клиента
@dp.message(lambda message: message.text == "➕ Добавить клиента")
async def add_client(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await clean_chat(message, state)
    msg = await message.answer("Введите номер телефона или Telegram (@username):", reply_markup=get_cancel_button())
    await state.update_data(client={}, message_ids=[msg.message_id])
    await AddClient.number_or_tg.set()

@dp.message(AddClient.number_or_tg)
async def process_number_or_tg(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    if message.text.startswith('@'):
        client_data['telegram'] = message.text
    else:
        client_data['number'] = message.text
    await state.update_data(client=client_data)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
    msg = await message.answer("Указать дату рождения?", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.birthdate_choice.set()

@dp.message(AddClient.birthdate_choice)
async def process_birthdate_choice(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    if message.text == "Нет":
        client_data['birthdate'] = "Отсутствует"
        await state.update_data(client=client_data)
        msg = await message.answer("Введите данные аккаунта (логин, пароль, почта-пароль, каждая строка отдельно):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.account_data.set()
    elif message.text == "Да":
        msg = await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.birthdate.set()

@dp.message(AddClient.birthdate)
async def process_birthdate(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    if validate_date(message.text):
        client_data = (await state.get_data()).get('client', {})
        client_data['birthdate'] = message.text
        await state.update_data(client=client_data)
        msg = await message.answer("Введите данные аккаунта (логин, пароль, почта-пароль, каждая строка отдельно):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.account_data.set()
    else:
        msg = await message.answer("Неверный формат даты. Введите снова (дд.мм.гггг):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])

@dp.message(AddClient.account_data)
async def process_account_data(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    lines = message.text.strip().split('\n')
    client_data = (await state.get_data()).get('client', {})
    client_data['account'] = {
        'login': lines[0] if lines else 'Не указан',
        'password': lines[1] if len(lines) > 1 else '',
        'email': lines[2] if len(lines) > 2 else ''
    }
    await state.update_data(client=client_data)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("укр"), KeyboardButton("тур"), KeyboardButton("другой"), KeyboardButton("❌ Отмена"))
    msg = await message.answer("Выберите регион аккаунта:", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.region.set()

@dp.message(AddClient.region)
async def process_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    client_data['region'] = message.text
    await state.update_data(client=client_data)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("PS4"), KeyboardButton("PS5"), KeyboardButton("PS4/PS5"), KeyboardButton("❌ Отмена"))
    msg = await message.answer("Выберите консоль:", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.console.set()

@dp.message(AddClient.console)
async def process_console(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    client_data['console'] = message.text
    await state.update_data(client=client_data)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
    msg = await message.answer("Есть подписки?", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.subscription_choice.set()

@dp.message(AddClient.subscription_choice)
async def process_subscription_choice(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    if message.text == "Нет":
        client_data['subscriptions'] = [{'type': 'отсутствует', 'term': '', 'start_date': '', 'end_date': ''}]
        await state.update_data(client=client_data)
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
        msg = await message.answer("Оформлены игры?", reply_markup=keyboard)
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.games_choice.set()
    elif message.text == "Да":
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Одна"), KeyboardButton("Две"), KeyboardButton("❌ Отмена"))
        msg = await message.answer("Сколько подписок?", reply_markup=keyboard)
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.subscription_count.set()

@dp.message(AddClient.subscription_count)
async def process_subscription_count(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    await state.update_data(sub_count=1 if message.text == "Одна" else 2)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential"), KeyboardButton("EA Play"), KeyboardButton("❌ Отмена"))
    msg = await message.answer("Выберите тип первой подписки:", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.subscription1_type.set()

@dp.message(AddClient.subscription1_type)
async def process_subscription1_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    await state.update_data(sub1_type=message.text)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    terms = ["1 мес", "12 мес"] if message.text == "EA Play" else ["1 мес", "3 мес", "12 мес"]
    keyboard.add(*[KeyboardButton(term) for term in terms], KeyboardButton("❌ Отмена"))
    msg = await message.answer("Выберите срок подписки:", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.subscription1_term.set()

@dp.message(AddClient.subscription1_term)
async def process_subscription1_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    await state.update_data(sub1_term=message.text)
    msg = await message.answer("Введите дату оформления подписки (дд.мм.гггг):", reply_markup=get_cancel_button())
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.subscription1_date.set()

@dp.message(AddClient.subscription1_date)
async def process_subscription1_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    if validate_date(message.text):
        data = await state.get_data()
        client_data = data.get('client', {})
        client_data.setdefault('subscriptions', []).append({
            'type': data.get('sub1_type'),
            'term': data.get('sub1_term'),
            'start_date': message.text,
            'end_date': calculate_end_date(message.text, data.get('sub1_term')).strftime('%d.%m.%Y')
        })
        await state.update_data(client=client_data)
        if data.get('sub_count') == 2:
            available_types = ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"] if data.get('sub1_type') == "EA Play" else ["EA Play"]
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(*[KeyboardButton(t) for t in available_types], KeyboardButton("❌ Отмена"))
            msg = await message.answer("Выберите тип второй подписки:", reply_markup=keyboard)
            await state.update_data(message_ids=[msg.message_id])
            await AddClient.subscription2_type.set()
        else:
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
            msg = await message.answer("Оформлены игры?", reply_markup=keyboard)
            await state.update_data(message_ids=[msg.message_id])
            await AddClient.games_choice.set()
    else:
        msg = await message.answer("Неверный формат даты. Введите снова (дд.мм.гггг):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])

@dp.message(AddClient.subscription2_type)
async def process_subscription2_type(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    await state.update_data(sub2_type=message.text)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    terms = ["1 мес", "12 мес"] if message.text == "EA Play" else ["1 мес", "3 мес", "12 мес"]
    keyboard.add(*[KeyboardButton(term) for term in terms], KeyboardButton("❌ Отмена"))
    msg = await message.answer("Выберите срок второй подписки:", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.subscription2_term.set()

@dp.message(AddClient.subscription2_term)
async def process_subscription2_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    await state.update_data(sub2_term=message.text)
    msg = await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=get_cancel_button())
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.subscription2_date.set()

@dp.message(AddClient.subscription2_date)
async def process_subscription2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    if validate_date(message.text):
        data = await state.get_data()
        client_data = data.get('client', {})
        client_data['subscriptions'].append({
            'type': data.get('sub2_type'),
            'term': data.get('sub2_term'),
            'start_date': message.text,
            'end_date': calculate_end_date(message.text, data.get('sub2_term')).strftime('%d.%m.%Y')
        })
        await state.update_data(client=client_data)
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
        msg = await message.answer("Оформлены игры?", reply_markup=keyboard)
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.games_choice.set()
    else:
        msg = await message.answer("Неверный формат даты. Введите снова (дд.мм.гггг):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])

@dp.message(AddClient.games_choice)
async def process_games_choice(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    if message.text == "Нет":
        client_data['games'] = []
        await state.update_data(client=client_data)
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
        msg = await message.answer("Есть резервные коды?", reply_markup=keyboard)
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.reserve_codes_choice.set()
    elif message.text == "Да":
        msg = await message.answer("Введите список игр (каждая с новой строки):", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.games.set()

@dp.message(AddClient.games)
async def process_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    client_data['games'] = message.text.strip().split('\n')
    await state.update_data(client=client_data)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
    msg = await message.answer("Есть резервные коды?", reply_markup=keyboard)
    await state.update_data(message_ids=[msg.message_id])
    await AddClient.reserve_codes_choice.set()

@dp.message(AddClient.reserve_codes_choice)
async def process_reserve_codes_choice(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    client_data = (await state.get_data()).get('client', {})
    if message.text == "Нет":
        client_data['reserve_photo_id'] = None
        await state.update_data(client=client_data)
        await finalize_client(message, state)
    elif message.text == "Да":
        msg = await message.answer("Отправьте фото резервных кодов:", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])
        await AddClient.reserve_codes_photo.set()

@dp.message(AddClient.reserve_codes_photo, content_types=types.ContentType.PHOTO)
async def process_reserve_codes_photo(message: types.Message, state: FSMContext):
    client_data = (await state.get_data()).get('client', {})
    client_data['reserve_photo_id'] = message.photo[-1].file_id
    await state.update_data(client=client_data)
    await finalize_client(message, state)

async def finalize_client(message: types.Message, state: FSMContext):
    await clean_chat(message, state)
    client_data = (await state.get_data()).get('client', {})
    db = load_db()
    client_id = str(len(db) + 1)
    db[client_id] = client_data
    save_db(db)
    msg = await message.answer(format_client_card(client_data), parse_mode="Markdown", reply_markup=get_edit_buttons())
    await state.update_data(client_id=client_id, message_ids=[msg.message_id])
    asyncio.create_task(auto_delete_card(msg.chat.id, msg.message_id))
    await state.set_state(EditClient.edit_field)

# Поиск клиента
@dp.message(lambda message: message.text == "🔍 Найти клиента")
async def search_client(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await clean_chat(message, state)
    msg = await message.answer("Введите номер телефона или Telegram (@username):", reply_markup=get_cancel_button())
    await state.update_data(message_ids=[msg.message_id])
    await EditClient.search.set()

@dp.message(EditClient.search)
async def process_search(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await clean_chat(message, state)
        msg = await message.answer("Главное меню", reply_markup=get_main_menu())
        await state.update_data(message_ids=[msg.message_id])
        await state.reset_state()
        return
    db = load_db()
    client_id = None
    search_term = message.text
    for cid, client in db.items():
        if client.get('number') == search_term or client.get('telegram') == search_term:
            client_id = cid
            break
    if client_id:
        client = db[client_id]
        msg = await message.answer(format_client_card(client), parse_mode="Markdown", reply_markup=get_edit_buttons())
        await state.update_data(client_id=client_id, message_ids=[msg.message_id], client=client)
        asyncio.create_task(auto_delete_card(msg.chat.id, msg.message_id))
        await EditClient.edit_field.set()
    else:
        msg = await message.answer("Клиент не найден. Попробовать снова?", reply_markup=get_cancel_button())
        await state.update_data(message_ids=[msg.message_id])

# Автоудаление карточки
async def auto_delete_card(chat_id, message_id):
    await asyncio.sleep(300)  # 5 минут
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

# Редактирование клиента
@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    field = callback.data.replace("edit_", "")
    await callback.message.delete()
    if field == "number":
        msg = await callback.message.answer("Введите новый номер телефона или Telegram (@username):", reply_markup=get_cancel_button())
        await state.update_data(edit_field="number_or_tg", message_ids=[msg.message_id])
        await EditClient.new_value.set()
    elif field == "birthdate":
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Да"), KeyboardButton("Нет"), KeyboardButton("❌ Отмена"))
        msg = await callback.message.answer("Указать дату рождения?", reply_markup=keyboard)
        await state.update_data(edit_field="birthdate_choice", message_ids=[msg.message_id])
        await EditClient.new_value.set()
    # ... (Аналогичные обработчики для других полей)

@dp.callback_query(lambda c: c.data == "save_client")
async def save_client(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    client_id = data.get('client_id')
    client_data = data.get('client')
    if client_id and client_data:
        db = load_db()
        db[client_id] = client_data
        save_db(db)
        await callback.message.answer("Данные клиента сохранены.")
    await clean_chat(callback.message, state)
    msg = await callback.message.answer("Главное меню", reply_markup=get_main_menu())
    await state.update_data(message_ids=[msg.message_id])
    await state.reset_state()

# Уведомления о подписке
async def check_subscriptions():
    while True:
        db = load_db()
        today = datetime.now().date()
        one_day = timedelta(days=1)
        for client_id, client in db.items():
            for sub in client.get('subscriptions', []):
                if sub['type'] == 'отсутствует':
                    continue
                end_date = parse(sub['end_date'], dayfirst=True).date()
                if end_date - today == one_day:
                    card = format_client_card(client)
                    msg = await bot.send_message(ADMIN_ID, f"Напоминание: подписка истекает завтра\n\n{card}", parse_mode="Markdown", reply_markup=get_edit_buttons())
                    asyncio.create_task(auto_delete_card(msg.chat.id, msg.message_id))
        await asyncio.sleep(86400)  # Проверка раз в день

# Экспорт базы данных
@dp.message(Command('export_db'))
async def export_db(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await clean_chat(message, state)
    with open(DB_FILE, 'rb') as f:
        await bot.send_document(ADMIN_ID, f, caption="База данных клиентов")
    msg = await message.answer("Главное меню", reply_markup=get_main_menu())
    await state.update_data(message_ids=[msg.message_id])

# Импорт базы данных
@dp.message(Command('import_db'))
async def import_db(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await clean_chat(message, state)
    msg = await message.answer("Отправьте JSON файл базы данных:", reply_markup=get_cancel_button())
    await state.update_data(message_ids=[msg.message_id], import_db=True)

@dp.message(lambda message: message.document)
async def process_import_db(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    if not data.get('import_db'):
        return
    try:
        file = await bot.get_file(message.document.file_id)
        file_path = file.file_path
        file_content = await bot.download_file(file_path)
        new_db = json.loads(file_content.read().decode('utf-8'))
        save_db(new_db)
        await message.answer("База данных успешно импортирована.")
    except Exception as e:
        logger.error(f"Ошибка импорта базы данных: {e}")
        await message.answer("Ошибка при импорте базы данных.")
    await clean_chat(message, state)
    msg = await message.answer("Главное меню", reply_markup=get_main_menu())
    await state.update_data(message_ids=[msg.message_id], import_db=False)

# Удаление клиента
@dp.callback_query(lambda c: c.data == "delete_client")
async def delete_client(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    client_id = data.get('client_id')
    if client_id:
        db = load_db()
        if client_id in db:
            del db[client_id]
            save_db(db)
            await callback.message.answer("Клиент удалён.")
        else:
            await callback.message.answer("Клиент не найден.")
    await clean_chat(callback.message, state)
    msg = await callback.message.answer("Главное меню", reply_markup=get_main_menu())
    await state.update_data(message_ids=[msg.message_id])
    await state.reset_state()

# Запуск бота и проверки подписок
async def main():
    asyncio.create_task(check_subscriptions())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
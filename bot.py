import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from database import save_client, load_clients

TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AddClient(StatesGroup):
    step1 = State()
    step2 = State()
    step3 = State()
    step4 = State()
    step5_start = State()
    step5_subs = State()
    step5_sub1_name = State()
    step5_sub1_period = State()
    step5_sub1_date = State()
    step5_sub2_name = State()
    step5_sub2_period = State()
    step5_sub2_date = State()
    step6_games = State()
    step7_codes = State()
    step7_codes_photo = State()
    confirm = State()
    edit_menu = State()
    edit_field = State()

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Добавить клиента"))
    kb.add(KeyboardButton("🔍 Найти клиента"))
    return kb

def cancel_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('❌ Отмена'))

def yes_no_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def region_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("(укр)"), KeyboardButton("(тур)"), KeyboardButton("(другой)"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def sub_count_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Одна"), KeyboardButton("Две"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def psplus_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"))
    kb.add(KeyboardButton("PS Plus Essential"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def eaplay_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("EA Play"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def sub_period_kb(options=("1м", "3м", "12м")):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for opt in options:
        kb.insert(KeyboardButton(opt))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def games_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def reserve_codes_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Есть"), KeyboardButton("Нету"))
    kb.add(KeyboardButton('❌ Отмена'))
    return kb

def edit_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("📱 Изменить номер"), KeyboardButton("📅 Изменить дату рождения"))
    kb.add(KeyboardButton("🔐 Изменить аккаунт"), KeyboardButton("🌍 Изменить регион"))
    kb.add(KeyboardButton("🖼 Изменить резерв коды"), KeyboardButton("💳 Изменить подписку"))
    kb.add(KeyboardButton("🎮 Изменить игры"), KeyboardButton("✅ Сохранить"))
    return kb

async def clear_chat(chat_id):
    async for msg in bot.iter_history(chat_id, limit=100):
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except:
            continue

@dp.message_handler(commands=['start'], state='*')
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Выберите действие:", reply_markup=main_menu())

@dp.message_handler(lambda m: m.text == "➕ Добавить клиента", state='*')
async def add_client_start(message: types.Message, state: FSMContext):
    await state.finish()
    await clear_chat(message.chat.id)
    await message.answer("Шаг 1\n<b>Номер телефона или Telegram:</b>", parse_mode="HTML", reply_markup=cancel_kb())
    await AddClient.step1.set()

@dp.message_handler(state=AddClient.step1, content_types=types.ContentTypes.TEXT)
async def add_client_step1(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(contact=message.text)
    await message.answer("Шаг 2\nДата рождения\n(Есть/Нету)", reply_markup=yes_no_kb())
    await AddClient.step2.set()

@dp.message_handler(state=AddClient.step2, content_types=types.ContentTypes.TEXT)
async def add_client_step2(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    if message.text == "Есть":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb())
    elif message.text == "Нет":
        await state.update_data(birthday="отсутствует")
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=cancel_kb())
        await AddClient.step3.set()
        return
    else:
        await message.answer("Пожалуйста, выберите «Есть» или «Нет».", reply_markup=yes_no_kb())
        return
    await AddClient.step2.set()
    await state.update_data(waiting_birthday=True)

@dp.message_handler(state=AddClient.step2, content_types=types.ContentTypes.TEXT)
async def add_client_step2_birthday(message: types.Message, state: FSMContext):
    if await state.get_data():
        d = await state.get_data()
        if d.get("waiting_birthday"):
            if message.text == '❌ Отмена':
                await state.finish()
                await clear_chat(message.chat.id)
                await message.answer("Выберите действие:", reply_markup=main_menu())
                return
            await state.update_data(birthday=message.text)
            await state.update_data(waiting_birthday=False)
            await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=cancel_kb())
            await AddClient.step3.set()

@dp.message_handler(state=AddClient.step3, content_types=types.ContentTypes.TEXT)
async def add_client_step3(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    lines = message.text.strip().split('\n')
    login = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mailpass = lines[2] if len(lines) > 2 else ""
    await state.update_data(login=login, password=password, mailpass=mailpass)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb())
    await AddClient.step4.set()

@dp.message_handler(state=AddClient.step4, content_types=types.ContentTypes.TEXT)
async def add_client_step4(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(region=message.text)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())
    await AddClient.step5_start.set()

@dp.message_handler(state=AddClient.step5_start, content_types=types.ContentTypes.TEXT)
async def add_client_step5_start(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[])
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=games_kb())
        await AddClient.step6_games.set()
        return
    await message.answer("Сколько подписок?", reply_markup=sub_count_kb())
    await AddClient.step5_subs.set()

@dp.message_handler(state=AddClient.step5_subs, content_types=types.ContentTypes.TEXT)
async def add_client_step5_subs(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(sub_count=message.text)
    await message.answer("Какая первая подписка?", reply_markup=psplus_kb())
    await AddClient.step5_sub1_name.set()

@dp.message_handler(state=AddClient.step5_sub1_name, content_types=types.ContentTypes.TEXT)
async def add_client_step5_sub1_name(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(sub1_name=message.text)
    if message.text == "EA Play":
        await message.answer("Срок подписки?", reply_markup=sub_period_kb(("1м", "12м")))
    else:
        await message.answer("Срок подписки?", reply_markup=sub_period_kb(("1м", "3м", "12м")))
    await AddClient.step5_sub1_period.set()

@dp.message_handler(state=AddClient.step5_sub1_period, content_types=types.ContentTypes.TEXT)
async def add_client_step5_sub1_period(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(sub1_period=message.text)
    await message.answer("Введите дату оформления первой подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.step5_sub1_date.set()

@dp.message_handler(state=AddClient.step5_sub1_date, content_types=types.ContentTypes.TEXT)
async def add_client_step5_sub1_date(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(sub1_date=message.text)
    data = await state.get_data()
    if data.get("sub_count") == "Одна":
        await state.update_data(subscriptions=[{
            "name": data["sub1_name"],
            "period": data["sub1_period"],
            "start": data["sub1_date"]
        }])
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=games_kb())
        await AddClient.step6_games.set()
        return
    sub1 = data["sub1_name"]
    if sub1 == "EA Play":
        await message.answer("Какая вторая подписка?", reply_markup=psplus_kb())
    else:
        await message.answer("Какая вторая подписка?", reply_markup=eaplay_kb())
    await AddClient.step5_sub2_name.set()

@dp.message_handler(state=AddClient.step5_sub2_name, content_types=types.ContentTypes.TEXT)
async def add_client_step5_sub2_name(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(sub2_name=message.text)
    if message.text == "EA Play":
        await message.answer("Срок подписки?", reply_markup=sub_period_kb(("1м", "12м")))
    else:
        await message.answer("Срок подписки?", reply_markup=sub_period_kb(("1м", "3м", "12м")))
    await AddClient.step5_sub2_period.set()

@dp.message_handler(state=AddClient.step5_sub2_period, content_types=types.ContentTypes.TEXT)
async def add_client_step5_sub2_period(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    await state.update_data(sub2_period=message.text)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.step5_sub2_date.set()

@dp.message_handler(state=AddClient.step5_sub2_date, content_types=types.ContentTypes.TEXT)
async def add_client_step5_sub2_date(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    data = await state.get_data()
    sub1 = {
        "name": data["sub1_name"],
        "period": data["sub1_period"],
        "start": data["sub1_date"]
    }
    sub2 = {
        "name": data["sub2_name"],
        "period": data["sub2_period"],
        "start": message.text
    }
    await state.update_data(subscriptions=[sub1, sub2])
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=games_kb())
    await AddClient.step6_games.set()

@dp.message_handler(state=AddClient.step6_games, content_types=types.ContentTypes.TEXT)
async def add_client_step6_games(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    if message.text == "Да":
        await message.answer("Напиши какие игры (каждая на новой строке):", reply_markup=cancel_kb())
        await AddClient.step6_games.set()
        await state.update_data(waiting_games=True)
        return
    await state.update_data(games=[])
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=reserve_codes_kb())
    await AddClient.step7_codes.set()

@dp.message_handler(state=AddClient.step6_games, content_types=types.ContentTypes.TEXT)
async def add_client_step6_games_list(message: types.Message, state: FSMContext):
    d = await state.get_data()
    if d.get("waiting_games"):
        if message.text == '❌ Отмена':
            await state.finish()
            await clear_chat(message.chat.id)
            await message.answer("Выберите действие:", reply_markup=main_menu())
            return
        games = [g.strip() for g in message.text.split('\n') if g.strip()]
        await state.update_data(games=games)
        await state.update_data(waiting_games=False)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=reserve_codes_kb())
        await AddClient.step7_codes.set()

@dp.message_handler(state=AddClient.step7_codes, content_types=types.ContentTypes.TEXT)
async def add_client_step7_codes(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())
        return
    if message.text == "Есть":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=cancel_kb())
        await AddClient.step7_codes_photo.set()
        return
    await state.update_data(reserve_codes=None)
    await finish_add_client(message, state)

@dp.message_handler(state=AddClient.step7_codes_photo, content_types=types.ContentTypes.PHOTO)
async def add_client_step7_codes_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(reserve_codes=file_id)
    await finish_add_client(message, state)

@dp.message_handler(state=AddClient.step7_codes_photo, content_types=types.ContentTypes.TEXT)
async def add_client_step7_codes_photo_text(message: types.Message, state: FSMContext):
    if message.text == '❌ Отмена':
        await state.finish()
        await clear_chat(message.chat.id)
        await message.answer("Выберите действие:", reply_markup=main_menu())

async def finish_add_client(message, state):
    data = await state.get_data()
    await clear_chat(message.chat.id)
    save_client(data)
    info = format_client_info(data)
    await message.answer(f"✅ {data['contact']} добавлен\n\n{info}", parse_mode="HTML", reply_markup=edit_kb())
    await state.finish()

def format_client_info(data):
    info = ""
    info += f"👤 <b>{data.get('contact')}</b>"
    if data.get('birthday'):
        info += f" | {data['birthday']}\n"
    else:
        info += "\n"
    info += f"🔐 <b>{data.get('login')}; {data.get('password')} {data.get('region','')}</b>\n"
    if data.get('mailpass'):
        info += f"✉️ Почта-пароль: {data.get('mailpass')}\n"
    if data.get('subscriptions'):
        for sub in data['subscriptions']:
            name = sub.get('name')
            period = sub.get('period')
            start = sub.get('start')
            end = calc_end_date(start, period)
            info += f"\n💳 {name} {period}\n📅 {start} → {end}"
    else:
        info += "\n💳 Подписки: (отсутствует)"
    info += f"\n🌍 Регион: {data.get('region','')}\n"
    if data.get('games'):
        info += "\n🎮 Игры:\n"
        for g in data['games']:
            info += f"• {g}\n"
    return info

from datetime import datetime
from dateutil.relativedelta import relativedelta

def calc_end_date(start, period):
    try:
        start_dt = datetime.strptime(start, "%d.%m.%Y")
    except:
        return "неизвестно"
    if period == "1м":
        end = start_dt + relativedelta(months=1)
    elif period == "3м":
        end = start_dt + relativedelta(months=3)
    elif period == "12м":
        end = start_dt + relativedelta(months=12)
    else:
        end = start_dt
    return end.strftime("%d.%m.%Y")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
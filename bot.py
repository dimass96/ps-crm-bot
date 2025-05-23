import logging
import os
import shutil
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime
from database import save_client

API_TOKEN = '7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8'
ADMIN_ID = 350902460

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AddClient(StatesGroup):
    waiting_id = State()
    waiting_birthday = State()
    waiting_birthday_value = State()
    waiting_account = State()
    waiting_region = State()
    waiting_sub_status = State()
    waiting_sub_count = State()
    waiting_sub1_type = State()
    waiting_sub1_period = State()
    waiting_sub1_start = State()
    waiting_sub2_period = State()
    waiting_sub2_start = State()
    waiting_games_status = State()
    waiting_games_value = State()
    waiting_codes = State()
    waiting_codes_upload = State()

main_menu_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_kb.add(KeyboardButton("➕ Добавить клиента"))
main_menu_kb.add(KeyboardButton("🔍 Найти клиента"))

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def yes_no_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Да"), KeyboardButton("Нет"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def region_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("(укр)"), KeyboardButton("(тур)"), KeyboardButton("(другой)"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub_count_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Одна"), KeyboardButton("Две"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub1_type_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("PS Plus Deluxe"), KeyboardButton("PS Plus Extra"), KeyboardButton("PS Plus Essential"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub1_period_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("1м"), KeyboardButton("3м"), KeyboardButton("12м"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def sub2_period_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("1м"), KeyboardButton("12м"))
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def edit_buttons():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🖲 Изменить номер", callback_data="edit_id"),
        InlineKeyboardButton("📅 Изменить дату рождения", callback_data="edit_birthday"),
        InlineKeyboardButton("🔑 Изменить аккаунт", callback_data="edit_account"),
        InlineKeyboardButton("🌎 Изменить регион", callback_data="edit_region"),
        InlineKeyboardButton("🖼 Изменить резерв коды", callback_data="edit_codes"),
        InlineKeyboardButton("💳 Изменить подписку", callback_data="edit_sub"),
        InlineKeyboardButton("🎮 Изменить игры", callback_data="edit_games"),
        InlineKeyboardButton("✅ Сохранить", callback_data="save_confirm")
    )
    return kb

async def clear_chat(chat_id):
    async for m in bot.iter_chat_members(chat_id, 0):
        pass

def parse_account_data(raw):
    lines = [l.strip() for l in raw.strip().split('\n') if l.strip()]
    login = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mailpass = lines[2] if len(lines) > 2 else ""
    return login, password, mailpass

def format_info(client):
    parts = []
    if client.get("codes_path"):
        parts.append('🖼 <b>Резервные коды загружены</b>')
    id_line = f'👤 <b>{client["id"]}</b>'
    if client.get("birthday"):
        id_line += f' | {client["birthday"]}'
    else:
        id_line += ' | отсутствует'
    parts.append(id_line)
    login, password, mailpass = parse_account_data(client.get("account", ""))
    region = client.get("region", "")
    acc_line = f'🔐 <b>{login}</b>; <b>{password}</b> {region}'
    parts.append(acc_line)
    if mailpass:
        parts.append(f'✉️ Почта-пароль: <b>{mailpass}</b>')
    if client.get("sub1"):
        sub1 = client["sub1"]
        parts.append(f'💳 {sub1["name"]} {sub1["period"]} {region}')
        parts.append(f'🗓 {sub1["start"]} → {sub1["end"]}')
    if client.get("sub2"):
        sub2 = client["sub2"]
        parts.append(f'💳 {sub2["name"]} {sub2["period"]} {region}')
        parts.append(f'🗓 {sub2["start"]} → {sub2["end"]}')
    if client.get("games"):
        games = client["games"].split(' —— ')
        if games and any(g.strip() for g in games):
            games_list = "\n".join([f"• {g.strip()}" for g in games if g.strip()])
            parts.append(f'🎮 Игры:\n{games_list}')
    return "\n\n".join(parts)

def calculate_end_date(start, period):
    dt = datetime.strptime(start, "%d.%m.%Y")
    if period == "1м":
        month = dt.month + 1
        year = dt.year
        if month > 12:
            month -= 12
            year += 1
        end = dt.replace(month=month, year=year)
    elif period == "3м":
        month = dt.month + 3
        year = dt.year
        if month > 12:
            month -= 12
            year += 1
        end = dt.replace(month=month, year=year)
    elif period == "12м":
        end = dt.replace(year=dt.year + 1)
    else:
        end = dt
    return end.strftime("%d.%m.%Y")

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Меню", reply_markup=main_menu_kb)

@dp.message_handler(lambda m: m.text == "➕ Добавить клиента")
async def add_client_start(message: types.Message, state: FSMContext):
    await state.finish()
    await state.update_data(new_client={})
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=cancel_kb())
    await AddClient.waiting_id.set()

@dp.message_handler(lambda m: m.text == "❌ Отмена", state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Меню", reply_markup=main_menu_kb)

@dp.message_handler(state=AddClient.waiting_id)
async def step_id(message: types.Message, state: FSMContext):
    await state.update_data(new_client={"id": message.text})
    await message.answer("Шаг 2\nДата рождения?\n", reply_markup=yes_no_kb())
    await AddClient.waiting_birthday.set()

@dp.message_handler(state=AddClient.waiting_birthday)
async def step_birthday(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=cancel_kb())
        await AddClient.waiting_birthday_value.set()
    else:
        data = await state.get_data()
        client = data.get("new_client", {})
        client["birthday"] = None
        await state.update_data(new_client=client)
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=cancel_kb())
        await AddClient.waiting_account.set()

@dp.message_handler(state=AddClient.waiting_birthday_value)
async def step_birthday_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("new_client", {})
    client["birthday"] = message.text
    await state.update_data(new_client=client)
    await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=cancel_kb())
    await AddClient.waiting_account.set()

@dp.message_handler(state=AddClient.waiting_account)
async def step_account(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = data.get("new_client", {})
    client["account"] = message.text
    await state.update_data(new_client=client)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb())
    await AddClient.waiting_region.set()

@dp.message_handler(state=AddClient.waiting_region)
async def step_region(message: types.Message, state: FSMContext):
    region = message.text.strip()
    data = await state.get_data()
    client = data.get("new_client", {})
    client["region"] = region
    await state.update_data(new_client=client)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())
    await AddClient.waiting_sub_status.set()

@dp.message_handler(state=AddClient.waiting_sub_status)
async def step_sub_status(message: types.Message, state: FSMContext):
    if message.text.lower() == "нет":
        data = await state.get_data()
        client = data.get("new_client", {})
        client["sub1"] = None
        client["sub2"] = None
        await state.update_data(new_client=client)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        await AddClient.waiting_games_status.set()
    else:
        await message.answer("Сколько подписок?", reply_markup=sub_count_kb())
        await AddClient.waiting_sub_count.set()

@dp.message_handler(state=AddClient.waiting_sub_count)
async def step_sub_count(message: types.Message, state: FSMContext):
    await state.update_data(sub_count=message.text)
    if message.text == "Одна":
        await message.answer("Выберите подписку:", reply_markup=sub1_type_kb())
        await AddClient.waiting_sub1_type.set()
    elif message.text == "Две":
        await message.answer("Какая первая подписка?", reply_markup=sub1_type_kb())
        await AddClient.waiting_sub1_type.set()
    else:
        await message.answer("Выберите 'Одна' или 'Две'.", reply_markup=sub_count_kb())

@dp.message_handler(state=AddClient.waiting_sub1_type)
async def step_sub1_type(message: types.Message, state: FSMContext):
    if message.text not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]:
        await message.answer("Выберите тип подписки.", reply_markup=sub1_type_kb())
        return
    await state.update_data(sub1_name=message.text)
    await message.answer("Срок подписки?", reply_markup=sub1_period_kb())
    await AddClient.waiting_sub1_period.set()

@dp.message_handler(state=AddClient.waiting_sub1_period)
async def step_sub1_period(message: types.Message, state: FSMContext):
    if message.text not in ["1м", "3м", "12м"]:
        await message.answer("Выберите срок подписки.", reply_markup=sub1_period_kb())
        return
    await state.update_data(sub1_period=message.text)
    await message.answer("Введите дату оформления первой подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.waiting_sub1_start.set()

@dp.message_handler(state=AddClient.waiting_sub1_start)
async def step_sub1_start(message: types.Message, state: FSMContext):
    sub1_start = message.text
    data = await state.get_data()
    client = data.get("new_client", {})
    sub1_name = data.get("sub1_name")
    sub1_period = data.get("sub1_period")
    region = client.get("region", "")
    sub1_end = calculate_end_date(sub1_start, sub1_period)
    client["sub1"] = {"name": sub1_name, "period": sub1_period, "region": region, "start": sub1_start, "end": sub1_end}
    await state.update_data(new_client=client)
    sub_count = data.get("sub_count")
    if sub_count == "Две":
        await message.answer("Вторая подписка — EA Play", reply_markup=sub2_period_kb())
        await AddClient.waiting_sub2_period.set()
    else:
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        await AddClient.waiting_games_status.set()

@dp.message_handler(state=AddClient.waiting_sub2_period)
async def step_sub2_period(message: types.Message, state: FSMContext):
    if message.text not in ["1м", "12м"]:
        await message.answer("Выберите срок.", reply_markup=sub2_period_kb())
        return
    await state.update_data(sub2_period=message.text)
    await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):", reply_markup=cancel_kb())
    await AddClient.waiting_sub2_start.set()

@dp.message_handler(state=AddClient.waiting_sub2_start)
async def step_sub2_start(message: types.Message, state: FSMContext):
    sub2_start = message.text
    data = await state.get_data()
    client = data.get("new_client", {})
    sub2_period = data.get("sub2_period")
    region = client.get("region", "")
    sub2_end = calculate_end_date(sub2_start, sub2_period)
    client["sub2"] = {"name": "EA Play", "period": sub2_period, "region": region, "start": sub2_start, "end": sub2_end}
    await state.update_data(new_client=client)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
    await AddClient.waiting_games_status.set()

@dp.message_handler(state=AddClient.waiting_games_status)
async def step_games_status(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        await message.answer("Напиши какие игры (каждая на новой строке):", reply_markup=cancel_kb())
        await AddClient.waiting_games_value.set()
    else:
        data = await state.get_data()
        client = data.get("new_client", {})
        client["games"] = ""
        await state.update_data(new_client=client)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
        await AddClient.waiting_codes.set()

@dp.message_handler(state=AddClient.waiting_games_value)
async def step_games_value(message: types.Message, state: FSMContext):
    games = " —— ".join([line.strip() for line in message.text.split('\n') if line.strip()])
    data = await state.get_data()
    client = data.get("new_client", {})
    client["games"] = games
    await state.update_data(new_client=client)
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
    await AddClient.waiting_codes.set()

@dp.message_handler(state=AddClient.waiting_codes)
async def step_codes(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=cancel_kb())
        await AddClient.waiting_codes_upload.set()
    else:
        data = await state.get_data()
        client = data.get("new_client", {})
        client["codes_path"] = None
        await state.update_data(new_client=client)
        await finish_adding_client(message, state)

@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddClient.waiting_codes_upload)
async def codes_upload(message: types.Message, state: FSMContext):
    file = await message.photo[-1].download()
    codes_path = f"codes/{file.filename}"
    shutil.move(file.name, codes_path)
    data = await state.get_data()
    client = data.get("new_client", {})
    client["codes_path"] = codes_path
    await state.update_data(new_client=client)
    await finish_adding_client(message, state)

async def finish_adding_client(message, state: FSMContext):
    data = await state.get_data()
    client = data.get("new_client", {})
    save_client(client)
    await message.answer("✅ {} добавлен\n\n{}".format(client["id"], format_info(client)), parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await message.answer("Изменить данные:", reply_markup=edit_buttons())
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
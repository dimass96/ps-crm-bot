import os
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from database import add_client_to_db, update_client_in_db, find_client, load_db

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

class AddClientFSM(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_3 = State()
    step_4 = State()
    step_5 = State()
    step_5_subcount = State()
    step_5_sub1 = State()
    step_5_term1 = State()
    step_5_date1 = State()
    step_5_sub2 = State()
    step_5_term2 = State()
    step_5_date2 = State()
    step_6 = State()
    step_7 = State()
    codes_photo = State()
    editing = State()
    edit_field = State()
    edit_photo = State()

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента"), KeyboardButton(text="🔍 Найти клиента")]
        ], resize_keyboard=True
    )

def yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def region_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур"), KeyboardButton(text="другой")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def sub_count_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def sub_choice_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
            [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def psplus_term_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def eaplay_term_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def edit_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Изменить номер-TG"), KeyboardButton(text="📅 Изменить дату рождения")],
            [KeyboardButton(text="🔐 Изменить аккаунт"), KeyboardButton(text="🌍 Изменить регион")],
            [KeyboardButton(text="🖼 Изменить резерв коды"), KeyboardButton(text="💳 Изменить подписку")],
            [KeyboardButton(text="🎮 Изменить игры"), KeyboardButton(text="✅ Сохранить")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True
    )

def format_client_info(client):
    out = []
    out.append(f"👤 {client.get('number') or client.get('telegram') or ''} | {client.get('birthdate', 'отсутствует')}")
    acc = client.get('account', '')
    if acc:
        region = client.get("region", "")
        acc_line = acc
        if region:
            acc_line = f"{acc} ({region})"
        out.append(f"🔐 {acc_line}")
    if client.get('mailpass'):
        out.append(f"✉️ Почта-пароль: {client['mailpass']}")
    subs = client.get("subscriptions", [])
    if subs and subs[0].get("name") != "отсутствует":
        for s in subs:
            out.append(f"💳 {s['name']} {s['term']}")
            out.append(f"📅 {s['start']} → {s['end']}")
    else:
        out.append("💳 Подписки: (отсутствует)")
    region = client.get("region", "")
    out.append(f"🌍 Регион: {region}")
    games = client.get("games", [])
    if games:
        out.append("🎮 Игры:")
        for g in games:
            out.append(f"• {g}")
    if client.get("reserve_codes_path"):
        out.append("🖼 Резерв коды прикреплены ниже")
    return "\n".join(out)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

async def clear_chat(chat_id):
    pass

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("", reply_markup=ReplyKeyboardRemove())
    await message.answer("Выберите действие:", reply_markup=main_menu_kb())

@dp.message(lambda m: m.text == "➕ Добавить клиента")
async def add_client(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Шаг 1\nВведите номер телефона или Telegram:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClientFSM.step_1)

@dp.message(AddClientFSM.step_1)
async def add_step_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    value = message.text.strip()
    if value.startswith("+"):
        await state.update_data(number=value)
    elif value.startswith("@"):
        await state.update_data(telegram=value)
    else:
        await message.answer("Введите корректный номер (+...) или Telegram (@...):")
        return
    await state.set_state(AddClientFSM.step_2)
    await message.answer("Шаг 2\nДата рождения:\nЕсть?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_2)
async def add_step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(birthdate="отсутствует")
        await state.set_state(AddClientFSM.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:\n(логин, пароль, почта-пароль если есть, с новой строки)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "Да":
        await message.answer("Введите дату рождения:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.step_2)
        await state.update_data(wait_birth=True)
        return
    data = await state.get_data()
    if data.get("wait_birth"):
        await state.update_data(birthdate=message.text)
        await state.set_state(AddClientFSM.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:\n(логин, пароль, почта-пароль если есть, с новой строки)", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(AddClientFSM.step_3)
async def add_step_3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    lines = message.text.strip().split('\n')
    login = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mailpass = lines[2] if len(lines) > 2 else ""
    account = f"{login}; {password}" if password else login
    await state.update_data(account=account, mailpass=mailpass)
    await state.set_state(AddClientFSM.step_4)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb())

@dp.message(AddClientFSM.step_4)
async def add_step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    region = message.text.strip()
    await state.update_data(region=region)
    await state.set_state(AddClientFSM.step_5)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_5)
async def add_step_5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await state.set_state(AddClientFSM.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
        return
    if message.text == "Да":
        await message.answer("Сколько подписок?", reply_markup=sub_count_kb())
        await state.set_state(AddClientFSM.step_5_subcount)
        return

@dp.message(AddClientFSM.step_5_subcount)
async def subcount_step(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Одна":
        await message.answer("Выберите подписку", reply_markup=sub_choice_kb())
        await state.set_state(AddClientFSM.step_5_sub1)
        await state.update_data(sub_count=1)
        return
    if message.text == "Две":
        await message.answer("Выберите первую подписку", reply_markup=sub_choice_kb())
        await state.set_state(AddClientFSM.step_5_sub1)
        await state.update_data(sub_count=2)
        return

@dp.message(AddClientFSM.step_5_sub1)
async def sub1_choice(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    sub = message.text
    if sub not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Выберите из предложенных вариантов.")
        return
    await state.update_data(sub1=sub)
    if sub == "EA Play":
        await message.answer("Срок подписки:", reply_markup=eaplay_term_kb())
    else:
        await message.answer("Срок подписки:", reply_markup=psplus_term_kb())
    await state.set_state(AddClientFSM.step_5_term1)

@dp.message(AddClientFSM.step_5_term1)
async def sub1_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    sub = (await state.get_data()).get("sub1")
    if sub == "EA Play":
        if message.text not in ["1м", "12м"]:
            await message.answer("Выберите срок из предложенных.")
            return
    else:
        if message.text not in ["1м", "3м", "12м"]:
            await message.answer("Выберите срок из предложенных.")
            return
    await state.update_data(sub1_term=message.text)
    await message.answer("Дата оформления подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClientFSM.step_5_date1)

@dp.message(AddClientFSM.step_5_date1)
async def sub1_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y")
    except Exception:
        await message.answer("Введите дату в формате дд.мм.гггг")
        return
    data = await state.get_data()
    name = data.get("sub1")
    term = data.get("sub1_term")
    if term == "1м":
        end_date = start_date + timedelta(days=30)
    elif term == "3м":
        end_date = start_date + timedelta(days=90)
    else:
        end_date = start_date + timedelta(days=365)
    sub1 = {
        "name": name,
        "term": term,
        "start": start_date.strftime("%d.%m.%Y"),
        "end": end_date.strftime("%d.%m.%Y")
    }
    await state.update_data(sub1_data=sub1)
    sub_count = data.get("sub_count", 1)
    if sub_count == 1:
        await state.update_data(subscriptions=[sub1])
        await state.set_state(AddClientFSM.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())
    else:
        other = "EA Play" if name.startswith("PS Plus") else "PS Plus Deluxe"
        await message.answer("Выберите вторую подписку", reply_markup=sub_choice_kb())
        await state.set_state(AddClientFSM.step_5_sub2)

@dp.message(AddClientFSM.step_5_sub2)
async def sub2_choice(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    data = await state.get_data()
    sub1_name = data.get("sub1")
    if sub1_name.startswith("PS Plus") and message.text != "EA Play":
        await message.answer("Вторая подписка — только EA Play.")
        return
    if sub1_name == "EA Play" and not message.text.startswith("PS Plus"):
        await message.answer("Вторая подписка — только PS Plus.")
        return
    sub2 = message.text
    await state.update_data(sub2=sub2)
    if sub2 == "EA Play":
        await message.answer("Срок подписки:", reply_markup=eaplay_term_kb())
    else:
        await message.answer("Срок подписки:", reply_markup=psplus_term_kb())
    await state.set_state(AddClientFSM.step_5_term2)

@dp.message(AddClientFSM.step_5_term2)
async def sub2_term(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    sub = (await state.get_data()).get("sub2")
    if sub == "EA Play":
        if message.text not in ["1м", "12м"]:
            await message.answer("Выберите срок из предложенных.")
            return
    else:
        if message.text not in ["1м", "3м", "12м"]:
            await message.answer("Выберите срок из предложенных.")
            return
    await state.update_data(sub2_term=message.text)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state(AddClientFSM.step_5_date2)

@dp.message(AddClientFSM.step_5_date2)
async def sub2_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y")
    except Exception:
        await message.answer("Введите дату в формате дд.мм.гггг")
        return
    data = await state.get_data()
    name = data.get("sub2")
    term = data.get("sub2_term")
    if term == "1м":
        end_date = start_date + timedelta(days=30)
    elif term == "3м":
        end_date = start_date + timedelta(days=90)
    else:
        end_date = start_date + timedelta(days=365)
    sub2 = {
        "name": name,
        "term": term,
        "start": start_date.strftime("%d.%m.%Y"),
        "end": end_date.strftime("%d.%m.%Y")
    }
    subs = [data.get("sub1_data"), sub2]
    await state.update_data(subscriptions=subs)
    await state.set_state(AddClientFSM.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_6)
async def add_step_6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(games=[])
        await state.set_state(AddClientFSM.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())
        return
    if message.text == "Да":
        await message.answer("Впишите игры (каждая с новой строки):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.update_data(wait_games=True)
        return
    data = await state.get_data()
    if data.get("wait_games"):
        games = [x.strip() for x in message.text.split('\n') if x.strip()]
        await state.update_data(games=games)
        await state.set_state(AddClientFSM.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=yes_no_kb())

@dp.message(AddClientFSM.step_7)
async def add_step_7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "Нет":
        await state.update_data(reserve_codes_path=None)
        await finish_add_client(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите фото с резервными кодами:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        await state.set_state(AddClientFSM.codes_photo)
        return

@dp.message(AddClientFSM.codes_photo, F.photo)
async def codes_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    path = os.path.join(MEDIA_DIR, f"{file_id}.jpg")
    await message.bot.download(message.photo[-1], destination=path)
    await state.update_data(reserve_codes_path=path)
    await finish_add_client(message, state)

async def finish_add_client(message, state):
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    add_client_to_db(client)
    text = f"✅ {client.get('number') or client.get('telegram')} добавлен\n\n"
    text += format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        with open(client["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
    await state.set_state(AddClientFSM.editing)

@dp.message(AddClientFSM.editing)
async def edit_menu(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    if message.text == "✅ Сохранить":
        update_client_in_db(client)
        await message.answer(f"✅ {client.get('number') or client.get('telegram')} успешно сохранен!", reply_markup=main_menu_kb())
        await state.clear()
        return
    if message.text == "📱 Изменить номер-TG":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field_name="number")
        await message.answer("Введите новый номер или Telegram:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "📅 Изменить дату рождения":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field_name="birthdate")
        await message.answer("Введите новую дату рождения:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "🔐 Изменить аккаунт":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field_name="account")
        await message.answer("Введите новые данные аккаунта (логин, пароль, почта-пароль если есть, с новой строки):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "🌍 Изменить регион":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field_name="region")
        await message.answer("Выберите регион:", reply_markup=region_kb())
        return
    if message.text == "🖼 Изменить резерв коды":
        await state.set_state(AddClientFSM.edit_photo)
        await message.answer("Загрузите новые резервные коды:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    if message.text == "💳 Изменить подписку":
        await state.set_state(AddClientFSM.step_5)
        await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb())
        return
    if message.text == "🎮 Изменить игры":
        await state.set_state(AddClientFSM.edit_field)
        await state.update_data(edit_field_name="games")
        games_text = "\n".join(client.get("games", [])) if client.get("games") else ""
        await message.answer(f"Введите новые игры (каждая с новой строки):\n\n{games_text}", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return

@dp.message(AddClientFSM.edit_field)
async def edit_field_step(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.set_state(AddClientFSM.editing)
        data = await state.get_data()
        client = {
            "number": data.get("number", ""),
            "telegram": data.get("telegram", ""),
            "birthdate": data.get("birthdate", "отсутствует"),
            "account": data.get("account", ""),
            "mailpass": data.get("mailpass", ""),
            "region": data.get("region", ""),
            "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
            "games": data.get("games", []),
            "reserve_codes_path": data.get("reserve_codes_path", None)
        }
        text = format_client_info(client)
        kb = edit_kb()
        if client.get("reserve_codes_path"):
            with open(client["reserve_codes_path"], "rb") as img:
                await message.answer_photo(img, caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return
    field = (await state.get_data()).get("edit_field_name")
    if field == "number":
        val = message.text
        await state.update_data(number=val)
    elif field == "birthdate":
        val = message.text
        await state.update_data(birthdate=val)
    elif field == "account":
        lines = message.text.strip().split('\n')
        login = lines[0] if len(lines) > 0 else ""
        password = lines[1] if len(lines) > 1 else ""
        mailpass = lines[2] if len(lines) > 2 else ""
        account = f"{login}; {password}" if password else login
        await state.update_data(account=account, mailpass=mailpass)
    elif field == "region":
        await state.update_data(region=message.text.strip())
    elif field == "games":
        games = [x.strip() for x in message.text.split('\n') if x.strip()]
        await state.update_data(games=games)
    await state.set_state(AddClientFSM.editing)
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    text = format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        with open(client["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

@dp.message(AddClientFSM.edit_photo, F.photo)
async def edit_photo_step(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    path = os.path.join(MEDIA_DIR, f"{file_id}.jpg")
    await message.bot.download(message.photo[-1], destination=path)
    await state.update_data(reserve_codes_path=path)
    await state.set_state(AddClientFSM.editing)
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", [{"name": "отсутствует"}]),
        "games": data.get("games", []),
        "reserve_codes_path": data.get("reserve_codes_path", None)
    }
    text = format_client_info(client)
    kb = edit_kb()
    if client.get("reserve_codes_path"):
        with open(client["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

@dp.message(lambda m: m.text == "🔍 Найти клиента")
async def search_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите номер или Telegram для поиска:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    await state.set_state("searching")

@dp.message(lambda m: m.text == "❌ Отмена")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await start(message, state)

@dp.message(state="searching")
async def search_find(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await start(message, state)
        return
    c = find_client(message.text.strip())
    if not c:
        await message.answer("Клиент не найден.", reply_markup=main_menu_kb())
        await state.clear()
        return
    await state.clear()
    await state.set_state(AddClientFSM.editing)
    await state.update_data(**c)
    text = format_client_info(c)
    kb = edit_kb()
    if c.get("reserve_codes_path"):
        with open(c["reserve_codes_path"], "rb") as img:
            await message.answer_photo(img, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
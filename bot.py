import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460
DB_PATH = "clients_db.json"

class AddClient(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_2_1 = State()
    step_3 = State()
    step_4 = State()
    step_5 = State()
    step_5_sub1 = State()
    step_5_sub2 = State()
    step_5_sub3 = State()
    step_5_sub4 = State()
    step_5_sub5 = State()
    step_5_sub6 = State()
    step_5_sub7 = State()
    step_5_sub8 = State()
    step_5_sub9 = State()
    step_5_sub10 = State()
    step_6 = State()
    step_6_games = State()
    step_7 = State()
    step_7_photo = State()
    edit_number = State()
    edit_birthdate = State()
    edit_account = State()
    edit_region = State()
    edit_codes = State()
    edit_games = State()
    edit_subscription = State()

class SearchClient(StatesGroup):
    waiting_for_query = State()

def load_db():
    if not os.path.exists(DB_PATH):
        return []
    with open(DB_PATH, encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_db(clients):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def add_client_to_db(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

def update_client_in_db(index, client):
    clients = load_db()
    if 0 <= index < len(clients):
        clients[index] = client
        save_db(clients)

def find_client(search):
    clients = load_db()
    for i, c in enumerate(clients):
        if (c.get("number") and c["number"] == search) or (c.get("telegram") and c["telegram"] == search):
            return i, c
    return None, None

def month_delta(date, months):
    d = datetime.strptime(date, "%d.%m.%Y")
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, [31,29 if y % 4 == 0 and not y % 100 == 0 or y % 400 == 0 else 28,31,30,31,30,31,31,30,31,30,31][m - 1])
    return datetime(y, m, day).strftime("%d.%m.%Y")

def make_client_block(client):
    number = client.get("number") or client.get("telegram") or ""
    birth = client.get("birthdate", "отсутствует")
    acc = client.get("account", "")
    acc_mail = client.get("mailpass", "")
    games = client.get("games", [])
    subs = client.get("subscriptions", [])
    region = client.get("region", "отсутствует")
    block = f"👤 {number} | {birth}\n"
    block += f"🔐 {acc}\n" if acc else ""
    block += f"✉️ Почта-пароль: {acc_mail}\n" if acc_mail else ""
    if subs and subs[0]["name"] != "отсутствует":
        for s in subs:
            block += f"\n💳 {s['name']} {s['term']}\n"
            block += f"📅 {s['start']} → {s['end']}\n"
    else:
        block += "\n💳 Подписки: (отсутствует)\n"
    block += f"\n🌍 Регион: ({region})\n"
    if games:
        block += "\n🎮 Игры:\n"
        for g in games:
            block += f"• {g}\n"
    return block

def get_edit_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="📱 Изменить номер", callback_data="edit_number"),
            InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birthdate"),
        ],
        [
            InlineKeyboardButton(text="🔐 Изменить аккаунт", callback_data="edit_account"),
            InlineKeyboardButton(text="🌍 Изменить регион", callback_data="edit_region"),
        ],
        [
            InlineKeyboardButton(text="🖼 Изменить резервные коды", callback_data="edit_codes"),
            InlineKeyboardButton(text="💳 Изменить подписку", callback_data="edit_subscription"),
        ],
        [
            InlineKeyboardButton(text="🎮 Изменить игры", callback_data="edit_games"),
            InlineKeyboardButton(text="✅ Сохранить", callback_data="save_changes"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_main_menu():
    kb = [
        [KeyboardButton(text="➕ Добавить клиента")],
        [KeyboardButton(text="🔍 Найти клиента")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_kb():
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_yesno_kb():
    kb = [
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_subs_count_kb():
    kb = [
        [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_sub_type_kb():
    kb = [
        [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
        [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_term_kb(psplus=True):
    if psplus:
        kb = [
            [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ]
    else:
        kb = [
            [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
            [KeyboardButton(text="❌ Отмена")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_region_kb():
    kb = [
        [KeyboardButton(text="укр"), KeyboardButton(text="тур"), KeyboardButton(text="другой")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

bot = Bot(token=TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def clear_chat(chat_id, state: FSMContext, keep=None):
    try:
        async for msg in bot.get_chat_history(chat_id, limit=60):
            if keep and msg.message_id in keep:
                continue
            try:
                await bot.delete_message(chat_id, msg.message_id)
            except:
                pass
    except:
        pass

@dp.message(lambda m: m.text == "❌ Отмена")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(message.chat.id, state)

async def show_client_card(chat_id, client, state, edit_keyboard=True):
    text = make_client_block(client)
    if client.get("codes"):
        msg = await bot.send_photo(
            chat_id, client["codes"], caption=text,
            reply_markup=get_edit_keyboard() if edit_keyboard else None,
            parse_mode="HTML"
        )
        await state.update_data(last_card_msg_ids=[msg.message_id])
        await clear_chat(chat_id, state, keep=[msg.message_id])
    else:
        msg = await bot.send_message(
            chat_id, text,
            reply_markup=get_edit_keyboard() if edit_keyboard else None,
            parse_mode="HTML"
        )
        await state.update_data(last_card_msg_ids=[msg.message_id])
        await clear_chat(chat_id, state, keep=[msg.message_id])

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await clear_chat(message.chat.id, state)
    await message.answer("Выберите действие:", reply_markup=get_main_menu())

@dp.message(lambda m: m.text == "➕ Добавить клиента")
async def add_client(message: types.Message, state: FSMContext):
    await clear_chat(message.chat.id, state)
    await state.set_state(AddClient.step_1)
    await state.update_data(new_client={})
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_1)
async def step_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    num = message.text.strip()
    data = await state.get_data()
    client = data.get("new_client", {})
    if num.startswith("@"):
        client["telegram"] = num
        client["number"] = ""
    else:
        client["number"] = num
        client["telegram"] = ""
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_2)
    await message.answer("Шаг 2\nДата рождения:", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_2)
async def step_2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Есть":
        await state.set_state(AddClient.step_2_1)
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())
    elif message.text == "Нет":
        data = await state.get_data()
        client = data.get("new_client", {})
        client["birthdate"] = "отсутствует"
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=get_cancel_kb())
    else:
        await message.answer("Выберите Есть или Нету.", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_2_1)
async def step_2_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    date = message.text.strip()
    try:
        datetime.strptime(date, "%d.%m.%Y")
    except Exception:
        await message.answer("Некорректный формат даты! Пример: 01.05.1996", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    client = data.get("new_client", {})
    client["birthdate"] = date
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_3)
    await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_3)
async def step_3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    lines = message.text.split("\n")
    acc = lines[0].strip()
    pwd = lines[1].strip() if len(lines) > 1 else ""
    mailpass = lines[2].strip() if len(lines) > 2 else ""
    data = await state.get_data()
    client = data.get("new_client", {})
    client["account"] = acc + (f" ; {pwd}" if pwd else "")
    client["mailpass"] = mailpass
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_4)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=get_region_kb())

@dp.message(AddClient.step_4)
async def step_4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    region = message.text.strip()
    data = await state.get_data()
    client = data.get("new_client", {})
    client["region"] = region
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_5)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_5)
async def step_5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Нет":
        data = await state.get_data()
        client = data.get("new_client", {})
        client["subscriptions"] = [{"name": "отсутствует"}]
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())
    elif message.text == "Да":
        await state.set_state(AddClient.step_5_sub1)
        await message.answer("Сколько подписок оформлено?", reply_markup=get_subs_count_kb())
    else:
        await message.answer("Выберите Да или Нет.", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_5_sub1)
async def step_5_sub1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Одна":
        await state.set_state(AddClient.step_5_sub2)
        await message.answer("Выберите подписку:", reply_markup=get_sub_type_kb())
    elif message.text == "Две":
        await state.set_state(AddClient.step_5_sub3)
        await message.answer("Первая подписка:", reply_markup=get_sub_type_kb())
    else:
        await message.answer("Выберите Одна или Две.", reply_markup=get_subs_count_kb())

@dp.message(AddClient.step_5_sub2)
async def step_5_sub2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    name = message.text.strip()
    if name not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Выберите тип подписки:", reply_markup=get_sub_type_kb())
        return
    await state.update_data(sub1_type=name)
    await state.set_state(AddClient.step_5_sub4)
    await message.answer("Выберите срок:", reply_markup=get_term_kb(psplus=name != "EA Play"))

@dp.message(AddClient.step_5_sub4)
async def step_5_sub4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    term = message.text.strip()
    if term not in ["1м", "3м", "12м"]:
        await message.answer("Выберите срок:", reply_markup=get_term_kb())
        return
    await state.update_data(sub1_term=term)
    await state.set_state(AddClient.step_5_sub5)
    await message.answer("Дата оформления подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_5_sub5)
async def step_5_sub5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    try:
        d = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    client = data.get("new_client", {})
    sub = {
        "name": data.get("sub1_type"),
        "term": data.get("sub1_term"),
        "start": message.text.strip(),
        "end": month_delta(message.text.strip(), int(data.get("sub1_term").replace("м", "")))
    }
    client["subscriptions"] = [sub]
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_5_sub3)
async def step_5_sub3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    name1 = message.text.strip()
    if name1 not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Первая подписка:", reply_markup=get_sub_type_kb())
        return
    await state.update_data(sub1_type=name1)
    await state.set_state(AddClient.step_5_sub6)
    await message.answer("Срок первой подписки?", reply_markup=get_term_kb(psplus=name1 != "EA Play"))

@dp.message(AddClient.step_5_sub6)
async def step_5_sub6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    term1 = message.text.strip()
    if term1 not in ["1м", "3м", "12м"]:
        await message.answer("Срок первой подписки?", reply_markup=get_term_kb())
        return
    await state.update_data(sub1_term=term1)
    await state.set_state(AddClient.step_5_sub7)
    await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_5_sub7)
async def step_5_sub7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    try:
        d1 = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())
        return
    await state.update_data(sub1_start=message.text.strip())
    data = await state.get_data()
    cat1 = data.get("sub1_type")
    cat2 = "EA Play" if "PS Plus" in cat1 else "PS Plus Extra"
    await state.update_data(sub2_cat=cat2)
    await state.set_state(AddClient.step_5_sub8)
    await message.answer("Вторая подписка:", reply_markup=get_sub_type_kb())

@dp.message(AddClient.step_5_sub8)
async def step_5_sub8(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    name2 = message.text.strip()
    d = await state.get_data()
    cat2 = d.get("sub2_cat")
    if name2 not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
        await message.answer("Вторая подписка:", reply_markup=get_sub_type_kb())
        return
    if ("PS Plus" in name2 and "PS Plus" in d.get("sub1_type")) or ("EA Play" in name2 and "EA Play" in d.get("sub1_type")):
        await message.answer("Вторая подписка должна быть из другой категории.", reply_markup=get_sub_type_kb())
        return
    await state.update_data(sub2_type=name2)
    await state.set_state(AddClient.step_5_sub9)
    await message.answer("Срок второй подписки?", reply_markup=get_term_kb(psplus=name2 != "EA Play"))

@dp.message(AddClient.step_5_sub9)
async def step_5_sub9(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    term2 = message.text.strip()
    if term2 not in ["1м", "3м", "12м"]:
        await message.answer("Срок второй подписки?", reply_markup=get_term_kb())
        return
    await state.update_data(sub2_term=term2)
    await state.set_state(AddClient.step_5_sub10)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_5_sub10)
async def step_5_sub10(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    try:
        d2 = datetime.strptime(message.text.strip(), "%d.%m.%Y")
    except:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    client = data.get("new_client", {})
    sub1 = {
        "name": data.get("sub1_type"),
        "term": data.get("sub1_term"),
        "start": data.get("sub1_start"),
        "end": month_delta(data.get("sub1_start"), int(data.get("sub1_term").replace("м", "")))
    }
    sub2 = {
        "name": data.get("sub2_type"),
        "term": data.get("sub2_term"),
        "start": message.text.strip(),
        "end": month_delta(message.text.strip(), int(data.get("sub2_term").replace("м", "")))
    }
    client["subscriptions"] = [sub1, sub2]
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_6)
async def step_6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Да":
        await state.set_state(AddClient.step_6_games)
        await message.answer("Введите список игр, каждая на новой строке:", reply_markup=get_cancel_kb())
    elif message.text == "Нет":
        data = await state.get_data()
        client = data.get("new_client", {})
        client["games"] = []
        await state.update_data(new_client=client)
        await state.set_state(AddClient.step_7)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yesno_kb())
    else:
        await message.answer("Выберите Да или Нет.", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_6_games)
async def step_6_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    data = await state.get_data()
    client = data.get("new_client", {})
    client["games"] = games
    await state.update_data(new_client=client)
    await state.set_state(AddClient.step_7)
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_7)
async def step_7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Да":
        await state.set_state(AddClient.step_7_photo)
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=get_cancel_kb())
    elif message.text == "Нет":
        data = await state.get_data()
        client = data.get("new_client", {})
        client["codes"] = ""
        add_client_to_db(client)
        await state.clear()
        await show_client_card(message.chat.id, client, state)
    else:
        await message.answer("Выберите Да или Нет.", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_7_photo, F.photo)
async def step_7_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    client = data.get("new_client", {})
    client["codes"] = file_id
    add_client_to_db(client)
    await state.clear()
    await show_client_card(message.chat.id, client, state)

@dp.message(lambda m: m.text == "Меню")
async def menu_cmd(message: types.Message, state: FSMContext):
    await clear_chat(message.chat.id, state)
    await message.answer("Выберите действие:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "edit_number")
async def edit_number_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_number)
    await callback.message.answer("Введите новый номер или Telegram:", reply_markup=get_cancel_kb())

@dp.message(AddClient.edit_number)
async def do_edit_number(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    value = message.text.strip()
    idx, client = find_client(message.reply_to_message.text.split(" | ")[0].replace("👤", "").strip())
    if value.startswith("@"):
        client["telegram"] = value
        client["number"] = ""
    else:
        client["number"] = value
        client["telegram"] = ""
    update_client_in_db(idx, client)
    await show_client_card(message.chat.id, client, state)

@dp.callback_query(F.data == "edit_birthdate")
async def edit_birth_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_birthdate)
    await callback.message.answer("Введите новую дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())

@dp.message(AddClient.edit_birthdate)
async def do_edit_birth(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    value = message.text.strip()
    try:
        datetime.strptime(value, "%d.%m.%Y")
    except Exception:
        await message.answer("Некорректный формат даты! Пример: 01.05.1996", reply_markup=get_cancel_kb())
        return
    idx, client = find_client(message.reply_to_message.text.split(" | ")[0].replace("👤", "").strip())
    client["birthdate"] = value
    update_client_in_db(idx, client)
    await show_client_card(message.chat.id, client, state)

@dp.callback_query(F.data == "edit_account")
async def edit_acc_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_account)
    await callback.message.answer("Введите новые данные аккаунта:\nлогин\nпароль\nпочта-пароль (если есть)", reply_markup=get_cancel_kb())

@dp.message(AddClient.edit_account)
async def do_edit_acc(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    lines = message.text.split("\n")
    acc = lines[0].strip()
    pwd = lines[1].strip() if len(lines) > 1 else ""
    mailpass = lines[2].strip() if len(lines) > 2 else ""
    idx, client = find_client(message.reply_to_message.text.split(" | ")[0].replace("👤", "").strip())
    client["account"] = acc + (f" ; {pwd}" if pwd else "")
    client["mailpass"] = mailpass
    update_client_in_db(idx, client)
    await show_client_card(message.chat.id, client, state)

@dp.callback_query(F.data == "edit_region")
async def edit_region_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_region)
    await callback.message.answer("Выберите новый регион:", reply_markup=get_region_kb())

@dp.message(AddClient.edit_region)
async def do_edit_region(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    value = message.text.strip()
    idx, client = find_client(message.reply_to_message.text.split(" | ")[0].replace("👤", "").strip())
    client["region"] = value
    update_client_in_db(idx, client)
    await show_client_card(message.chat.id, client, state)

@dp.callback_query(F.data == "edit_codes")
async def edit_codes_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_codes)
    await callback.message.answer("Загрузите новый скриншот с резервными кодами:", reply_markup=get_cancel_kb())

@dp.message(AddClient.edit_codes, F.photo)
async def do_edit_codes_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    idx, client = find_client(message.reply_to_message.text.split(" | ")[0].replace("👤", "").strip())
    client["codes"] = file_id
    update_client_in_db(idx, client)
    await show_client_card(message.chat.id, client, state)

@dp.callback_query(F.data == "edit_games")
async def edit_games_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_games)
    await callback.message.answer("Введите новый список игр, каждая на новой строке:", reply_markup=get_cancel_kb())

@dp.message(AddClient.edit_games)
async def do_edit_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    idx, client = find_client(message.reply_to_message.text.split(" | ")[0].replace("👤", "").strip())
    client["games"] = games
    update_client_in_db(idx, client)
    await show_client_card(message.chat.id, client, state)

@dp.callback_query(F.data == "edit_subscription")
async def edit_sub_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(AddClient.edit_subscription)
    await callback.message.answer("Пока изменение подписки работает только через удаление и добавление заново.\n(можно доработать позже)", reply_markup=get_cancel_kb())

@dp.callback_query(F.data == "save_changes")
async def save_changes_cb(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await clear_chat(callback.message.chat.id, state)
    msg = await callback.message.answer("Информация успешно сохранена.", reply_markup=get_main_menu())
    await asyncio.sleep(10)
    await bot.delete_message(callback.message.chat.id, msg.message_id)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
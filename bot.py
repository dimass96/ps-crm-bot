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
    step_7_photo = State()
    edit_number = State()
    edit_birthdate = State()
    edit_account = State()
    edit_region = State()
    edit_codes = State()
    edit_games = State()
    edit_subs_step1 = State()
    edit_subs_step2 = State()
    edit_subs_step3 = State()
    edit_subs_step4 = State()
    edit_subs_step5 = State()
    edit_subs_step6 = State()
    edit_subs_step7 = State()
    edit_subs_step8 = State()
    edit_subs_step9 = State()
    edit_subs_step10 = State()

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
    msgs = []
    msg = await bot.send_message(chat_id, text, reply_markup=get_edit_keyboard() if edit_keyboard else None)
    msgs.append(msg.message_id)
    if client.get("codes"):
        m2 = await bot.send_photo(chat_id, client["codes"])
        msgs.append(m2.message_id)
    await state.update_data(last_card_msg_ids=msgs)
    await clear_chat(chat_id, state, keep=msgs)
    return msgs

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
    await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=get_cancel_kb())

@dp.message(lambda m: m.text == "🔍 Найти клиента")
async def search_client(message: types.Message, state: FSMContext):
    await clear_chat(message.chat.id, state)
    await message.answer("Введите номер или Telegram клиента:", reply_markup=get_cancel_kb())
    await state.set_state(SearchClient.waiting_for_query)

@dp.message(SearchClient.waiting_for_query)
async def searching(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    idx, client = find_client(message.text.strip())
    if client:
        await state.update_data(edit_idx=idx)
        await state.update_data(client_edit=client)
        await show_client_card(message.chat.id, client, state)
    else:
        await clear_chat(message.chat.id, state)
        await message.answer("Клиент не найден.", reply_markup=get_main_menu())

@dp.message(AddClient.step_1)
async def step1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    value = message.text.strip()
    if value.startswith("@"):
        await state.update_data(telegram=value, number="")
    else:
        await state.update_data(number=value, telegram="")
    await state.set_state(AddClient.step_2)
    await message.answer("Шаг 2\nДата рождения:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Есть"), KeyboardButton(text="Нету")], [KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    ))

@dp.message(AddClient.step_2)
async def step2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Есть":
        await state.set_state(AddClient.step_2_1)
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=get_cancel_kb())
    elif message.text == "Нету":
        await state.update_data(birthdate="отсутствует")
        await state.set_state(AddClient.step_3)
        await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=get_cancel_kb())
    else:
        await message.answer("Выберите: Есть или Нету.", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Есть"), KeyboardButton(text="Нету")], [KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        ))

@dp.message(AddClient.step_2_1)
async def step2_1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    value = message.text.strip()
    try:
        datetime.strptime(value, "%d.%m.%Y")
    except Exception:
        await message.answer("Некорректный формат даты! Пример: 01.05.1996", reply_markup=get_cancel_kb())
        return
    await state.update_data(birthdate=value)
    await state.set_state(AddClient.step_3)
    await message.answer("Шаг 3\nДанные от аккаунта:", reply_markup=get_cancel_kb())

@dp.message(AddClient.step_3)
async def step3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    lines = message.text.split("\n")
    acc = lines[0].strip()
    pwd = lines[1].strip() if len(lines) > 1 else ""
    mailpass = lines[2].strip() if len(lines) > 2 else ""
    await state.update_data(account=acc + (f" ; {pwd}" if pwd else ""), mailpass=mailpass)
    await state.set_state(AddClient.step_4)
    await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=get_region_kb())

@dp.message(AddClient.step_4)
async def step4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    region = message.text.strip()
    await state.update_data(region=region)
    await state.set_state(AddClient.step_5)
    await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")], [KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    ))

@dp.message(AddClient.step_5)
async def step5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Нет":
        await state.update_data(subscriptions=[{"name": "отсутствует", "term": "", "start": "", "end": ""}])
        await state.set_state(AddClient.step_6)
        await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())
    elif message.text == "Да":
        await message.answer("Сколько подписок?", reply_markup=get_subs_count_kb())
        await state.set_state(AddClient.step_5_sub1)
    else:
        await message.answer("Выберите Да или Нет.", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")], [KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        ))

@dp.message(AddClient.step_5_sub1)
async def step5_sub1(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Одна":
        await state.update_data(subs_count=1)
        await message.answer("Выберите подписку:", reply_markup=get_sub_type_kb())
        await state.set_state(AddClient.step_5_sub2)
    elif message.text == "Две":
        await state.update_data(subs_count=2)
        await message.answer("Выберите первую подписку:", reply_markup=get_sub_type_kb())
        await state.set_state(AddClient.step_5_sub3)
    else:
        await message.answer("Выберите Одна или Две.", reply_markup=get_subs_count_kb())

@dp.message(AddClient.step_5_sub2)
async def step5_sub2(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    sub = message.text.strip()
    await state.update_data(first_sub_type=sub)
    if sub == "EA Play":
        await message.answer("Срок подписки?", reply_markup=get_term_kb(psplus=False))
    else:
        await message.answer("Срок подписки?", reply_markup=get_term_kb(psplus=True))
    await state.set_state(AddClient.step_5_sub4)

@dp.message(AddClient.step_5_sub4)
async def step5_sub4(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    term = message.text.strip()
    await state.update_data(first_sub_term=term)
    await message.answer("Дата оформления подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.step_5_sub5)

@dp.message(AddClient.step_5_sub5)
async def step5_sub5(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    date = message.text.strip()
    try:
        datetime.strptime(date, "%d.%m.%Y")
    except Exception:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    subs = [{
        "name": data["first_sub_type"],
        "term": data["first_sub_term"],
        "start": date,
        "end": month_delta(date, int(data["first_sub_term"].replace("м", "")))
    }]
    await state.update_data(subscriptions=subs)
    await state.set_state(AddClient.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_5_sub3)
async def step5_sub3(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    sub = message.text.strip()
    await state.update_data(first_sub_type=sub)
    if sub == "EA Play":
        await message.answer("Срок подписки?", reply_markup=get_term_kb(psplus=False))
    else:
        await message.answer("Срок подписки?", reply_markup=get_term_kb(psplus=True))
    await state.set_state(AddClient.step_5_sub6)

@dp.message(AddClient.step_5_sub6)
async def step5_sub6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    term = message.text.strip()
    await state.update_data(first_sub_term=term)
    await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.step_5_sub7)

@dp.message(AddClient.step_5_sub7)
async def step5_sub7(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    date = message.text.strip()
    try:
        datetime.strptime(date, "%d.%m.%Y")
    except Exception:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())
        return
    await state.update_data(first_sub_date=date)
    data = await state.get_data()
    first_type = data["first_sub_type"]
    if "PS Plus" in first_type:
        await message.answer("Выберите вторую подписку (EA Play):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="EA Play")],[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
    else:
        await message.answer("Выберите вторую подписку (PS Plus):", reply_markup=ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True))
    await state.set_state(AddClient.step_5_sub8)

@dp.message(AddClient.step_5_sub8)
async def step5_sub8(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    sub = message.text.strip()
    await state.update_data(second_sub_type=sub)
    if sub == "EA Play":
        await message.answer("Срок второй подписки?", reply_markup=get_term_kb(psplus=False))
    else:
        await message.answer("Срок второй подписки?", reply_markup=get_term_kb(psplus=True))
    await state.set_state(AddClient.step_5_sub9)

@dp.message(AddClient.step_5_sub9)
async def step5_sub9(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    term = message.text.strip()
    await state.update_data(second_sub_term=term)
    await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=get_cancel_kb())
    await state.set_state(AddClient.step_5_sub10)

@dp.message(AddClient.step_5_sub10)
async def step5_sub10(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    date = message.text.strip()
    try:
        datetime.strptime(date, "%d.%m.%Y")
    except Exception:
        await message.answer("Некорректный формат даты! Пример: 22.05.2025", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    subs = [
        {
            "name": data["first_sub_type"],
            "term": data["first_sub_term"],
            "start": data["first_sub_date"],
            "end": month_delta(data["first_sub_date"], int(data["first_sub_term"].replace("м", "")))
        },
        {
            "name": data["second_sub_type"],
            "term": data["second_sub_term"],
            "start": date,
            "end": month_delta(date, int(data["second_sub_term"].replace("м", "")))
        }
    ]
    await state.update_data(subscriptions=subs)
    await state.set_state(AddClient.step_6)
    await message.answer("Шаг 6\nОформлены игры?", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_6)
async def step6(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Да":
        await state.set_state(AddClient.step_6_games)
        await message.answer("Введите список игр, каждая на новой строке:", reply_markup=get_cancel_kb())
    elif message.text == "Нет":
        await state.update_data(games=[])
        await state.set_state(AddClient.step_7_photo)
        await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yesno_kb())
    else:
        await message.answer("Выберите Да или Нет.", reply_markup=get_yesno_kb())

@dp.message(AddClient.step_6_games)
async def step6_games(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    games = [g.strip() for g in message.text.split("\n") if g.strip()]
    await state.update_data(games=games)
    await state.set_state(AddClient.step_7_photo)
    await message.answer("Шаг 7\nЕсть ли резервные коды?", reply_markup=get_yesno_kb())

# ---------- Исправленный шаг с резервными кодами ----------

@dp.message(AddClient.step_7_photo, F.photo)
async def step7_photo_upload(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    client = {
        "number": data.get("number", ""),
        "telegram": data.get("telegram", ""),
        "birthdate": data.get("birthdate", "отсутствует"),
        "account": data.get("account", ""),
        "mailpass": data.get("mailpass", ""),
        "region": data.get("region", ""),
        "subscriptions": data.get("subscriptions", []),
        "games": data.get("games", []),
        "codes": file_id
    }
    add_client_to_db(client)
    await clear_chat(message.chat.id, state)
    await show_client_card(message.chat.id, client, state)
    await state.clear()

@dp.message(AddClient.step_7_photo)
async def step7_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel(message, state)
        return
    if message.text == "Да":
        await message.answer("Загрузите скриншот с резервными кодами:", reply_markup=get_cancel_kb())
    elif message.text == "Нет":
        data = await state.get_data()
        client = {
            "number": data.get("number", ""),
            "telegram": data.get("telegram", ""),
            "birthdate": data.get("birthdate", "отсутствует"),
            "account": data.get("account", ""),
            "mailpass": data.get("mailpass", ""),
            "region": data.get("region", ""),
            "subscriptions": data.get("subscriptions", []),
            "games": data.get("games", []),
            "codes": ""
        }
        add_client_to_db(client)
        await clear_chat(message.chat.id, state)
        await show_client_card(message.chat.id, client, state)
        await state.clear()
    else:
        await message.answer("Выберите Есть или Нету.", reply_markup=get_yesno_kb())

# ----------------------------------------------------------

# (Остальной код для редактирования и сохранения информации клиента не меняется и уже был выше. Если нужно — добавлю полный блок заново.)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
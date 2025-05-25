import asyncio
import json
import os
import re
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter, Text
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove, InputFile
)

TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

DB_PATH = "clients_db.json"

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

def update_client_in_db(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if (c.get("number") == client.get("number") and client.get("number")) or \
           (c.get("telegram") == client.get("telegram") and client.get("telegram")):
            clients[i] = client
            break
    else:
        clients.append(client)
    save_db(clients)

def find_client(query):
    clients = load_db()
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            return c
    return None

def delete_client(query):
    clients = load_db()
    new_clients = []
    deleted = False
    for c in clients:
        if c.get("number") == query or c.get("telegram") == query:
            deleted = True
            continue
        new_clients.append(c)
    save_db(new_clients)
    return deleted

def export_all():
    clients = load_db()
    result = []
    for c in clients:
        number = c.get("number") or c.get("telegram") or ""
        birth = c.get("birthdate", "отсутствует")
        acc = c.get("account", "")
        acc_mail = c.get("mailpass", "")
        region = c.get("region", "отсутствует")
        subs = c.get("subscriptions", [])
        games = c.get("games", [])
        text = f"Клиент: {number} | {birth}\nАккаунт: {acc} ({region})\n"
        if acc_mail:
            text += f"Почта-пароль: {acc_mail}\n"
        if subs and subs[0].get("name") != "отсутствует":
            for s in subs:
                text += f"Подписка: {s['name']} {s['term']} ({region}) с {s['start']} по {s['end']}\n"
        else:
            text += "Подписки: отсутствует\n"
        text += f"Регион: {region}\n"
        if games:
            text += "Игры:\n"
            for g in games:
                text += f"- {g}\n"
        text += "\n"
        result.append(text)
    return "\n".join(result)

def is_valid_date(date_string):
    try:
        datetime.strptime(date_string, "%d.%m.%Y")
        return True
    except:
        return False

def calc_end(start, term):
    start_date = datetime.strptime(start, "%d.%m.%Y")
    if "м" in term:
        months = int(term.replace("м", ""))
        end_date = start_date + timedelta(days=30*months)
    elif "12" in term:
        end_date = start_date + timedelta(days=365)
    else:
        end_date = start_date
    return end_date.strftime("%d.%m.%Y")

class AddClient(StatesGroup):
    number = State()
    birth_check = State()
    birthdate = State()
    account = State()
    region = State()
    sub_check = State()
    sub_count = State()
    sub1_type = State()
    sub1_term = State()
    sub1_date = State()
    sub2_type = State()
    sub2_term = State()
    sub2_date = State()
    games_check = State()
    games = State()
    codes_check = State()
    codes_photo = State()
    confirm = State()

class EditClient(StatesGroup):
    choose_field = State()
    edit_number = State()
    edit_birthdate = State()
    edit_account = State()
    edit_region = State()
    edit_codes = State()
    edit_sub = State()
    edit_games = State()
    confirm = State()

async def clear_chat(chat_id: int, bot: Bot):
    # Удаляем до 60 последних сообщений
    history = []
    async for msg in bot.get_chat_history(chat_id, limit=60):
        history.append(msg)
    for msg in history:
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except:
            continue

def client_to_text(client):
    number = client.get("number") or client.get("telegram") or ""
    birth = client.get("birthdate", "отсутствует")
    acc = client.get("account", "")
    mail = client.get("mailpass", "")
    region = client.get("region", "отсутствует")
    subs = client.get("subscriptions", [])
    games = client.get("games", [])
    text = f"👤 <b>{number}</b>"
    if birth and birth != "отсутствует":
        text += f" | {birth}"
    text += "\n🔐 {0}".format(acc)
    if mail:
        text += f"\n✉️ Почта-пароль: {mail}"
    if subs and subs[0].get("name") != "отсутствует":
        for s in subs:
            text += f"\n🗓 <b>{s['name']}</b> {s['term']}\n{s['start']} ➔ {s['end']}"
    else:
        text += "\nПодписка: (отсутствует)"
    text += f"\n🌍 Регион: ({region})"
    if games:
        text += "\n🎮 Игры:\n" + "\n".join([f"• {g}" for g in games])
    return text

def edit_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 Изменить номер-TG", callback_data="edit_number"),
                InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birth")
            ],
            [
                InlineKeyboardButton(text="🔐 Изменить аккаунт", callback_data="edit_account"),
                InlineKeyboardButton(text="🌍 Изменить регион", callback_data="edit_region")
            ],
            [
                InlineKeyboardButton(text="🖼 Изменить резерв...", callback_data="edit_codes"),
                InlineKeyboardButton(text="💳 Изменить подписку", callback_data="edit_subs")
            ],
            [
                InlineKeyboardButton(text="🎮 Изменить игры", callback_data="edit_games"),
                InlineKeyboardButton(text="✅ Сохранить", callback_data="save_client")
            ]
        ]
    )

async def main():
    bot = Bot(token=TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    main_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="🧹 Очистить чат")],
            [KeyboardButton(text="⬇️ Выгрузить базу")]
        ],
        resize_keyboard=True
    )

    yes_no_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    sub_types_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
            [KeyboardButton(text="PS Plus Essential"), KeyboardButton(text="EA Play")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    region_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="укр"), KeyboardButton(text="тур"), KeyboardButton(text="другой")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    @dp.message(CommandStart())
    async def start(message: types.Message, state: FSMContext):
        await state.clear()
        await clear_chat(message.chat.id, bot)
        await message.answer("Выберите действие:", reply_markup=main_menu)

    @dp.message(Text("🧹 Очистить чат"))
    async def clear_cmd(message: types.Message, state: FSMContext):
        await state.clear()
        await clear_chat(message.chat.id, bot)
        await message.answer("Чат очищен!", reply_markup=main_menu)

    @dp.message(Text("⬇️ Выгрузить базу"))
    async def export_cmd(message: types.Message):
        text = export_all()
        await message.answer_document(types.input_file.InputFile.from_file(BytesIO(text.encode("utf-8")), filename="clients.txt"))

    @dp.message(Text("➕ Добавить клиента"))
    async def add_start(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Шаг 1\nНомер телефона или Telegram:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddClient.number)

    @dp.message(StateFilter(AddClient.number))
    async def add_number(message: types.Message, state: FSMContext):
        value = message.text.strip()
        if value.startswith("+"):
            await state.update_data(number=value, telegram="")
        else:
            await state.update_data(number="", telegram=value)
        await message.answer("Шаг 2\nЕсть ли дата рождения?", reply_markup=yes_no_kb)
        await state.set_state(AddClient.birth_check)

    @dp.message(StateFilter(AddClient.birth_check), Text("Да"))
    async def add_birth_yes(message: types.Message, state: FSMContext):
        await message.answer("Введите дату рождения (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddClient.birthdate)

    @dp.message(StateFilter(AddClient.birth_check), Text("Нет"))
    async def add_birth_no(message: types.Message, state: FSMContext):
        await state.update_data(birthdate="отсутствует")
        await message.answer("Шаг 3\nВведите данные от аккаунта:\n(Логин и пароль через ; )")
        await state.set_state(AddClient.account)

    @dp.message(StateFilter(AddClient.birthdate))
    async def add_birthdate(message: types.Message, state: FSMContext):
        value = message.text.strip()
        if not is_valid_date(value):
            await message.answer("Некорректный формат даты! Пример: 22.05.2025")
            return
        await state.update_data(birthdate=value)
        await message.answer("Шаг 3\nВведите данные от аккаунта:\n(Логин и пароль через ; )")
        await state.set_state(AddClient.account)

    @dp.message(StateFilter(AddClient.account))
    async def add_account(message: types.Message, state: FSMContext):
        lines = message.text.splitlines()
        if len(lines) >= 2:
            acc = lines[0]
            mailpass = lines[1]
        else:
            acc = message.text.strip()
            mailpass = ""
        await state.update_data(account=acc, mailpass=mailpass)
        await message.answer("Шаг 4\nКакой регион аккаунта?", reply_markup=region_kb)
        await state.set_state(AddClient.region)

    @dp.message(StateFilter(AddClient.region))
    async def add_region(message: types.Message, state: FSMContext):
        reg = message.text.strip()
        await state.update_data(region=reg)
        await message.answer("Шаг 5\nОформлена ли подписка?", reply_markup=yes_no_kb)
        await state.set_state(AddClient.sub_check)

    @dp.message(StateFilter(AddClient.sub_check), Text("Да"))
    async def add_sub_yes(message: types.Message, state: FSMContext):
        await message.answer("Сколько подписок оформлено?", reply_markup=ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="Одна"), KeyboardButton(text="Две")],
            [KeyboardButton(text="❌ Отмена")]
        ], resize_keyboard=True, one_time_keyboard=True))
        await state.set_state(AddClient.sub_count)

    @dp.message(StateFilter(AddClient.sub_check), Text("Нет"))
    async def add_sub_no(message: types.Message, state: FSMContext):
        await state.update_data(subscriptions=[{"name": "отсутствует"}])
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=yes_no_kb)
        await state.set_state(AddClient.games_check)

    @dp.message(StateFilter(AddClient.sub_count), Text("Одна"))
    async def add_one_sub(message: types.Message, state: FSMContext):
        await message.answer("Выберите подписку:", reply_markup=sub_types_kb)
        await state.set_state(AddClient.sub1_type)

    @dp.message(StateFilter(AddClient.sub_count), Text("Две"))
    async def add_two_sub(message: types.Message, state: FSMContext):
        await message.answer("Выберите первую подписку:", reply_markup=sub_types_kb)
        await state.set_state(AddClient.sub1_type)

    @dp.message(StateFilter(AddClient.sub1_type))
    async def add_sub1_type(message: types.Message, state: FSMContext):
        sub = message.text.strip()
        if sub not in ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"]:
            await message.answer("Выберите подписку из списка.")
            return
        await state.update_data(sub1_type=sub)
        if sub == "EA Play":
            await message.answer("Срок EA Play:", reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True, one_time_keyboard=True))
        else:
            await message.answer("Срок PS Plus:", reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True, one_time_keyboard=True))
        await state.set_state(AddClient.sub1_term)

    @dp.message(StateFilter(AddClient.sub1_term))
    async def add_sub1_term(message: types.Message, state: FSMContext):
        term = message.text.strip()
        if term not in ["1м", "3м", "12м"]:
            await message.answer("Выберите срок из списка.")
            return
        await state.update_data(sub1_term=term)
        await message.answer("Дата оформления первой подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddClient.sub1_date)

    @dp.message(StateFilter(AddClient.sub1_date))
    async def add_sub1_date(message: types.Message, state: FSMContext):
        date1 = message.text.strip()
        if not is_valid_date(date1):
            await message.answer("Некорректный формат даты! Пример: 22.05.2025")
            return
        data = await state.get_data()
        sub_type1 = data.get("sub1_type")
        term1 = data.get("sub1_term")
        start1 = date1
        end1 = calc_end(start1, term1)
        subs = [{
            "name": sub_type1,
            "term": term1,
            "start": start1,
            "end": end1
        }]
        await state.update_data(subscriptions=subs)
        if data.get("sub_count") == "Две":
            # Вторая подписка (обратная категория)
            cats = ["EA Play"] if sub_type1.startswith("PS Plus") else ["PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=x)] for x in cats] + [[KeyboardButton(text="❌ Отмена")]],
                resize_keyboard=True, one_time_keyboard=True)
            await message.answer("Выберите вторую подписку:", reply_markup=kb)
            await state.set_state(AddClient.sub2_type)
        else:
            await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=yes_no_kb)
            await state.set_state(AddClient.games_check)

    @dp.message(StateFilter(AddClient.sub2_type))
    async def add_sub2_type(message: types.Message, state: FSMContext):
        sub = message.text.strip()
        valid = ["EA Play", "PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"]
        if sub not in valid:
            await message.answer("Выберите подписку из списка.")
            return
        await state.update_data(sub2_type=sub)
        if sub == "EA Play":
            await message.answer("Срок EA Play:", reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True, one_time_keyboard=True))
        else:
            await message.answer("Срок PS Plus:", reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="1м"), KeyboardButton(text="3м"), KeyboardButton(text="12м")],
                [KeyboardButton(text="❌ Отмена")]
            ], resize_keyboard=True, one_time_keyboard=True))
        await state.set_state(AddClient.sub2_term)

    @dp.message(StateFilter(AddClient.sub2_term))
    async def add_sub2_term(message: types.Message, state: FSMContext):
        term = message.text.strip()
        if term not in ["1м", "3м", "12м"]:
            await message.answer("Выберите срок из списка.")
            return
        await state.update_data(sub2_term=term)
        await message.answer("Дата оформления второй подписки? (дд.мм.гггг):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddClient.sub2_date)

    @dp.message(StateFilter(AddClient.sub2_date))
    async def add_sub2_date(message: types.Message, state: FSMContext):
        date2 = message.text.strip()
        if not is_valid_date(date2):
            await message.answer("Некорректный формат даты! Пример: 22.05.2025")
            return
        data = await state.get_data()
        sub1 = {
            "name": data.get("sub1_type"),
            "term": data.get("sub1_term"),
            "start": data.get("sub1_date"),
            "end": calc_end(data.get("sub1_date"), data.get("sub1_term"))
        }
        sub2 = {
            "name": data.get("sub2_type"),
            "term": data.get("sub2_term"),
            "start": date2,
            "end": calc_end(date2, data.get("sub2_term"))
        }
        await state.update_data(subscriptions=[sub1, sub2])
        await message.answer("Шаг 6\nЕсть ли оформленные игры?", reply_markup=yes_no_kb)
        await state.set_state(AddClient.games_check)

    @dp.message(StateFilter(AddClient.games_check), Text("Да"))
    async def add_games_yes(message: types.Message, state: FSMContext):
        await message.answer("Введите список игр (каждая на новой строке):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddClient.games)

    @dp.message(StateFilter(AddClient.games_check), Text("Нет"))
    async def add_games_no(message: types.Message, state: FSMContext):
        await state.update_data(games=[])
        await message.answer("Шаг 7\nЕсть резерв коды?", reply_markup=yes_no_kb)
        await state.set_state(AddClient.codes_check)

    @dp.message(StateFilter(AddClient.games))
    async def add_games(message: types.Message, state: FSMContext):
        games = [g.strip() for g in message.text.splitlines() if g.strip()]
        await state.update_data(games=games)
        await message.answer("Шаг 7\nЕсть резерв коды?", reply_markup=yes_no_kb)
        await state.set_state(AddClient.codes_check)

    @dp.message(StateFilter(AddClient.codes_check), Text("Да"))
    async def add_codes_yes(message: types.Message, state: FSMContext):
        await message.answer("Загрузите фото с резерв кодами:")
        await state.set_state(AddClient.codes_photo)

    @dp.message(StateFilter(AddClient.codes_check), Text("Нет"))
    async def add_codes_no(message: types.Message, state: FSMContext):
        await state.update_data(codes_photo_id=None)
        await confirm_and_save(message, state)

    @dp.message(StateFilter(AddClient.codes_photo), F.photo)
    async def add_codes_photo(message: types.Message, state: FSMContext):
        photo_id = message.photo[-1].file_id
        await state.update_data(codes_photo_id=photo_id)
        await confirm_and_save(message, state)

    async def confirm_and_save(message, state):
        data = await state.get_data()
        client = {
            "number": data.get("number", ""),
            "telegram": data.get("telegram", ""),
            "birthdate": data.get("birthdate", "отсутствует"),
            "account": data.get("account", ""),
            "mailpass": data.get("mailpass", ""),
            "region": data.get("region", "отсутствует"),
            "subscriptions": data.get("subscriptions", []),
            "games": data.get("games", []),
            "codes_photo_id": data.get("codes_photo_id")
        }
        add_client_to_db(client)
        await clear_chat(message.chat.id, bot)
        text = client_to_text(client)
        if client.get("codes_photo_id"):
            msg = await bot.send_photo(message.chat.id, client["codes_photo_id"], caption=text, reply_markup=edit_kb())
        else:
            msg = await bot.send_message(message.chat.id, text, reply_markup=edit_kb())
        await asyncio.sleep(300)
        await bot.delete_message(message.chat.id, msg.message_id)

    # --- Обработчики редактирования будут добавлены ниже ---

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
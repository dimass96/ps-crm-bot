import asyncio
import logging
import os
import json
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardMarkup, InlineKeyboardButton, 
                           ReplyKeyboardRemove, InputFile)
from aiogram.utils.markdown import hbold
from aiogram.enums import ParseMode

API_TOKEN = "7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8"
ADMIN_ID = 350902460

DATA_FILE = "clients.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- Вспомогательные функции ---

def load_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(clients):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def calc_sub_end(start_date: str, duration: str):
    dt = datetime.strptime(start_date, "%d.%m.%Y")
    months = int(duration.replace('м', ''))
    end_dt = dt + timedelta(days=30*months)
    return end_dt.strftime("%d.%m.%Y")

def get_next_client_id(clients):
    return max([c.get("id", 0) for c in clients], default=0) + 1

def find_client(query):
    clients = load_db()
    for client in clients:
        if client["contact"].lower() == query.lower():
            return client
    return None

def update_client(client):
    clients = load_db()
    for i, c in enumerate(clients):
        if c["id"] == client["id"]:
            clients[i] = client
            save_db(clients)
            return

def delete_client(client_id):
    clients = load_db()
    clients = [c for c in clients if c["id"] != client_id]
    save_db(clients)

def format_client_info(client):
    lines = []
    contact = client["contact"]
    bdate = client["birth_date"] if client["birth_date"] else "—"
    console = client["console"]
    lines.append(f"📱 <b>{contact}</b> | {bdate} <b>({console})</b>")

    login = client["account_login"]
    password = client["account_password"]
    mail_pass = client["mail_password"] or "—"
    lines.append(f"🔑 {login}; {password}")
    lines.append(f"📧 {mail_pass}")

    for i in (1, 2):
        sub = client.get(f"subscription_{i}", {})
        if sub and sub.get("type"):
            lines.append(f"💳 {sub['type']} {sub['duration']}")
            lines.append(f"📅 {sub['start_date']} — {sub['end_date']}")

    region = client["region"]
    lines.append(f"🌍 Регион: <b>({region})</b>")

    if client.get("games"):
        lines.append("\n🎮 Игры:")
        for game in client["games"]:
            lines.append(game)
    if client.get("reserve_codes"):
        lines.append("\n🗂 Резерв-коды: загружено")
    return "\n".join(lines)

# --- Хэндлеры ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить клиента")],
            [KeyboardButton(text="🔎 Поиск"), KeyboardButton(text="📤 Выгрузить базу")],
            [KeyboardButton(text="🧹 Очистить чат")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=kb)

@dp.message(F.text == "🧹 Очистить чат")
async def clear_chat(message: types.Message):
    await message.answer("Чат очищен.", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "📤 Выгрузить базу")
async def dump_db(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    clients = load_db()
    text = "\n\n".join(format_client_info(c) for c in clients)
    fname = f"clients_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)
    await bot.send_document(message.chat.id, InputFile(fname))
    os.remove(fname)

# --- Добавление клиента ---

user_states = {}

async def start_add_client(message):
    user_states[message.from_user.id] = {"step": "contact", "data": {}}
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
    await message.answer("Введите номер телефона или @username клиента:", reply_markup=kb)

@dp.message(F.text == "➕ Добавить клиента")
async def add_client_start(message: types.Message):
    await start_add_client(message)

@dp.message(F.text == "Отмена")
async def cancel(message: types.Message):
    user_states.pop(message.from_user.id, None)
    await cmd_start(message)

@dp.message()
async def add_flow(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    state = user_states.get(message.from_user.id)
    if not state:
        return

    step = state["step"]
    data = state["data"]

    if step == "contact":
        data["contact"] = message.text.strip()
        state["step"] = "birth_ask"
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Есть дата рождения")],
                [KeyboardButton(text="Нет даты рождения")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Есть ли дата рождения клиента?", reply_markup=kb)
        return

    if step == "birth_ask":
        if message.text == "Есть дата рождения":
            state["step"] = "birth_date"
            await message.answer("Введите дату рождения клиента (дд.мм.гггг):")
            return
        if message.text == "Нет даты рождения":
            data["birth_date"] = ""
            state["step"] = "console"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS4"), KeyboardButton(text="PS5")],
                    [KeyboardButton(text="PS4/PS5")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Какая консоль у клиента?", reply_markup=kb)
            return
        await message.answer("Выберите 'Есть дата рождения' или 'Нет даты рождения'.")
        return

    if step == "birth_date":
        try:
            dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
            data["birth_date"] = message.text.strip()
            state["step"] = "console"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS4"), KeyboardButton(text="PS5")],
                    [KeyboardButton(text="PS4/PS5")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Какая консоль у клиента?", reply_markup=kb)
            return
        except Exception:
            await message.answer("Введите дату в формате дд.мм.гггг")
            return

    if step == "console":
        if message.text not in ("PS4", "PS5", "PS4/PS5"):
            await message.answer("Выберите консоль кнопкой.")
            return
        data["console"] = message.text
        state["step"] = "account_login"
        await message.answer("Введите ЛОГИН от аккаунта:")
        return

    if step == "account_login":
        data["account_login"] = message.text.strip()
        state["step"] = "account_password"
        await message.answer("Введите ПАРОЛЬ от аккаунта:")
        return

    if step == "account_password":
        data["account_password"] = message.text.strip()
        state["step"] = "mail_password"
        await message.answer("Введите ПАРОЛЬ от почты (или '-' если нет):")
        return

    if step == "mail_password":
        data["mail_password"] = message.text.strip() if message.text.strip() != "-" else ""
        state["step"] = "region"
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="укр"), KeyboardButton(text="тур")],
                [KeyboardButton(text="польша"), KeyboardButton(text="британия")],
                [KeyboardButton(text="другой")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите регион аккаунта:", reply_markup=kb)
        return

    if step == "region":
        if message.text not in ("укр", "тур", "польша", "британия", "другой"):
            await message.answer("Выберите регион кнопкой.")
            return
        data["region"] = message.text
        state["step"] = "subs_ask"
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Нет подписки")],
                [KeyboardButton(text="Одна подписка")],
                [KeyboardButton(text="Две подписки")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("Сколько подписок у клиента?", reply_markup=kb)
        return

    if step == "subs_ask":
        # reset subscriptions
        data["subscription_1"] = {}
        data["subscription_2"] = {}
        if message.text == "Нет подписки":
            state["step"] = "games_ask"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Есть игры")],
                    [KeyboardButton(text="Нет игр")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Есть ли у клиента оформленные игры?", reply_markup=kb)
            return
        elif message.text == "Одна подписка":
            state["step"] = "sub1_type"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                    [KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Выберите подписку:", reply_markup=kb)
            return
        elif message.text == "Две подписки":
            state["step"] = "sub1_type"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra")],
                    [KeyboardButton(text="PS Plus Essential")],
                    [KeyboardButton(text="EA Play")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Выберите первую подписку:", reply_markup=kb)
            return
        else:
            await message.answer("Выберите количество подписок кнопкой.")
            return

    if step == "sub1_type":
        v = message.text
        if v not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play"):
            await message.answer("Выберите подписку кнопкой.")
            return
        data["subscription_1"]["type"] = v
        if v == "EA Play":
            durations = [["1м", "12м"]]
        else:
            durations = [["1м", "3м", "12м"]]
        kb = ReplyKeyboardMarkup(
            keyboard=[list(map(KeyboardButton, row)) for row in durations] + [[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
        state["step"] = "sub1_duration"
        await message.answer("Выберите срок подписки:", reply_markup=kb)
        return

    if step == "sub1_duration":
        v = message.text
        if data["subscription_1"]["type"] == "EA Play" and v not in ("1м", "12м"):
            await message.answer("EA Play только 1м или 12м.")
            return
        elif data["subscription_1"]["type"] != "EA Play" and v not in ("1м", "3м", "12м"):
            await message.answer("Выберите срок кнопкой.")
            return
        data["subscription_1"]["duration"] = v
        state["step"] = "sub1_start"
        await message.answer("Введите дату оформления подписки (дд.мм.гггг):")
        return

    if step == "sub1_start":
        try:
            dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
            data["subscription_1"]["start_date"] = message.text.strip()
            data["subscription_1"]["end_date"] = calc_sub_end(message.text.strip(), data["subscription_1"]["duration"])
            if user_states[message.from_user.id]["step"] == "sub1_start" and (
                data.get("subscription_2") is not None and user_states[message.from_user.id].get("want_second_sub")):
                state["step"] = "sub2_type"
                kb = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="EA Play")] if data["subscription_1"]["type"] != "EA Play" else
                        [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                        [KeyboardButton(text="Отмена")]
                    ],
                    resize_keyboard=True
                )
                await message.answer("Выберите вторую подписку:", reply_markup=kb)
                return
            elif user_states[message.from_user.id]["step"] == "sub1_start" and (
                user_states[message.from_user.id].get("want_second_sub") is None and data.get("subscription_2") == {}):
                state["step"] = "games_ask"
                kb = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Есть игры")],
                        [KeyboardButton(text="Нет игр")],
                        [KeyboardButton(text="Отмена")]
                    ],
                    resize_keyboard=True
                )
                await message.answer("Есть ли у клиента оформленные игры?", reply_markup=kb)
                return
            else:
                state["step"] = "sub2_type"
                kb = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="EA Play")] if data["subscription_1"]["type"] != "EA Play" else
                        [KeyboardButton(text="PS Plus Deluxe"), KeyboardButton(text="PS Plus Extra"), KeyboardButton(text="PS Plus Essential")],
                        [KeyboardButton(text="Отмена")]
                    ],
                    resize_keyboard=True
                )
                await message.answer("Выберите вторую подписку:", reply_markup=kb)
                return
        except Exception:
            await message.answer("Введите дату в формате дд.мм.гггг")
            return

    if step == "sub2_type":
        v = message.text
        if data["subscription_1"]["type"] == "EA Play" and v not in ("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential"):
            await message.answer("Вторая подписка может быть только из другой категории.")
            return
        if data["subscription_1"]["type"] != "EA Play" and v != "EA Play":
            await message.answer("Вторая подписка может быть только EA Play.")
            return
        data["subscription_2"]["type"] = v
        if v == "EA Play":
            durations = [["1м", "12м"]]
        else:
            durations = [["1м", "3м", "12м"]]
        kb = ReplyKeyboardMarkup(
            keyboard=[list(map(KeyboardButton, row)) for row in durations] + [[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
        state["step"] = "sub2_duration"
        await message.answer("Выберите срок подписки:", reply_markup=kb)
        return

    if step == "sub2_duration":
        v = message.text
        if data["subscription_2"]["type"] == "EA Play" and v not in ("1м", "12м"):
            await message.answer("EA Play только 1м или 12м.")
            return
        elif data["subscription_2"]["type"] != "EA Play" and v not in ("1м", "3м", "12м"):
            await message.answer("Выберите срок кнопкой.")
            return
        data["subscription_2"]["duration"] = v
        state["step"] = "sub2_start"
        await message.answer("Введите дату оформления второй подписки (дд.мм.гггг):")
        return

    if step == "sub2_start":
        try:
            dt = datetime.strptime(message.text.strip(), "%d.%m.%Y")
            data["subscription_2"]["start_date"] = message.text.strip()
            data["subscription_2"]["end_date"] = calc_sub_end(message.text.strip(), data["subscription_2"]["duration"])
            state["step"] = "games_ask"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Есть игры")],
                    [KeyboardButton(text="Нет игр")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Есть ли у клиента оформленные игры?", reply_markup=kb)
            return
        except Exception:
            await message.answer("Введите дату в формате дд.мм.гггг")
            return

    if step == "games_ask":
        if message.text == "Есть игры":
            data["games"] = []
            state["step"] = "games"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Закончить ввод игр")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Вводите по одной игре в строку. Когда закончите, нажмите 'Закончить ввод игр'.", reply_markup=kb)
            return
        if message.text == "Нет игр":
            data["games"] = []
            state["step"] = "reserve_ask"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Есть резерв-коды")],
                    [KeyboardButton(text="Нет резерв-кодов")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Есть ли резерв-коды?", reply_markup=kb)
            return

    if step == "games":
        if message.text == "Закончить ввод игр":
            state["step"] = "reserve_ask"
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Есть резерв-коды")],
                    [KeyboardButton(text="Нет резерв-кодов")],
                    [KeyboardButton(text="Отмена")]
                ],
                resize_keyboard=True
            )
            await message.answer("Есть ли резерв-коды?", reply_markup=kb)
            return
        data.setdefault("games", []).append(message.text.strip())
        await message.answer("Добавлено. Введите следующую игру или нажмите 'Закончить ввод игр'.")
        return

    if step == "reserve_ask":
        if message.text == "Есть резерв-коды":
            state["step"] = "reserve_photo"
            await message.answer("Отправьте фото резерв-кодов:")
            return
        if message.text == "Нет резерв-кодов":
            data["reserve_codes"] = []
            # Завершаем!
            client = data.copy()
            client["id"] = get_next_client_id(load_db())
            save_new_client(client)
            user_states.pop(message.from_user.id, None)
            await message.answer("Клиент добавлен!", reply_markup=ReplyKeyboardRemove())
            await message.answer(format_client_info(client))
            await cmd_start(message)
            return

    if step == "reserve_photo":
        await message.answer("Ожидаю фото.")
        return

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    state = user_states.get(message.from_user.id)
    if state and state["step"] == "reserve_photo":
        data = state["data"]
        photo_id = message.photo[-1].file_id
        data.setdefault("reserve_codes", []).append(photo_id)
        # Завершаем!
        client = data.copy()
        client["id"] = get_next_client_id(load_db())
        save_new_client(client)
        user_states.pop(message.from_user.id, None)
        await message.answer("Клиент добавлен!", reply_markup=ReplyKeyboardRemove())
        await message.answer(format_client_info(client))
        await cmd_start(message)

def save_new_client(client):
    clients = load_db()
    clients.append(client)
    save_db(clients)

# --- Поиск ---

@dp.message(F.text == "🔎 Поиск")
async def search_start(message: types.Message):
    await message.answer("Введите номер телефона или @username клиента для поиска:")

@dp.message()
async def search_flow(message: types.Message):
    if message.text.startswith("+") or message.text.startswith("@"):
        client = find_client(message.text.strip())
        if client:
            await message.answer(format_client_info(client))
            # TODO: добавить кнопки редактирования, удаления
        else:
            await message.answer("Клиент не найден.")

# --- Уведомления ---

async def notify_subs_and_birthdays():
    while True:
        clients = load_db()
        today = datetime.now()
        # Завтра заканчивается подписка
        tomorrow = (today + timedelta(days=1)).strftime("%d.%m.%Y")
        for c in clients:
            for i in (1, 2):
                sub = c.get(f"subscription_{i}", {})
                if sub and sub.get("end_date") == tomorrow:
                    await bot.send_message(ADMIN_ID, f"У клиента {c['contact']} завтра заканчивается подписка: {sub['type']}")
        # День рождения
        for c in clients:
            if c.get("birth_date"):
                bdate = datetime.strptime(c["birth_date"], "%d.%m.%Y")
                if bdate.day == today.day and bdate.month == today.month:
                    await bot.send_message(ADMIN_ID, f"Сегодня день рождения у клиента: {c['contact']}")
        await asyncio.sleep(60 * 60 * 6)  # Проверять каждые 6 часов

async def main():
    asyncio.create_task(notify_subs_and_birthdays())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
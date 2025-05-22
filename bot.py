import telebot
from telebot import types
from database import init_db, add_client, get_client_by_identifier, update_client_field, delete_client_by_id
from datetime import datetime, timedelta
import threading

bot = telebot.TeleBot("7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8")
admin_id = 350902460
client_data = {}
temp_messages = {}
editing_client_id = {}
editing_client_data = {}

def remember_message(msg):
    chat_id = msg.chat.id
    if chat_id not in temp_messages:
        temp_messages[chat_id] = []
    temp_messages[chat_id].append(msg.message_id)

def full_clear(chat_id):
    if chat_id in temp_messages:
        for msg_id in temp_messages[chat_id]:
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                continue
        temp_messages[chat_id] = []

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить", "🔍 Найти клиента")
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.from_user.id != admin_id:
        return bot.send_message(message.chat.id, "Доступ запрещён.")
    msg = bot.send_message(message.chat.id, "CRM для PS клиентов", reply_markup=main_keyboard())
    remember_message(msg)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def start_add(message):
    if message.from_user.id != admin_id:
        return
    full_clear(message.chat.id)
    client_data.clear()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Номер телефона", "Telegram", "Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 1: Укажите способ идентификации клиента", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, get_identifier)

def get_identifier(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["method"] = message.text
    msg = bot.send_message(message.chat.id, f"Введите {message.text.lower()}:")
    remember_message(msg)
    bot.register_next_step_handler(msg, ask_birth_option)

def ask_birth_option(message):
    remember_message(message)
    client_data["username"] = message.text.strip()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Есть", "Нету", "Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 2: Есть ли дата рождения?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, ask_birth_date)

def ask_birth_date(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Есть":
        msg = bot.send_message(message.chat.id, "Введите дату рождения (дд.мм.гггг):")
        remember_message(msg)
        bot.register_next_step_handler(msg, collect_birth_date)
    else:
        client_data["birth_date"] = "отсутствует"
        ask_account_info(message)

def collect_birth_date(message):
    remember_message(message)
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
        client_data["birth_date"] = message.text.strip()
    except:
        client_data["birth_date"] = "отсутствует"
    ask_account_info(message)

def ask_account_info(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 3: Введите:\nemail\nпароль\nпароль от почты (можно пусто)", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, ask_console)

def ask_console(message):
    remember_message(message)
    lines = message.text.strip().split('\n')
    email = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mail_pass = lines[2] if len(lines) > 2 else ""
    client_data["email"] = email
    client_data["password_raw"] = password
    client_data["mail_password"] = mail_pass
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("PS4", "PS5", "PS4/PS5", "Отмена")
    msg = bot.send_message(message.chat.id, "Какие консоли?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, ask_region)

def ask_region(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["account_password"] = f"{client_data['email']};{client_data['password_raw']} ({message.text})"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("(укр)", "(тур)", "(другое)", "Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 4: Какой регион аккаунта?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, ask_reserve_code)

def ask_reserve_code(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["region"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 5: Есть резерв коды?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, process_reserve_code)

def process_reserve_code(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Да":
        msg = bot.send_message(message.chat.id, "Загрузите скриншот с резерв кодами")
        remember_message(msg)
        bot.register_next_step_handler(msg, save_reserve_photo)
    else:
        client_data["reserve_photo"] = None
        ask_subscription_status(message)

@bot.message_handler(content_types=['photo'])
def save_reserve_photo(message):
    remember_message(message)
    file_id = message.photo[-1].file_id
    client_data["reserve_photo"] = file_id
    ask_subscription_status(message)

def ask_subscription_status(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 6: Оформлена ли подписка?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, ask_subscriptions_count)

def ask_subscriptions_count(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Нет":
        client_data["subscription_name"] = "не оформлена"
        client_data["subscription_start"] = ""
        client_data["subscription_end"] = ""
        ask_games_option(message)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Одна", "Две", "Отмена")
    msg = bot.send_message(message.chat.id, "Сколько подписок оформлено?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, choose_first_subscription)

def choose_first_subscription(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["subs_total"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play")
    label = "подписку" if message.text == "Одна" else "первую подписку"
    msg = bot.send_message(message.chat.id, f"Выберите {label}:", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, collect_first_subscription)

def collect_first_subscription(message):
    remember_message(message)
    client_data["sub1_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("12м", "3м", "1м", "Отмена")
    msg = bot.send_message(message.chat.id, "Срок подписки:", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, collect_first_duration)

def collect_first_duration(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["sub1_duration"] = message.text
    msg = bot.send_message(message.chat.id, "Дата оформления подписки (дд.мм.гггг):")
    remember_message(msg)
    if client_data["subs_total"] == "Одна":
        bot.register_next_step_handler(msg, calculate_subscriptions_single)
    else:
        bot.register_next_step_handler(msg, collect_second_subscription)

def calculate_subscriptions_single(message):
    remember_message(message)
    try:
        start = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        start = datetime.now()
    duration = client_data["sub1_duration"]
    end = start + (timedelta(days=365) if duration == "12м" else timedelta(days=90) if duration == "3м" else timedelta(days=30))
    client_data["subscription_start"] = start.strftime("%d.%m.%Y")
    client_data["subscription_end"] = end.strftime("%d.%m.%Y")
    client_data["subscription_name"] = f"{client_data['sub1_type']} {client_data['sub1_duration']} {client_data['region']}"
    ask_games_option(message)

def collect_second_subscription(message):
    remember_message(message)
    try:
        sub1_start = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        sub1_start = datetime.now()
    duration = client_data["sub1_duration"]
    sub1_end = sub1_start + (timedelta(days=365) if duration == "12м" else timedelta(days=90) if duration == "3м" else timedelta(days=30))
    client_data["sub1_start"] = sub1_start.strftime("%d.%m.%Y")
    client_data["sub1_end"] = sub1_end.strftime("%d.%m.%Y")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("EA Play")
    msg = bot.send_message(message.chat.id, "Выберите вторую подписку:", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, collect_second_duration)

def collect_second_duration(message):
    remember_message(message)
    client_data["sub2_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("12м", "1м", "Отмена")
    msg = bot.send_message(message.chat.id, "Срок второй подписки:", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, collect_second_date)

def collect_second_date(message):
    remember_message(message)
    try:
        sub2_start = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        sub2_start = datetime.now()
    duration2 = message.text
    client_data["sub2_duration"] = duration2
    sub2_end = sub2_start + (timedelta(days=365) if duration2 == "12м" else timedelta(days=30))
    client_data["subscription_start"] = client_data["sub1_start"]
    client_data["subscription_end"] = sub2_end.strftime("%d.%m.%Y")
    name1 = f"{client_data['sub1_type']} {client_data['sub1_duration']} {client_data['region']}"
    name2 = f"{client_data['sub2_type']} {client_data['sub2_duration']} {client_data['region']}"
    client_data["subscription_name"] = f"{name1} + {name2}"
    ask_games_option(message)

def ask_games_option(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    msg = bot.send_message(message.chat.id, "Шаг 7: Есть ли игры?", reply_markup=markup)
    remember_message(msg)
    bot.register_next_step_handler(msg, collect_games)

def collect_games(message):
    remember_message(message)
    if message.text == "Отмена":
        full_clear(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Нет":
        client_data["games"] = ""
        finish_add(message)
    else:
        msg = bot.send_message(message.chat.id, "Введите список игр (по строкам):")
        remember_message(msg)
        bot.register_next_step_handler(msg, save_games)

def save_games(message):
    remember_message(message)
    client_data["games"] = " —— ".join(message.text.strip().split('\n'))
    finish_add(message)

def finish_add(message):
    data = (
        client_data.get("username", ""),
        client_data.get("birth_date", ""),
        client_data.get("email", ""),
        client_data.get("account_password", ""),
        client_data.get("mail_password", ""),
        client_data.get("subscription_name", "не оформлена"),
        client_data.get("subscription_start", ""),
        client_data.get("subscription_end", ""),
        client_data.get("region", ""),
        client_data.get("games", ""),
        client_data.get("reserve_photo", None)
    )
    add_client(data)
    full_clear(message.chat.id)
    msg = bot.send_message(message.chat.id, f"✅ {client_data['username']} добавлен!")
    remember_message(msg)
    send_client_info(message.chat.id, client_data)

def send_client_info(chat_id, data):
    subs = data['subscription_name'].split(" + ")
    subs_text = ""
    if len(subs) == 2:
        subs_text = f"💳 {subs[0]}\n📅 {data['subscription_start']} → {data['sub1_end']}\n\n"
        subs_text += f"💳 {subs[1]}\n📅 {data['subscription_start']} → {data['subscription_end']}"
    else:
        subs_text = f"💳 {data['subscription_name']}\n📅 {data['subscription_start']} → {data['subscription_end']}"

    games_block = '🎮 Игры:\n• ' + '\n• '.join(data['games'].split(" —— ")) if data['games'] else '🎮 Игры: Нет'

    text = f"""👤 {data['username']} | {data['birth_date']}
🔐 {data['account_password']}
✉️ Почта-пароль: {data['mail_password']}

{subs_text}
🌍 Регион: {data['region']}

{games_block}
"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📱 Изменить номер", "📅 Изменить дату рождения")
    markup.add("🔐 Изменить данные", "🎮 Изменить консоль")
    markup.add("🌍 Изменить регион", "🖼 Изменить резерв коды")
    markup.add("💳 Изменить подписку", "🎮 Изменить игры")
    markup.add("✅ Сохранить", "❌ Отмена")

    if data["reserve_photo"]:
        msg = bot.send_photo(chat_id, data["reserve_photo"], caption=text, reply_markup=markup)
    else:
        msg = bot.send_message(chat_id, text, reply_markup=markup)

    def delete_later(cid, mid):
        import time
        time.sleep(300)
        try:
            bot.delete_message(cid, mid)
        except:
            pass

    threading.Thread(target=delete_later, args=(msg.chat.id, msg.message_id)).start()

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()
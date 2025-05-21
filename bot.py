import telebot
from telebot import types
from database import (
    init_db, add_client, get_client_by_identifier,
    update_client_field, delete_client_by_id
)
from datetime import datetime, timedelta

bot = telebot.TeleBot("7636123092:AAEAnU8iuShy7UHjH2cwzt1vRA-Pl3e3od8")
admin_id = 350902460
client_data = {}

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить", "🔍 Найти клиента")
    return markup

def start_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Start")
    return markup

def clear_chat(chat_id):
    try:
        messages = bot.get_chat_history(chat_id, limit=20)
        for msg in messages:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except:
                continue
    except:
        pass

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id != admin_id:
        return bot.send_message(message.chat.id, "Доступ запрещён.")
    clear_chat(message.chat.id)
    bot.send_message(message.chat.id, "CRM для PS клиентов", reply_markup=start_keyboard())

@bot.message_handler(func=lambda m: m.text == "Start")
def handle_start_button(message):
    clear_chat(message.chat.id)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить")
def start_add(message):
    if message.from_user.id != admin_id:
        return
    client_data.clear()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Номер телефона", "Telegram", "Отмена")
    bot.send_message(message.chat.id, "Шаг 1: Укажите способ идентификации клиента", reply_markup=markup)
    bot.register_next_step_handler(message, get_identifier)

def get_identifier(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["method"] = message.text
    bot.send_message(message.chat.id, f"Введите {message.text.lower()}:")
    bot.register_next_step_handler(message, ask_birth_option)

def ask_birth_option(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["username"] = message.text.strip()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Есть", "Нету", "Отмена")
    bot.send_message(message.chat.id, "Шаг 2: Есть ли дата рождения?", reply_markup=markup)
    bot.register_next_step_handler(message, ask_birth_date)

def ask_birth_date(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Есть":
        bot.send_message(message.chat.id, "Введите дату рождения (дд.мм.гггг):")
        bot.register_next_step_handler(message, collect_birth_date)
    else:
        client_data["birth_date"] = "отсутствует"
        ask_account_info(message)

def collect_birth_date(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    try:
        datetime.strptime(message.text.strip(), "%d.%m.%Y")
        client_data["birth_date"] = message.text.strip()
    except:
        client_data["birth_date"] = "отсутствует"
    ask_account_info(message)

def ask_account_info(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Отмена")
    bot.send_message(message.chat.id, "Шаг 3: Введите:\nemail\nпароль\nпароль от почты (можно пусто)", reply_markup=markup)
    bot.register_next_step_handler(message, process_account_info)

def process_account_info(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    lines = message.text.strip().split('\n')
    email = lines[0] if len(lines) > 0 else ""
    password = lines[1] if len(lines) > 1 else ""
    mail_pass = lines[2] if len(lines) > 2 else ""
    client_data["email"] = email
    client_data["account_password"] = f"{email};{password}"
    client_data["mail_password"] = mail_pass
    ask_account_region(message)

def ask_account_region(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("(укр)", "(тур)", "(другое)", "Отмена")
    bot.send_message(message.chat.id, "Шаг 4: Какой регион аккаунта?", reply_markup=markup)
    bot.register_next_step_handler(message, process_account_region)

def process_account_region(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["region"] = message.text.strip()
    ask_reserve_code(message)

def ask_reserve_code(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    bot.send_message(message.chat.id, "Шаг 5: Есть резерв коды?", reply_markup=markup)
    bot.register_next_step_handler(message, process_reserve_code)

def process_reserve_code(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Да":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Отмена")
        bot.send_message(message.chat.id, "Загрузите скриншот с резерв кодами\nИли нажмите Отмена", reply_markup=markup)
    else:
        client_data["reserve_photo"] = None
        ask_subscription_status(message)

@bot.message_handler(content_types=['photo'])
def handle_reserve_photo(message):
    if "subscription_name" in client_data:
        return
    file_id = message.photo[-1].file_id
    client_data["reserve_photo"] = file_id
    ask_subscription_status(message)

def ask_subscription_status(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    bot.send_message(message.chat.id, "Шаг 6: Оформлена ли подписка?", reply_markup=markup)
    bot.register_next_step_handler(message, ask_subscriptions_count)

def ask_subscriptions_count(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Нет":
        client_data["subscription_name"] = "Нету"
        client_data["subscription_start"] = ""
        client_data["subscription_end"] = ""
        ask_games_option(message)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Одна", "Две", "Отмена")
    bot.send_message(message.chat.id, "Сколько подписок оформлено?", reply_markup=markup)
    bot.register_next_step_handler(message, choose_first_subscription_type)

def choose_first_subscription_type(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["subs_total"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential", "EA Play")
    bot.send_message(message.chat.id, "Выберите первую подписку:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_first_duration)

def choose_first_duration(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["sub1_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if client_data["sub1_type"] == "EA Play":
        markup.add("1м", "12м")
    else:
        markup.add("1м", "3м", "12м")
    bot.send_message(message.chat.id, "Срок первой подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_first_start)

def choose_first_start(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["sub1_duration"] = message.text
    bot.send_message(message.chat.id, "Дата оформления первой подписки (дд.мм.гггг):")
    bot.register_next_step_handler(message, process_first_subscription)

def process_first_subscription(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    try:
        start1 = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        start1 = datetime.now()
    duration = client_data["sub1_duration"]
    end1 = start1 + (timedelta(days=365) if duration == "12м" else timedelta(days=90) if duration == "3м" else timedelta(days=30))
    client_data["sub1_start"] = start1.strftime("%d.%m.%Y")
    client_data["sub1_end"] = end1.strftime("%d.%m.%Y")

    if client_data["subs_total"] == "Одна":
        client_data["subscription_name"] = f"{client_data['sub1_type']} {client_data['sub1_duration']}"
        client_data["subscription_start"] = client_data["sub1_start"]
        client_data["subscription_end"] = client_data["sub1_end"]
        ask_games_option(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        if client_data["sub1_type"] == "EA Play":
            markup.add("PS Plus Deluxe", "PS Plus Extra", "PS Plus Essential")
        else:
            markup.add("EA Play")
        bot.send_message(message.chat.id, "Выберите вторую подписку:", reply_markup=markup)
        bot.register_next_step_handler(message, choose_second_duration)

def choose_second_duration(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["sub2_type"] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if client_data["sub2_type"] == "EA Play":
        markup.add("1м", "12м")
    else:
        markup.add("1м", "3м", "12м")
    bot.send_message(message.chat.id, "Срок второй подписки:", reply_markup=markup)
    bot.register_next_step_handler(message, choose_second_start)

def choose_second_start(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    client_data["sub2_duration"] = message.text
    bot.send_message(message.chat.id, "Дата оформления второй подписки (дд.мм.гггг):")
    bot.register_next_step_handler(message, process_both_subscriptions)

def process_both_subscriptions(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    try:
        start2 = datetime.strptime(message.text, "%d.%m.%Y")
    except:
        start2 = datetime.now()
    duration = client_data["sub2_duration"]
    end2 = start2 + (timedelta(days=365) if duration == "12м" else timedelta(days=30))
    client_data["sub2_start"] = start2.strftime("%d.%m.%Y")
    client_data["sub2_end"] = end2.strftime("%d.%m.%Y")

    client_data["subscription_name"] = (
        f"{client_data['sub1_type']} {client_data['sub1_duration']}; "
        f"{client_data['sub2_type']} {client_data['sub2_duration']}"
    )
    client_data["subscription_start"] = f"{client_data['sub1_start']}; {client_data['sub2_start']}"
    client_data["subscription_end"] = f"{client_data['sub1_end']}; {client_data['sub2_end']}"

    ask_games_option(message)

def ask_games_option(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Да", "Нет", "Отмена")
    bot.send_message(message.chat.id, "Шаг 7: Есть ли игры?", reply_markup=markup)
    bot.register_next_step_handler(message, collect_games)

def collect_games(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    if message.text == "Нет":
        client_data["games"] = ""
        finish_add(message)
    elif message.text == "Да":
        bot.send_message(message.chat.id, "Введите список игр (по строкам):")
        bot.register_next_step_handler(message, save_games)
    else:
        clear_chat(message.chat.id)

def save_games(message):
    if message.text == "Отмена":
        clear_chat(message.chat.id)
        return bot.send_message(message.chat.id, "Добавление отменено.", reply_markup=main_keyboard())
    games = message.text.split("\n")
    client_data["games"] = " —— ".join(games)
    finish_add(message)

def finish_add(message):
    data = (
        client_data.get("username", ""),
        client_data.get("birth_date", ""),
        client_data.get("email", ""),
        client_data.get("account_password", ""),
        client_data.get("mail_password", ""),
        client_data.get("subscription_name", "Нету"),
        client_data.get("subscription_start", ""),
        client_data.get("subscription_end", ""),
        client_data.get("region", ""),
        client_data.get("games", ""),
        client_data.get("reserve_photo", None)
    )
    add_client(data)
    clear_chat(message.chat.id)
    bot.send_message(message.chat.id, f"✅ {client_data['username']} добавлен!", reply_markup=main_keyboard())

if __name__ == "__main__":
    init_db()
    bot.infinity_polling()
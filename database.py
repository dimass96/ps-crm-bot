import json
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename='bot.log', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к файлу базы данных
DB_FILE = 'clients_db.json'

# Загрузка базы данных
def load_db():
    """
    Загружает базу данных из файла clients_db.json.
    Возвращает пустой словарь, если файл не существует или повреждён.
    """
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info("Файл базы данных не найден, создаётся пустая база")
        return {}
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON базы данных")
        return {}

# Сохранение базы данных
def save_db(data):
    """
    Сохраняет базу данных в файл clients_db.json.
    """
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("База данных успешно сохранена")
    except Exception as e:
        logger.error(f"Ошибка при сохранении базы данных: {e}")

# Добавление клиента
def add_client(client_data):
    """
    Добавляет нового клиента в базу данных.
    client_data: словарь с данными клиента.
    Возвращает ID нового клиента.
    """
    db = load_db()
    client_id = str(len(db) + 1)
    db[client_id] = client_data
    save_db(db)
    logger.info(f"Клиент {client_id} добавлен")
    return client_id

# Поиск клиента
def find_client(search_term):
    """
    Ищет клиента по номеру телефона или Telegram.
    Возвращает ID клиента и его данные, если найден, иначе None.
    """
    db = load_db()
    for client_id, client in db.items():
        if client.get('number') == search_term or client.get('telegram') == search_term:
            return client_id, client
    logger.info(f"Клиент с контактом {search_term} не найден")
    return None, None

# Редактирование клиента
def edit_client(client_id, field, value):
    """
    Редактирует указанное поле клиента.
    field: строка, указывающая поле для редактирования (number, telegram, birthdate и т.д.).
    value: новое значение поля.
    """
    db = load_db()
    if client_id in db:
        if field in ['number', 'telegram', 'birthdate', 'region', 'console', 'reserve_photo_id']:
            db[client_id][field] = value
        elif field == 'account':
            db[client_id]['account'] = value
        elif field == 'subscriptions':
            db[client_id]['subscriptions'] = value
        elif field == '.games':
            db[client_id]['games'] = value
        save_db(db)
        logger.info(f"Поле {field} клиента {client_id} обновлено")
    else:
        logger.error(f"Клиент {client_id} не найден для редактирования")

# Удаление клиента
def delete_client(client_id):
    """
    Удаляет клиента из базы данных по ID.
    """
    db = load_db()
    if client_id in db:
        del db[client_id]
        save_db(db)
        logger.info(f"Клиент {client_id} удалён")
        return True
    logger.error(f"Клиент {client_id} не найден для удаления")
    return False

# Проверка подписок
def check_subscriptions():
    """
    Проверяет подписки, возвращает список клиентов, у которых подписка истекает завтра.
    Возвращает список словарей {client_id, client_data}.
    """
    db = load_db()
    today = datetime.now().date()
    one_day = timedelta(days=1)
    expiring_clients = []
    for client_id, client in db.items():
        for sub in client.get('subscriptions', []):
            if sub['type'] == 'отсутствует':
                continue
            try:
                end_date = parse(sub['end_date'], dayfirst=True).date()
                if end_date - today == one_day:
                    expiring_clients.append({'client_id': client_id, 'client_data': client})
                    logger.info(f"Найдена подписка, истекающая завтра для клиента {client_id}")
            except Exception as e:
                logger.error(f"Ошибка проверки подписки клиента {client_id}: {e}")
    return expiring_clients

# Экспорт базы данных
def export_db():
    """
    Возвращает содержимое базы данных в виде словаря.
    """
    return load_db()

# Импорт базы данных
def import_db(new_data):
    """
    Заменяет текущую базу данных новой.
    new_data: словарь с данными базы.
    """
    try:
        save_db(new_data)
        logger.info("Новая база данных успешно импортирована")
        return True
    except Exception as e:
        logger.error(f"Ошибка при импорте базы данных: {e}")
        return False

# Валидация даты
def validate_date(date_str):
    """
    Проверяет, является ли строка валидной датой в формате дд.мм.гггг.
    Возвращает объект date или None, если формат неверный.
    """
    try:
        return parse(date_str, dayfirst=True).date()
    except:
        logger.error(f"Неверный формат даты: {date_str}")
        return None

# Расчёт даты окончания подписки
def calculate_end_date(start_date, term):
    """
    Рассчитывает дату окончания подписки на основе даты начала и срока.
    """
    try:
        start = parse(start_date, dayfirst=True).date()
        if term == '1 мес':
            return start + timedelta(days=30)
        elif term == '3 мес':
            return start + timedelta(days=90)
        elif term == '12 мес':
            return start + timedelta(days=365)
        return start
    except Exception as e:
        logger.error(f"Ошибка расчёта даты окончания: {e}")
        return None
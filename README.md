 # Telegram Bot с поддержкой Qwen 2.5 Max API

## Описание
Этот проект представляет собой Telegram-бота, который взаимодействует с API модели Qwen 2.5 Max для обработки запросов пользователей. Бот поддерживает диалоговый контекст, управление доступом через инвайт-коды и административные функции.

---

## Содержание
- [Требования](#требования)
- [Установка](#установка)
- [Настройка](#настройка)
- [Использование](#использование)
- [Команды бота](#команды-бота)
- [Администрирование](#администрирование)
- [Локальное тестирование](#локальное-тестирование)

---

## Требования
Для работы бота необходимы следующие зависимости:
- Python 3.9+
- PostgreSQL (для хранения данных о пользователях и контексте)
- Библиотеки: `python-telegram-bot`, `asyncpg`, `dashscope`, `python-dotenv`

---

## Установка
1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/Maksimnp/TelegramBot_AI.git
   cd TelegramBot_AI
   python -m venv venv
   source venv/bin/activate
   
## Установите зависимости:
   ```bash
   pip install -r requirements.txt

Создайте файл .env:
   Создайте файл .env в корне проекта и добавьте необходимые переменные окружения:
``sql
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
QWEN_APP_ID=your_qwen_app_id
QWEN_API_KEY=your_qwen_api_key
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database_name

Настройте базу данных:
Создайте базу данных PostgreSQL и примените миграции (если они есть).


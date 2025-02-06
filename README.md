Telegram Bot с поддержкой Qwen 2.5 Max API
Описание
Этот проект представляет собой Telegram-бота, который взаимодействует с API модели Qwen 2.5 Max для обработки запросов пользователей. Бот поддерживает диалоговый контекст, управление доступом через инвайт-коды и административные функции.

Для работы бота необходимы следующие зависимости:

Python 3.9+
PostgreSQL (для хранения данных о пользователях и контексте)
Библиотеки: python-telegram-bot, asyncpg, dashscope, python-dotenv
Установка
Клонируйте репозиторий:

git clone https://github.com/Maksimnp/TelegramBot_AI.git
cd TelegramBot_AI
Создайте виртуальное окружение:

python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
Установите зависимости:

pip install -r requirements.txt
Создайте файл .env:
Создайте файл .env в корне проекта и добавьте необходимые переменные окружения:

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
Настройка
API Qwen: Убедитесь, что вы зарегистрированы в AliCloud и получили QWEN_APP_ID и QWEN_API_KEY.
Telegram Bot: Создайте бота в @BotFather и получите токен (TELEGRAM_BOT_TOKEN).
База данных: Создайте таблицы allowed_users, invite_codes и user_context в PostgreSQL. Пример SQL-скрипта:

CREATE TABLE allowed_users (
    user_id BIGINT PRIMARY KEY
);

CREATE TABLE invite_codes (
    code VARCHAR(255) PRIMARY KEY,
    used BOOLEAN DEFAULT FALSE
);

CREATE TABLE user_context (
    chat_id BIGINT PRIMARY KEY,
    context JSONB NOT NULL
);

Использование
Запустите бота:
python bot.py
Начните диалог с ботом в Telegram:
Отправьте /start для начала работы.
Для очистки истории диалога используйте команду /clearhistory.
Команды бота
/start — Начать работу с ботом.
/clearhistory — Очистить историю диалога.
/request_access <инвайт-код> — Запросить доступ к боту с помощью инвайт-кода.
Администрирование
Для администраторов доступны следующие команды:

/add_user <ID пользователя> — Добавить пользователя в список разрешенных.
/generate_invite — Сгенерировать новый инвайт-код.
/admin — Открыть административное меню с кнопками управления.
Важно: ID администраторов должны быть указаны в списке ADMIN_IDS в коде бота.

Локальное тестирование
Для локального тестирования убедитесь, что:

Все переменные окружения правильно настроены.
База данных доступна и содержит необходимые таблицы.
API Qwen работает корректно.

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
import asyncpg
from dotenv import load_dotenv
import dashscope
import json
import string
import random

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования 
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Установите уровень логирования на DEBUG для подробной информации
)
logger = logging.getLogger(__name__)

# Используем переменные окружения для хранения токена и ключа API
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
QWEN_APP_ID = os.getenv('QWEN_APP_ID')
QWEN_API_KEY = os.getenv('QWEN_API_KEY')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT'))
POSTGRES_DB = os.getenv('POSTGRES_DB')

if not TELEGRAM_BOT_TOKEN or not QWEN_APP_ID or not QWEN_API_KEY:
    logger.error("Не найдены переменные окружения TELEGRAM_BOT_TOKEN, QWEN_APP_ID или QWEN_API_KEY")
    exit(1)

if not POSTGRES_USER or not POSTGRES_PASSWORD or not POSTGRES_HOST or not POSTGRES_PORT or not POSTGRES_DB:
    logger.error("Не найдены переменные окружения для подключения к базе данных")
    exit(1)

# Установка API ключа
dashscope.api_key = QWEN_API_KEY

# Настройки API Qwen 2.5 Max
dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

# Список администраторов (Добавьте свой ID Telegram)
ADMIN_IDS = [000000000000]

# Функция для подключения к базе данных
async def get_db_connection():
    try:
        conn = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        logger.debug(f"Successfully connected to the database {POSTGRES_DB}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database {POSTGRES_DB}: {e}")
        raise

# Проверка доступа пользователя
async def is_user_allowed(chat_id):
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow('SELECT 1 FROM allowed_users WHERE user_id = $1', chat_id)
        return bool(result)
    except Exception as e:
        logger.error(f"Error checking user access for chat_id {chat_id}: {e}")
        return False
    finally:
        await conn.close()

# Добавление пользователя в список разрешенных
async def add_user_to_allowed_list(chat_id):
    conn = await get_db_connection()
    try:
        await conn.execute('INSERT INTO allowed_users (user_id) VALUES ($1)', chat_id)
        logger.info(f"User {chat_id} added to the allowed list.")
    except Exception as e:
        logger.error(f"Error adding user {chat_id} to the allowed list: {e}")
    finally:
        await conn.close()

# Проверка инвайт-кода
async def check_invite_code(code):
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow('SELECT 1 FROM invite_codes WHERE code = $1 AND used = FALSE', code)
        if result:
            await conn.execute('UPDATE invite_codes SET used = TRUE WHERE code = $1', code)
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking invite code {code}: {e}")
        return False
    finally:
        await conn.close()

# Генерация нового инвайт-кода
def generate_invite_code(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Сохранение инвайт-кода в базу данных
async def save_invite_code(code):
    try:
        conn = await get_db_connection()
        # Проверяем, существует ли уже такой код в базе данных
        existing_code = await conn.fetchrow('SELECT 1 FROM invite_codes WHERE code = $1', code)
        if existing_code:
            logger.warning(f"Invite code {code} already exists in the database.")
            return
        # Сохраняем код в базу данных
        await conn.execute('INSERT INTO invite_codes (code) VALUES ($1)', code)
        logger.info(f"Invite code {code} saved successfully.")
    except asyncpg.exceptions.UniqueViolationError:
        logger.error(f"Invite code {code} violates unique constraint. Code might already exist.")
    except Exception as e:
        logger.error(f"Error saving invite code {code}: {e}")
    finally:
        if 'conn' in locals():
            await conn.close()

# Сохранение контекста пользователя
async def save_context(chat_id, context):
    conn = await get_db_connection()
    try:
        await conn.execute('''
            INSERT INTO user_context (chat_id, context) VALUES ($1, $2)
            ON CONFLICT (chat_id) DO UPDATE SET context = EXCLUDED.context
        ''', chat_id, json.dumps(context))
        logger.info(f"Context saved successfully for chat_id {chat_id}")
    except Exception as e:
        logger.error(f"Error saving context for chat_id {chat_id}: {e}")
    finally:
        await conn.close()

# Получение контекста пользователя
async def get_context(chat_id):
    conn = await get_db_connection()
    try:
        result = await conn.fetchrow('SELECT context FROM user_context WHERE chat_id = $1', chat_id)
        if result and result['context']:
            return json.loads(result['context'])
        return []
    except Exception as e:
        logger.error(f"Error fetching context for chat_id {chat_id}: {e}")
        return []
    finally:
        await conn.close()

# Вспомогательные функции
def clean_markdown(text):
    return text.replace('\\', '')

def format_list_as_markdown(response_text):
    formatted_text = ""
    lines = response_text.split("\n")
    for line in lines:
        if line.strip().startswith("-"):
            formatted_text += f"• {line[1:].strip()}\n"
        elif line.strip().startswith("1.") or line.strip().startswith("2.") or line.strip().startswith("3."):
            formatted_text += f"{line.strip()}\n"
        else:
            formatted_text += f"{line.strip()}\n"
    return formatted_text

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not await is_user_allowed(chat_id):
        await update.message.reply_text("У вас нет доступа к этому боту. Запросите доступ у администратора.")
        return
    await update.message.reply_text('Привет! Я бот, который взаимодействует с Qwen 2.5 Max API. Отправь мне запрос.')

# Команда /clearhistory
async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not await is_user_allowed(chat_id):
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return
    conn = await get_db_connection()
    try:
        await conn.execute('DELETE FROM user_context WHERE chat_id = $1', chat_id)
        logger.info(f"Deleted context for chat_id {chat_id}")
        await update.message.reply_text("История успешно удалена.")
    except Exception as e:
        logger.error(f"Error deleting context for chat_id {chat_id}: {e}")
        await update.message.reply_text("Произошла ошибка при удалении истории.")
    finally:
        await conn.close()

# Команда /request_access
async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    args = context.args
    if not args:
        await update.message.reply_text("Пожалуйста, укажите инвайт-код. Например: /request_access ABC123")
        return
    invite_code = args[0]
    if await check_invite_code(invite_code):
        await add_user_to_allowed_list(chat_id)
        await update.message.reply_text("Доступ получен! Теперь вы можете использовать бота.")
    else:
        await update.message.reply_text("Неверный или уже использованный инвайт-код.")

# Команда /add_user (админская команда)
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав администратора.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Пожалуйста, укажите ID пользователя. Например: /add_user 123456789")
        return
    user_id = int(args[0])
    await add_user_to_allowed_list(user_id)
    await update.message.reply_text(f"Пользователь {user_id} успешно добавлен в список разрешенных.")

# Команда /generate_invite (админская команда)
async def generate_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав администратора.")
        return
    new_code = generate_invite_code()
    try:
        await save_invite_code(new_code)
        await update.message.reply_text(f"Создан новый инвайт-код: `{new_code}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to save invite code {new_code}: {e}")
        await update.message.reply_text("Произошла ошибка при создании инвайт-кода. Попробуйте позже.")

# Команда /admin для администратора
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав администратора.")
        return

    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton("Сгенерировать инвайт-код", callback_data='generate_invite')],
        [InlineKeyboardButton("Посмотреть список пользователей", callback_data='view_users')],
        [InlineKeyboardButton("Закрыть меню", callback_data='close_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Административное меню:", reply_markup=reply_markup)

# Обработчик нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.from_user.id
    if chat_id not in ADMIN_IDS:
        await query.edit_message_text("У вас нет прав администратора.")
        return

    if query.data == 'generate_invite':
        new_code = generate_invite_code()
        await save_invite_code(new_code)
        await query.edit_message_text(f"Создан новый инвайт-код: `{new_code}`", parse_mode="Markdown")

    elif query.data == 'view_users':
        conn = await get_db_connection()
        try:
            result = await conn.fetch('SELECT user_id FROM allowed_users')
            if result:
                users = '\n'.join([str(row['user_id']) for row in result])
                await query.edit_message_text(f"Список разрешенных пользователей:\n{users}")
            else:
                await query.edit_message_text("Нет разрешенных пользователей.")
        except Exception as e:
            logger.error(f"Error fetching allowed users: {e}")
            await query.edit_message_text("Произошла ошибка при получении списка пользователей.")
        finally:
            if 'conn' in locals():
                await conn.close()

    elif query.data == 'close_menu':
        await query.edit_message_text("Административное меню закрыто.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    chat_type = update.message.chat.type  # Тип чата (private, group, supergroup)

    # Если это групповой чат, проверяем, упомянут ли бот
    if chat_type in ['group', 'supergroup']:
        # Проверяем, упомянут ли бот в сообщении
        if not (f"@{context.bot.username}" in update.message.text or update.message.text.startswith('/')):
            return  # Игнорируем сообщения без упоминания бота

    # Проверяем, есть ли у пользователя доступ
    if not await is_user_allowed(chat_id):
        await update.message.reply_text("У вас нет доступа к этому боту. Запросите доступ у администратора.")
        return

    # Убираем упоминание бота из текста сообщения (если оно есть)
    user_message = update.message.text.replace(f"@{context.bot.username}", "").strip()

    # Получаем контекст пользователя
    context_data = await get_context(chat_id)
    if not context_data:
        context_data = []
        logger.debug(f"No previous context found for chat_id {chat_id}. Starting with an empty context.")

    # Добавляем сообщение пользователя в контекст
    user_message_escaped = clean_markdown(user_message)
    context_data.append({'role': 'user', 'content': user_message_escaped})

    try:
        # Отправляем уведомление о наборе текста
        typing_message = await update.message.reply_text("Печатает...")

        # Формируем запрос к API
        messages = [{'role': msg['role'], 'content': msg['content']} for msg in context_data]
        response = dashscope.Application.call(app_id=QWEN_APP_ID, prompt=user_message_escaped, messages=messages)

        # Обрабатываем ответ от API
        if response and 'output' in response:
            output_content = response['output']['text']
            formatted_output = format_list_as_markdown(output_content)
            clean_output = clean_markdown(formatted_output)

            # Отправляем ответ частями, если он слишком длинный
            try:
                await send_message_in_chunks(update, clean_output)
            except Exception as e:
                logger.error(f"Ошибка при отправке: {e}")
                await send_message_in_chunks(update, output_content, max_chunk_size=4096)

            # Сохраняем контекст
            context_data.append({'role': 'assistant', 'content': clean_output})
            await save_context(chat_id, context_data)
        else:
            await update.message.reply_text("Не удалось получить ответ от API. Попробуйте позже.")

        # Удаляем уведомление о наборе текста
        await typing_message.delete()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Произошла ошибка при отправке запроса.")

# Разбиение сообщений на части
async def send_message_in_chunks(update, content, max_chunk_size=4096):
    for i in range(0, len(content), max_chunk_size):
        chunk = content[i:i + max_chunk_size]
        await update.message.reply_text(chunk)

# Создание и запуск бота
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clearhistory", clear_history))
    application.add_handler(CommandHandler("request_access", request_access))
    application.add_handler(CommandHandler("add_user", add_user))
    application.add_handler(CommandHandler("generate_invite", generate_invite))
    application.add_handler(CommandHandler("admin", admin_menu))  # Новая команда для админ-меню
    application.add_handler(CallbackQueryHandler(button_handler))  # Обработчик для кнопок
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    application.run_polling()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.error import TelegramError
from dotenv import load_dotenv
import os
import sys
import io
import logging
from datetime import datetime
from functools import lru_cache
import time

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.knowledge import find_answer, generate_answer_text, reload_index

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")

# User language preferences
USER_LANGUAGES = {}

# Request rate limiting (user_id -> [timestamps])
USER_REQUESTS = {}
MAX_REQUESTS_PER_MINUTE = 5

# Caching
@lru_cache(maxsize=100)
def cached_find_answer(question: str):
    """Cache answers for frequently asked questions."""
    return find_answer(question)


def is_rate_limited(user_id: int) -> bool:
    """Check if user exceeded rate limit."""
    now = time.time()
    if user_id not in USER_REQUESTS:
        USER_REQUESTS[user_id] = []
    
    # Remove old requests (older than 60 seconds)
    USER_REQUESTS[user_id] = [t for t in USER_REQUESTS[user_id] if now - t < 60]
    
    if len(USER_REQUESTS[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        return True
    
    USER_REQUESTS[user_id].append(now)
    return False


def get_user_lang(user_id: int) -> str:
    """Get user's preferred language (default: 'de')."""
    return USER_LANGUAGES.get(user_id, 'de')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with language selection."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started bot")
    
    keyboard = [
        [InlineKeyboardButton("Deutsch", callback_data="lang_de"),
         InlineKeyboardButton("English", callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Hallo! Wähle deine Sprache / Hello! Choose your language:",
        reply_markup=reply_markup
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "lang_de":
        USER_LANGUAGES[user_id] = 'de'
        lang = 'de'
        welcome_text = (
            "🙏 **Hare Krishna!**\n\n"
            "Ich bin **HareKrishnaAI**.\n"
            "Dein Begleiter zu den heiligen Schriften.\n\n"
            "📚 Mein Wissen:\n"
            "• Bhagavad Gita • Yoga Sutra\n"
            "• Sri Isopanishad • Srimad Bhagavatam\n"
            "• Chaitanya Charitamrita • Krishna\n\n"
            "Verwende /help für Hilfe!"
        )
    else:
        USER_LANGUAGES[user_id] = 'en'
        lang = 'en'
        welcome_text = (
            "🙏 **Hare Krishna!**\n\n"
            "I am **HareKrishnaAI**.\n"
            "Your companion to the holy scriptures.\n\n"
            "📚 My knowledge:\n"
            "• Bhagavad Gita • Yoga Sutra\n"
            "• Sri Isopanishad • Srimad Bhagavatam\n"
            "• Chaitanya Charitamrita • Krishna\n\n"
            "Use /help for help!"
        )
    
    await query.answer()
    await query.edit_message_text(text=welcome_text, parse_mode="Markdown")
    logger.info(f"User {user_id} selected language: {lang}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    logger.info(f"User {user_id} requested help")
    
    if lang == 'de':
        text = (
            "**Befehle:**\n"
            "/start - Sprache wählen\n"
            "/help - Diese Hilfe\n"
            "/list - Verfügbare Schriften\n"
            "/reload - Index aktualisieren\n\n"
            "**Fragen stellen:**\n"
            "✅ Bhagavad Gita 2.47\n"
            "✅ Yoga Sutra 1.2\n"
            "✅ Wer ist Krishna?\n"
            "✅ Was ist Dharma?\n\n"
            "Stelle einfach deine Frage!"
        )
    else:
        text = (
            "**Commands:**\n"
            "/start - Choose language\n"
            "/help - This help\n"
            "/list - Available scriptures\n"
            "/reload - Refresh index\n\n"
            "**Ask questions:**\n"
            "✅ Bhagavad Gita 2.47\n"
            "✅ Yoga Sutra 1.2\n"
            "✅ Who is Krishna?\n"
            "✅ What is Dharma?\n\n"
            "Just ask your question!"
        )
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available scriptures."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    logger.info(f"User {user_id} requested scripture list")
    
    keyboard = [
        [InlineKeyboardButton("Bhagavad Gita", callback_data="scripture_bg")],
        [InlineKeyboardButton("Yoga Sutra", callback_data="scripture_yoga")],
        [InlineKeyboardButton("Srimad Bhagavatam", callback_data="scripture_bhagavatam")],
        [InlineKeyboardButton("Sri Isopanishad", callback_data="scripture_iso")],
        [InlineKeyboardButton("Chaitanya Charitamrita", callback_data="scripture_chaitanya")],
        [InlineKeyboardButton("Krishna", callback_data="scripture_krishna")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if lang == 'de':
        text = "Wähle eine Schrift:"
    else:
        text = "Choose a scripture:"
    
    await update.message.reply_text(text, reply_markup=reply_markup)


async def scripture_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle scripture selection."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    
    scriptures = {
        "scripture_bg": ("Bhagavad Gita 2.47", "Bhagavad Gita"),
        "scripture_yoga": ("Yoga Sutra 1.2", "Yoga Sutra"),
        "scripture_bhagavatam": ("Srimad Bhagavatam 1.1", "Srimad Bhagavatam"),
        "scripture_iso": ("Sri Isopanishad 1", "Sri Isopanishad"),
        "scripture_chaitanya": ("Chaitanya Charitamrita 1.1", "Chaitanya Charitamrita"),
        "scripture_krishna": ("Wer ist Krishna?", "Krishna")
    }
    
    query_text, title = scriptures.get(query.data, ("", ""))
    await query.answer()
    
    if query_text:
        await query.edit_message_text(text=f"Suche nach: {title}...", parse_mode="Markdown")
        result = cached_find_answer(query_text)
        if result:
            text = generate_answer_text(query_text, result, lang=lang)
            if len(text) > 4000:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    await query.message.reply_text(chunk, parse_mode="Markdown")
            else:
                await query.edit_message_text(text=text, parse_mode="Markdown")
        else:
            if lang == 'de':
                await query.edit_message_text(text="Keine Ergebnisse gefunden.")
            else:
                await query.edit_message_text(text="No results found.")


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    question = update.message.text
    
    logger.info(f"User {user_id} asked: {question}")
    
    # Rate limiting
    if is_rate_limited(user_id):
        if lang == 'de':
            msg = "Zu viele Anfragen! Bitte warte einen Moment."
        else:
            msg = "Too many requests! Please wait a moment."
        await update.message.reply_text(msg)
        return
    
    try:
        result = cached_find_answer(question)
        if result:
            text = generate_answer_text(question, result, lang=lang)
            if len(text) > 4000:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode="Markdown")
            else:
                await update.message.reply_text(text, parse_mode="Markdown")
        else:
            if lang == 'de':
                text = (
                    "Ich habe dazu keinen passenden Vers.\n\n"
                    "Versuche:\n"
                    "• Bhagavad Gita 2.47\n"
                    "• Yoga Sutra 1.2\n"
                    "• /list"
                )
            else:
                text = (
                    "I don't have a matching verse.\n\n"
                    "Try:\n"
                    "• Bhagavad Gita 2.47\n"
                    "• Yoga Sutra 1.2\n"
                    "• /list"
                )
            await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {e}")
        if lang == 'de':
            error_msg = "Entschuldigung, ein Fehler ist aufgetreten. Bitte versuche es später erneut."
        else:
            error_msg = "Sorry, an error occurred. Please try again later."
        await update.message.reply_text(error_msg)


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reload knowledge base index."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    logger.info(f"User {user_id} triggered reload")
    
    try:
        if lang == 'de':
            await update.message.reply_text("Aktualisiere Index...")
        else:
            await update.message.reply_text("Updating index...")
        
        count = reload_index()
        cached_find_answer.cache_clear()  # Clear cache
        
        if lang == 'de':
            msg = f"Index aktualisiert: {count} Eintraege"
        else:
            msg = f"Index updated: {count} entries"
        
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error during reload: {e}")
        if lang == 'de':
            error_msg = "Fehler beim Aktualisieren des Index."
        else:
            error_msg = "Error updating index."
        await update.message.reply_text(error_msg)


if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN fehlt in .env")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("list", list_cmd))
app.add_handler(CommandHandler("reload", cmd_reload))
app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
app.add_handler(CallbackQueryHandler(scripture_callback, pattern="^scripture_"))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, answer)
)

logger.info("Bot started successfully")
print("Bot is running...")

app.run_polling()

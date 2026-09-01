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
from app.database import save_favorite, get_favorites, remove_favorite, set_user_language, get_user_language

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
         InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("हिंदी", callback_data="lang_hi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Hallo! Wähle deine Sprache / Hello! Choose your language / नमस्ते! भाषा चुनें:",
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
    elif query.data == "lang_en":
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
    else:  # Hindi
        USER_LANGUAGES[user_id] = 'hi'
        lang = 'hi'
        welcome_text = (
            "🙏 **हरे कृष्ण!**\n\n"
            "मैं **HareKrishnaAI** हूँ।\n"
            "पवित्र शास्त्रों के लिए आपका साथी।\n\n"
            "📚 मेरा ज्ञान:\n"
            "• भगवद गीता • योग सूत्र\n"
            "• श्री इशोपनिषद • श्रीमद भागवतम्\n"
            "• चैतन्य चरितामृत • कृष्ण\n\n"
            "सहायता के लिए /help का उपयोग करें!"
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
    elif lang == 'en':
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
    else:  # Hindi
        text = (
            "**कमांड:**\n"
            "/start - भाषा चुनें\n"
            "/help - यह सहायता\n"
            "/list - उपलब्ध शास्त्र\n"
            "/reload - इंडेक्स रीफ्रेश करें\n\n"
            "**प्रश्न पूछें:**\n"
            "✅ भगवद गीता 2.47\n"
            "✅ योग सूत्र 1.2\n"
            "✅ कृष्ण कौन हैं?\n"
            "✅ धर्म क्या है?\n\n"
            "बस अपना प्रश्न पूछें!"
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
        [InlineKeyboardButton("Krishna", callback_data="scripture_krishna")],
        [InlineKeyboardButton("Vedas", callback_data="scripture_vedas")],
        [InlineKeyboardButton("Upanishads", callback_data="scripture_upanishads")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if lang == 'de':
        text = "Wähle eine Schrift:"
    elif lang == 'en':
        text = "Choose a scripture:"
    else:  # Hindi
        text = "एक शास्त्र चुनें:"
    
    await update.message.reply_text(text, reply_markup=reply_markup)


async def scripture_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle scripture selection."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    
    # Map scripture buttons to specific search queries
    scriptures = {
        "scripture_bg": "Bhagavad Gita 1.1",
        "scripture_yoga": "Yoga Sutra 1.1",
        "scripture_bhagavatam": "Srimad Bhagavatam 1.1",
        "scripture_iso": "Sri Isopanishad",
        "scripture_chaitanya": "Chaitanya Charitamrita 1.1",
        "scripture_krishna": "Krishna Introduction who_is",
        "scripture_vedas": "Rig Veda 1.1",
        "scripture_upanishads": "Isha Upanishad"
    }
    
    query_text = scriptures.get(query.data, "")
    title = {
        "scripture_bg": "Bhagavad Gita",
        "scripture_yoga": "Yoga Sutra",
        "scripture_bhagavatam": "Srimad Bhagavatam",
        "scripture_iso": "Sri Isopanishad",
        "scripture_chaitanya": "Chaitanya Charitamrita",
        "scripture_krishna": "Krishna",
        "scripture_vedas": "Vedas",
        "scripture_upanishads": "Upanishads"
    }.get(query.data, "")
    
    await query.answer()
    
    if query_text:
        if lang == 'de':
            await query.edit_message_text(text=f"Suche nach: {title}...", parse_mode="Markdown")
        elif lang == 'en':
            await query.edit_message_text(text=f"Searching: {title}...", parse_mode="Markdown")
        else:
            await query.edit_message_text(text=f"खोज रहे हैं: {title}...", parse_mode="Markdown")
        
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
            elif lang == 'en':
                await query.edit_message_text(text="No results found.")
            else:
                await query.edit_message_text(text="कोई परिणाम नहीं मिला।")


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
        elif lang == 'en':
            msg = "Too many requests! Please wait a moment."
        else:  # Hindi
            msg = "बहुत सारे अनुरोध! कृपया एक पल प्रतीक्षा करें।"
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
            elif lang == 'en':
                text = (
                    "I don't have a matching verse.\n\n"
                    "Try:\n"
                    "• Bhagavad Gita 2.47\n"
                    "• Yoga Sutra 1.2\n"
                    "• /list"
                )
            else:  # Hindi
                text = (
                    "मेरे पास इसके लिए कोई मिलान वाली श्लोक नहीं है।\n\n"
                    "कोशिश करें:\n"
                    "• भगवद गीता 2.47\n"
                    "• योग सूत्र 1.2\n"
                    "• /list"
                )
            await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {e}")
        if lang == 'de':
            error_msg = "Entschuldigung, ein Fehler ist aufgetreten. Bitte versuche es später erneut."
        elif lang == 'en':
            error_msg = "Sorry, an error occurred. Please try again later."
        else:  # Hindi
            error_msg = "क्षमा करें, एक त्रुटि हुई। कृपया बाद में फिर से प्रयास करें।"
        await update.message.reply_text(error_msg)


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reload knowledge base index."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    logger.info(f"User {user_id} triggered reload")
    
    try:
        if lang == 'de':
            await update.message.reply_text("Aktualisiere Index...")
        elif lang == 'en':
            await update.message.reply_text("Updating index...")
        else:  # Hindi
            await update.message.reply_text("इंडेक्स अपडेट कर रहे हैं...")
        
        count = reload_index()
        cached_find_answer.cache_clear()  # Clear cache
        
        if lang == 'de':
            msg = f"Index aktualisiert: {count} Eintraege"
        elif lang == 'en':
            msg = f"Index updated: {count} entries"
        else:  # Hindi
            msg = f"इंडेक्स अपडेट: {count} प्रविष्टियां"
        
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error during reload: {e}")
        if lang == 'de':
            error_msg = "Fehler beim Aktualisieren des Index."
        elif lang == 'en':
            error_msg = "Error updating index."
        else:  # Hindi
            error_msg = "इंडेक्स अपडेट करने में त्रुटि।"
        await update.message.reply_text(error_msg)


async def save_fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a scripture verse to favorites."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    if not context.args:
        if lang == 'de':
            msg = "Verwendung: /save Bhagavad Gita 2.47"
        elif lang == 'en':
            msg = "Usage: /save Bhagavad Gita 2.47"
        else:
            msg = "उपयोग: /save भगवद गीता 2.47"
        await update.message.reply_text(msg)
        return
    
    query = " ".join(context.args)
    result = cached_find_answer(query)
    
    if result:
        success = save_favorite(user_id, result.get("source", ""), result.get("chapter", ""), result.get("verse", ""))
        if success:
            if lang == 'de':
                msg = f"Gespeichert: {result.get('source')} {result.get('chapter')}.{result.get('verse')}"
            elif lang == 'en':
                msg = f"Saved: {result.get('source')} {result.get('chapter')}.{result.get('verse')}"
            else:
                msg = f"सहेजा गया: {result.get('source')} {result.get('chapter')}.{result.get('verse')}"
        else:
            if lang == 'de':
                msg = "Bereits in Favoriten!"
            elif lang == 'en':
                msg = "Already in favorites!"
            else:
                msg = "पहले से पसंदीदा में है!"
    else:
        if lang == 'de':
            msg = "Vers nicht gefunden!"
        elif lang == 'en':
            msg = "Verse not found!"
        else:
            msg = "श्लोक नहीं मिला!"
    
    await update.message.reply_text(msg)
    logger.info(f"User {user_id} saved favorite: {query}")


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all saved favorites."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    favorites = get_favorites(user_id)
    
    if not favorites:
        if lang == 'de':
            msg = "Du hast keine Favoriten gespeichert! Benutze /save"
        elif lang == 'en':
            msg = "You have no favorites! Use /save"
        else:
            msg = "आपके कोई पसंदीदा नहीं हैं! /save का उपयोग करें"
        await update.message.reply_text(msg)
        return
    
    text = "⭐ **Deine Favoriten:**\n\n" if lang == 'de' else "⭐ **Your Favorites:**\n\n" if lang == 'en' else "⭐ **आपके पसंदीदा:**\n\n"
    
    for i, fav in enumerate(favorites[:20], 1):  # Show first 20
        ref = f"{fav['source']} {fav['chapter']}.{fav['verse']}" if fav['verse'] else f"{fav['source']} {fav['chapter']}"
        text += f"{i}. {ref}\n"
    
    if len(favorites) > 20:
        text += f"\n... und {len(favorites) - 20} mehr"
    
    await update.message.reply_text(text, parse_mode="Markdown")
    logger.info(f"User {user_id} viewed favorites")


if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN fehlt in .env")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("list", list_cmd))
app.add_handler(CommandHandler("reload", cmd_reload))
app.add_handler(CommandHandler("save", save_fav))
app.add_handler(CommandHandler("favorites", show_favorites))
app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
app.add_handler(CallbackQueryHandler(scripture_callback, pattern="^scripture_"))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, answer)
)

logger.info("Bot started successfully")
print("Bot is running...")

app.run_polling()

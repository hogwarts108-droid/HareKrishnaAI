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
import threading
from flask import Flask, render_template, request
import json
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Language detection
try:
    from langdetect import detect, detect_langs
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("langdetect not installed. Install with: pip install langdetect")

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


def detect_user_language(text: str) -> str:
    """Auto-detect language from user input."""
    if not HAS_LANGDETECT or not text or len(text.strip()) < 3:
        return None
    
    try:
        detected = detect(text)
        # Map detected lang codes to our supported langs
        lang_map = {
            'de': 'de', 'en': 'en', 'hi': 'hi',
            'en-US': 'en', 'en-GB': 'en', 'de-DE': 'de'
        }
        return lang_map.get(detected, None)
    except:
        return None


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
            "/reload - Index aktualisieren\n"
            "/clear - Chat löschen & neu starten\n\n"
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
            "/reload - Refresh index\n"
            "/clear - Clear chat & restart\n\n"
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
            "/reload - इंडेक्स रीफ्रेश करें\n"
            "/clear - चैट साफ़ करें और पुनः शुरू करें\n\n"
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
                    await query.message.reply_text(chunk)
            else:
                await query.edit_message_text(text=text)
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
    question = update.message.text
    
    # Auto-detect language from user input
    detected_lang = detect_user_language(question)
    if detected_lang:
        lang = detected_lang
        USER_LANGUAGES[user_id] = lang  # Remember for next time
    else:
        lang = get_user_lang(user_id)
    
    logger.info(f"User {user_id} asked ({lang}): {question}")
    
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
            
            # Add inline buttons for figure entries
            reply_markup = None
            source = result.get("source", "").lower().replace(" ", "-")
            wikipedia_url = f"https://en.wikipedia.org/wiki/{result.get('source')}"
            
            keyboard = [
                [InlineKeyboardButton("📚 Wikipedia", url=wikipedia_url),
                 InlineKeyboardButton("❤️ Save", callback_data=f"save_{source}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if len(text) > 4000:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for i, chunk in enumerate(chunks):
                    # Only add buttons to last chunk
                    markup = reply_markup if i == len(chunks) - 1 else None
                    await update.message.reply_text(chunk, reply_markup=markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            if lang == 'de':
                text = (
                    "Ich habe dazu keinen passenden Vers.\n\n"
                    "Versuche:\n"
                    "• Bhagavad Gita 2.47\n"
                    "• /list - Alle Figuren ansehen"
                )
            elif lang == 'en':
                text = (
                    "I don't have a matching verse.\n\n"
                    "Try:\n"
                    "• Bhagavad Gita 2.47\n"
                    "• /list - View all figures"
                )
            else:  # Hindi
                text = (
                    "मेरे पास इसके लिए कोई मिलान वाली श्लोक नहीं है।\n\n"
                    "कोशिश करें:\n"
                    "• भगवद गीता 2.47\n"
                    "• /list - सभी आंकड़े देखें"
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
    """Reload knowledge base index (fast - only reloads entries)."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    logger.info(f"User {user_id} triggered reload")
    
    try:
        if lang == 'de':
            msg_loading = "⏳ Lade Knowledge Base neu..."
        elif lang == 'en':
            msg_loading = "⏳ Reloading knowledge base..."
        else:  # Hindi
            msg_loading = "⏳ नॉलेज बेस को फिर से लोड कर रहे हैं..."
        
        loading_msg = await update.message.reply_text(msg_loading)
        
        import time
        start = time.time()
        count = reload_index()
        cached_find_answer.cache_clear()  # Clear cache
        elapsed = time.time() - start
        
        if lang == 'de':
            msg = f"✅ Index aktualisiert: {count} Einträge ({elapsed:.1f}s)"
        elif lang == 'en':
            msg = f"✅ Index updated: {count} entries ({elapsed:.1f}s)"
        else:  # Hindi
            msg = f"✅ इंडेक्स अपडेट: {count} प्रविष्टियां ({elapsed:.1f}s)"
        
        # Edit the loading message with final result
        try:
            await loading_msg.edit_text(msg)
        except:
            # If edit fails, just send new message
            await update.message.reply_text(msg)
            
    except Exception as e:
        logger.error(f"Error during reload: {e}")
        if lang == 'de':
            error_msg = "❌ Fehler beim Aktualisieren des Index."
        elif lang == 'en':
            error_msg = "❌ Error updating index."
        else:  # Hindi
            error_msg = "❌ इंडेक्स अपडेट करने में त्रुटि।"
        
        await update.message.reply_text(error_msg)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear chat and restart from beginning."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    logger.info(f"User {user_id} requested chat clear")
    
    try:
        if lang == 'de':
            await update.message.reply_text("🗑️ Chat wird geleert...")
        elif lang == 'en':
            await update.message.reply_text("🗑️ Clearing chat...")
        else:  # Hindi
            await update.message.reply_text("🗑️ चैट साफ़ किया जा रहा है...")
        
        time.sleep(1)  # Brief pause for UX
        
        # Restart with start command
        await start(update, context)
    except Exception as e:
        logger.error(f"Error during clear: {e}")
        if lang == 'de':
            error_msg = "Fehler beim Löschen des Chats."
        elif lang == 'en':
            error_msg = "Error clearing chat."
        else:  # Hindi
            error_msg = "चैट साफ़ करने में त्रुटि।"
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
app.add_handler(CommandHandler("clear", cmd_clear))
app.add_handler(CommandHandler("save", save_fav))
app.add_handler(CommandHandler("favorites", show_favorites))
app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
app.add_handler(CallbackQueryHandler(scripture_callback, pattern="^scripture_"))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, answer)
)

logger.info("Bot started successfully")
print("Bot is running...")

# Create Flask app for web routes
flask_app = Flask(__name__, template_folder='app/templates')
BASE_DIR = Path(__file__).resolve().parent.parent

@flask_app.route('/krishna')
def krishna_story():
    """Serve the complete Krishna story page."""
    krishna_file = BASE_DIR / "data" / "scriptures" / "krishna_book.json"
    try:
        with open(krishna_file, 'r', encoding='utf-8') as f:
            krishna_entries = json.load(f)
    except Exception as e:
        logger.error(f"Error loading Krishna data: {e}")
        krishna_entries = []
    
    return render_template('krishna.html', entries=krishna_entries)


@flask_app.route('/figures')
def figures_index():
    """Serve figure index page with Wikipedia links and optional search."""
    figures_file = BASE_DIR / "data" / "scriptures" / "figures_introductions.json"
    q = request.args.get('q', '').strip().lower()
    try:
        with open(figures_file, 'r', encoding='utf-8') as f:
            figures_data = json.load(f)
        
        # Group by source (figure name)
        figures_dict = {}
        for entry in figures_data:
            source = entry.get('source')
            if source not in figures_dict:
                figures_dict[source] = {
                    'source': source,
                    'wikipedia': entry.get('wikipedia', ''),
                    'entries': []
                }
            figures_dict[source]['entries'].append(entry)
        
        figures = list(figures_dict.values())
        figures.sort(key=lambda x: x['source'])
        
        # If search query provided, filter figures
        if q:
            filtered = []
            for fig in figures:
                name = (fig['source'] or '').lower()
                wiki = (fig.get('wikipedia') or '').lower()
                translations_text = ' '.join(
                    [entry.get('translation', {}).get('de','') + ' ' + entry.get('translation', {}).get('en','') + ' ' + entry.get('translation', {}).get('hi','') for entry in fig.get('entries', [])]
                ).lower()
                if q in name or q in wiki or q in translations_text:
                    filtered.append(fig)
            figures = filtered
    except Exception as e:
        logger.error(f"Error loading figures data: {e}")
        figures = []
    
    return render_template('figures.html', figures=figures, q=request.args.get('q',''))

@flask_app.route('/health')
def health():
    return {'status': 'ok'}

# Use polling mode for reliability (handles all updates in order)
# This is more stable than webhooks and doesn't require domain configuration
logger.info("Starting bot in polling mode (24/7)")
logger.info("Bot will receive updates continuously from Telegram servers")

if __name__ == '__main__':
    app.run_polling()

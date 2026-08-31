from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import os
import sys
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.knowledge import find_answer, generate_answer_text, reload_index

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🙏 **Hare Krishna!**\n\n"
        "Ich bin **HareKrishnaAI**.\n"
        "Ich bin dein Begleiter zu den heiligen Schriften.\n\n"
        "📚 **Mein Wissen:**\n"
        "• Bhagavad Gita (Kapitel 1-18)\n"
        "• Yoga Sutra (Patanjali)\n"
        "• Sri Isopanishad (Upanishaden)\n"
        "• Srimad Bhagavatam\n"
        "• Chaitanya Charitamrita\n\n"
        "💬 **Wie fragst du?**\n"
        "❌ 'Was ist Dharma?'\n"
        "✅ 'Bhagavad Gita 18.66'\n"
        "✅ 'Yoga Sutra 1.2'\n"
        "✅ 'Srimad Bhagavatam 1.2.6'\n"
        "✅ 'Chaitanya Charitamrita 1.1'\n\n"
        "💡 **/reload** - Index erneuern\n"
        "🌿 /start - Diese Hilfe\n\n"
        "Gestellt deine Frage! 🙏"
    )


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    result = find_answer(question)
    if result:
        # Use LLM to generate a polished answer if available, otherwise format
        text = generate_answer_text(question, result, lang='de')
        # Split long answers to avoid Telegram limits
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
    else:
        text = (
            "🙏 Hare Krishna!\n\n"
            "Ich habe dazu noch keinen passenden Vers in meiner Datenbank.\n\n"
            "💡 Versuche es so:\n"
            "• Bhagavad Gita 2.47\n"
            "• Yoga Sutra 1.2\n"
            "• Chaitanya Charitamrita 1.1\n"
            "• Was ist Moksha?\n"
            "• Krishna Liebe"
        )
        await update.message.reply_text(text)


if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN fehlt in .env")


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Baue Index neu auf...")
    count = reload_index()
    await update.message.reply_text(f"✅ Index neu aufgebaut: {count} Einträge.")


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reload", cmd_reload))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, answer)
)

print("Bot is running...")

app.run_polling()

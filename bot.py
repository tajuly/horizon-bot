import logging
import random
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from cards import CARDS

# --- Настройки ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
HISTORY_FILE = "history.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthHandler)
    server.serve_forever()


def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_to_history(user_id: int, card: dict):
    history = load_history()
    uid = str(user_id)
    if uid not in history:
        history[uid] = []
    history[uid].append({
        "card_id": card["id"],
        "name": card["name"],
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    history[uid] = history[uid][-50:]
    save_history(history)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🃏 Вытянуть карту", callback_data="draw_card")],
        [InlineKeyboardButton("📜 Моя история", callback_data="show_history")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✨ *Горизонт Событий* ✨\n\n"
        "Добро пожаловать в мир оракула.\n"
        "Задай вопрос в своём сердце и вытяни карту — она даст тебе ответ.\n\n"
        "Выбери действие:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Как пользоваться ботом:*\n\n"
        "/start — главное меню\n"
        "/draw — вытянуть карту\n"
        "/history — посмотреть историю карт\n"
        "/help — помощь\n\n"
        "Или используй кнопки в главном меню.",
        parse_mode="Markdown"
    )


async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_card(update, context, user_id=update.effective_user.id)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_history(update, context, user_id=update.effective_user.id)


async def send_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    card = random.choice(CARDS)
    add_to_history(user_id, card)

    text = (
        f"🌌 *{card['name']}*\n\n"
        f"_{card['description']}_\n\n"
        f"💫 *Толкование:*\n{card['meaning']}"
    )

    keyboard = [
        [InlineKeyboardButton("🃏 Вытянуть ещё", callback_data="draw_card")],
        [InlineKeyboardButton("📜 Моя история", callback_data="show_history")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    image_path = f"cards_images/{card['id']}.jpg"
    if os.path.exists(image_path):
        with open(image_path, "rb") as img:
            if update.callback_query:
                await update.callback_query.message.reply_photo(
                    photo=img,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_photo(
                    photo=img,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
    else:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    history = load_history()
    uid = str(user_id)

    keyboard = [
        [InlineKeyboardButton("🃏 Вытянуть карту", callback_data="draw_card")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if uid not in history or not history[uid]:
        text = "📜 У тебя ещё нет истории карт.\n\nВытяни свою первую карту!"
    else:
        records = history[uid][-10:]
        lines = ["📜 *Последние карты:*\n"]
        for r in reversed(records):
            lines.append(f"• {r['date']} — *{r['name']}*")
        text = "\n".join(lines)

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "draw_card":
        await send_card(update, context, user_id=query.from_user.id)
    elif query.data == "show_history":
        await show_history(update, context, user_id=query.from_user.id)
    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🃏 Вытянуть карту", callback_data="draw_card")],
            [InlineKeyboardButton("📜 Моя история", callback_data="show_history")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "✨ *Горизонт Событий* ✨\n\nВыбери действие:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("draw", draw_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

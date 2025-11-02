import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# -------------------------------
# ✅ Logging setup
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -------------------------------
# ✅ Bot Token (use env var for safety)
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set. Please set it before running.")

# -------------------------------
# ✅ Keyboard Layout
# -------------------------------
def main_menu_keyboard():
    keyboard = [
        ["👤 Profile", "🎫 Lottery"],
        ["💰 Deposit", "📤 Withdraw"],
        ["🏠 Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# -------------------------------
# ✅ /start Command
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Lottery Bot!\n\nPlease use the menu below 👇",
        reply_markup=main_menu_keyboard()
    )

# -------------------------------
# ✅ Message Handler
# -------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "👤 Profile":
        await update.message.reply_text("👤 Profile Info:\nBalance: 0 Ks")
    elif text == "🎫 Lottery":
        await update.message.reply_text("🎫 You can buy lottery tickets here soon!")
    elif text == "💰 Deposit":
        await update.message.reply_text("💰 Deposit to: KPay 09789999368")
    elif text == "📤 Withdraw":
        await update.message.reply_text("📤 Withdraw feature coming soon!")
    elif text == "🏠 Main Menu":
        await update.message.reply_text("🏠 Back to main menu", reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text("❗ Please use the menu buttons.", reply_markup=main_menu_keyboard())

# -------------------------------
# ✅ Main Function
# -------------------------------
def main():
    print("🚀 Starting Telegram Bot...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

# -------------------------------
# ✅ Run Bot
# -------------------------------
if __name__ == "__main__":
    main()

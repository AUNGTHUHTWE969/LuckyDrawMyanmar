import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')

def main_menu_keyboard():
    keyboard = [
        ["👤 Profile", "🎫 Lottery"],
        ["💰 Deposit", "📤 Withdraw"],
        ["🏠 Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Welcome to Lottery Bot!\nUse the menu below:",
        reply_markup=main_menu_keyboard()
    )

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    
    if text == "👤 Profile":
        await update.message.reply_text("Profile: Balance 0 Ks")
    elif text == "🎫 Lottery":
        await update.message.reply_text("Buy lottery tickets")
    elif text == "💰 Deposit":
        await update.message.reply_text("Deposit to: KPay 09789999368")
    elif text == "🏠 Main Menu":
        await start(update, context)
    else:
        await update.message.reply_text("Use menu options", reply_markup=main_menu_keyboard())

def main():
    print("🚀 Starting bot...")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()

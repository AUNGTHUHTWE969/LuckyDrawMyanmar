import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')

async def start(update, context):
    await update.message.reply_text("🤖 Bot is working!")

async def echo(update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

def main():
    print("Starting test bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, echo))
    print("Bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()

import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from aiohttp import web

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')

# Simple in-memory database
users = {}

# Web server for health checks
async def health_check(request):
    return web.Response(text="✅ Telegram Lottery Bot is running on Render!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Web server running on port {port}")
    return runner

# Keyboard
def main_menu_keyboard():
    keyboard = [
        ["👤 My Profile", "🎫 ကံစမ်းမဲ ဝယ်ယူရန်"],
        ["💰 ငွေသွင်း", "📤 ငွေထုတ်"],
        ["📊 မှတ်တမ်းကြည့်ရန️်", "❓ FAQ"],
        ["🏠 ပင်မမီနူး"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 မင်္ဂလာပါ {user.first_name}!\n\n"
        "Telegram Lottery Bot မှ ကြိုဆိုပါတယ်! 🎉\n\n"
        "ကျေးဇူးပြု၍ အောက်ပါ menu မှ ရွေးချယ်မှုများကို အသုံးပြုပါ။",
        reply_markup=main_menu_keyboard()
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        await update.message.reply_text(
            "✅ သင်မှတ်ပုံတင်ပြီးသားဖြစ်ပါသည်!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    users[user_id] = {
        'name': update.effective_user.first_name,
        'phone': '09-XXXXXXX',
        'balance': 0,
        'registered_at': '2024-01-01',
        'referral_code': f"REF{user_id}"
    }
    
    await update.message.reply_text(
        f"✅ မှတ်ပုံတင်ပြီးပါပြီ {update.effective_user.first_name}!\n\n"
        f"👤 အမည်: {update.effective_user.first_name}\n"
        f"📞 ဖုန်း: 09-XXXXXXX\n"
        f"💰 လက်ကျန်ငွေ: 0 Ks\n"
        f"🔗 Referral Code: REF{user_id}\n\n"
        "🎉 ယခု ကံစမ်းမဲများ ဝယ်ယူနိုင်ပါပြီ!",
        reply_markup=main_menu_keyboard()
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        user_data = users[user_id]
        await update.message.reply_text(
            f"👤 **My Profile**\n\n"
            f"**NAME**\n{user_data['name']}\n\n"
            f"**PH NO.**\n{user_data['phone']}\n\n"
            f"**Balance**\n{user_data['balance']:,} Ks\n\n"
            f"**Referral Code**\n{user_data['referral_code']}\n\n"
            f"**Register Date**\n{user_data['registered_at']}",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ\n"
            "မှတ်ပုံတင်ရန် /register ကိုနှိပ်ပါ",
            reply_markup=main_menu_keyboard()
        )

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text(
            "❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ",
            reply_markup=main_menu_keyboard()
        )
        return
    
    await update.message.reply_text(
        "💰 **ငွေသွင်းရန်**\n\n"
        "ကျေးဇူးပြု၍ ငွေသွင်းနည်းလမ်းရွေးပါ:\n\n"
        "📱 KPay - 09789999368\n"
        "📱 WavePay - 09789999368\n\n"
        "ငွေသွင်းပြီးပါက Screenshot ပို့ပါ။",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text(
            "❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ",
            reply_markup=main_menu_keyboard()
        )
        return
    
    user_data = users[user_id]
    await update.message.reply_text(
        f"📤 **ငွေထုတ်ရန်**\n\n"
        f"💳 သင့်လက်ကျန်ငွေ: {user_data['balance']:,} Ks\n\n"
        "ကျေးဇူးပြု၍ ငွေထုတ်နည်းလမ်းရွေးပါ:\n\n"
        "📱 KPay\n"
        "📱 WavePay\n\n"
        "ငွေထုတ်ယူမည့်ပမာဏ ရိုက်ထည့်ပါ။",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text(
            "❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ",
            reply_markup=main_menu_keyboard()
        )
        return
    
    user_data = users[user_id]
    await update.message.reply_text(
        f"🎫 **ကံစမ်းမဲ ဝယ်ယူရန်**\n\n"
        f"💳 သင့်လက်ကျန်ငွေ: {user_data['balance']:,} Ks\n\n"
        "ကျေးဇူးပြု၍ ရွေးချယ်ပါ:\n\n"
        "• 1 Ticket - 1,000 Ks\n"
        "• 2 Tickets - 1,800 Ks\n" 
        "• 5 Tickets - 4,000 Ks\n"
        "• 7 Tickets - 5,600 Ks\n\n"
        "မိမိကြိုက်နှစ်သက်ရာ ဝယ်ယူနိုင်ပါသည်။",
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 **မှတ်တမ်းကြည့်ရန်**\n\n"
        "သင့်ငွေသွင်း/ထုတ်မှတ်တမ်းများ ကြည့်ရှုနိုင်ပါသည်။\n\n"
        "မည်သည့်ငွေသွင်း/ထုတ်မှတ်တမ်းမျှမရှိသေးပါ။\n\n"
        "စတင်ငွေသွင်းရန် ငွေသွင်းခလုတ်ကိုနှိပ်ပါ။",
        reply_markup=main_menu_keyboard()
    )

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ **FAQ**\n\n"
        "အမေးများသောမေးခွန်းများ:\n\n"
        "Q: မှတ်ပုံတင်နည်း\n"
        "A: /register ကိုနှိပ်ပါ\n\n"
        "Q: ငွေသွင်းနည်း\n"
        "A: KPay/WavePay ဖြင့်သွင်းနိုင်ပါသည်\n\n"
        "Q: ငွေထုတ်နည်း\n"
        "A: လက်ကျန်ငွေရှိပါက ထုတ်နိုင်ပါသည်\n\n"
        "အခြားမေးခွန်းများအတွက် Admin နှင့်ဆက်သွယ်ပါ။",
        reply_markup=main_menu_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "👤 My Profile":
        await profile(update, context)
    elif text == "🎫 ကံစမ်းမဲ ဝယ်ယူရန်":
        await lottery(update, context)
    elif text == "💰 ငွေသွင်း":
        await deposit(update, context)
    elif text == "📤 ငွေထုတ်":
        await withdraw(update, context)
    elif text == "📊 မှတ်တမ်းကြည့်ရန️်":
        await history(update, context)
    elif text == "❓ FAQ":
        await faq(update, context)
    elif text == "🏠 ပင်မမီနူး":
        await start(update, context)
    else:
        await update.message.reply_text(
            "ℹ️ ကျေးဇူးပြု၍ menu မှ ရွေးချယ်မှုများကို အသုံးပြုပါ။",
            reply_markup=main_menu_keyboard()
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error occurred: {context.error}")

async def main():
    logger.info("🚀 Starting Telegram Lottery Bot on Render...")
    
    # Check if BOT_TOKEN is available
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found in environment variables!")
        return
    
    try:
        # Start web server for health checks
        web_runner = await start_web_server()
        
        # Create bot application - FIXED: Use correct version for python-telegram-bot v20.x
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        application.add_handler(CommandHandler("profile", profile))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        # Start bot - FIXED: Correct way to start for v20.x
        await application.initialize()
        await application.start()
        
        # Start polling
        await application.updater.start_polling()
        
        logger.info("✅ Bot started successfully on Render!")
        logger.info("📱 Bot is now listening for messages...")
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
            
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        # Don't re-raise the exception to prevent immediate restart loop
        await asyncio.sleep(60)  # Wait before exiting
    finally:
        # Cleanup
        logger.info("🛑 Shutting down bot...")
        try:
            if 'application' in locals():
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
            if 'web_runner' in locals():
                await web_runner.cleanup()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

if __name__ == '__main__':
    asyncio.run(main())

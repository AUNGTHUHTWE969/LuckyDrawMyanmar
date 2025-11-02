import os

# Debug: Check current directory and files
print("=== DEBUG INFO ===")
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")
print("==================")
import os
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import datetime
import random
import asyncio
from aiohttp import web

# Configure logging for Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get Bot Token from Environment Variable
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')

# Database (In-memory)
users = {}
payment_accounts = {
    "kpay": [
        {
            "account_name": "AUNG THU HTWE", 
            "phone_number": "09789999368",
            "account_holder": "AUNG THU HTWE"
        }
    ],
    "wavepay": [
        {
            "account_name": "AUNG THU HTWE",
            "phone_number": "09789999368", 
            "account_holder": "AUNG THU HTWE"
        }
    ]
}
admins = {8070878424: {"username": "Main Admin", "added_by": "system", "added_date": "2024-01-01", "level": "super_admin"}}

# Health check endpoint
async def health_check(request):
    return web.Response(text="✅ Telegram Bot is running!")

async def handle_web_request(request):
    return web.Response(text="🤖 Telegram Lottery Bot is Alive!")

async def start_web_server():
    """Start web server for Render health checks"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', handle_web_request)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Web server running on port {port}")
    return runner

# Bot Functions
def main_menu_keyboard():
    keyboard = [
        ["👤 My Profile", "🎫 ကံစမ်းမဲ ဝယ်ယူရန်"],
        ["🏆 ပြိုင်ပွဲများ ရလဒ်များ", "📊 မှတ်တမ်းကြည့်ရန်"],
        ["💰 ငွေသွင်း", "📤 ငွေထုတ်"],
        ["📢 ကြော်ငြာ အပ်ရန်", "📺 Channel & Group"],
        ["⚙️ Admin", "👥 Referral", "❓ FAQ"],
        ["ℹ️ About Us", "🏠 ပင်မမီနူး"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        user_data = users[user_id]
        await update.message.reply_text(
            f"👋 ပြန်လည်ကြိုဆိုပါတယ် {user_data['full_name']}!",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "မှတ်ပုံတင်ရန် /register ကိုနှိပ်ပါ",
            reply_markup=ReplyKeyboardMarkup([["/register"]], resize_keyboard=True)
        )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        await update.message.reply_text(
            "✅ သင်မှတ်ပုံတင်ပြီးသားဖြစ်ပါသည်!",
            reply_markup=main_menu_keyboard()
        )
        return
        
    context.user_data['register_step'] = 'name'
    await update.message.reply_text("👤 ကျေးဇူးပြု၍ သင့်နာမည်ကိုရိုက်ထည့်ပါ:")

async def handle_register_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'register_step' not in context.user_data:
        return
    
    step = context.user_data['register_step']
    
    if step == 'name':
        context.user_data['full_name'] = update.message.text
        context.user_data['register_step'] = 'phone'
        await update.message.reply_text("📞 ကျေးဇူးပြု၍ သင့်ဖုန်းနံပါတ်ကိုရိုက်ထည့်ပါ:")
    
    elif step == 'phone':
        phone = update.message.text
        full_name = context.user_data['full_name']
        
        user_id = update.effective_user.id
        users[user_id] = {
            'full_name': full_name,
            'phone': phone,
            'balance': 0,
            'registered_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'referral_code': f"REF{user_id}",
            'referrals': [],
            'total_earnings': 0
        }
        
        del context.user_data['register_step']
        del context.user_data['full_name']
        
        await update.message.reply_text(
            f"✅ မှတ်ပုံတင်ပြီးပါပြီ!\n\n"
            f"👤 နာမည်: {full_name}\n"
            f"📞 ဖုန်း: {phone}\n"
            f"🔗 Referral Code: REF{user_id}",
            reply_markup=main_menu_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "/start":
        await start(update, context)
    elif text == "/register":
        await register(update, context)
    elif 'register_step' in context.user_data:
        await handle_register_steps(update, context)
    elif text == "👤 My Profile":
        user_id = update.effective_user.id
        if user_id in users:
            user_data = users[user_id]
            await update.message.reply_text(
                f"👤 **My Profile**\n\n"
                f"**NAME**\n{user_data['full_name']}\n\n"
                f"**PH NO.**\n{user_data['phone']}\n\n"
                f"**Balance**\n{user_data['balance']:,} Ks\n\n"
                f"**Referral Code**\n{user_data['referral_code']}",
                parse_mode='Markdown'
            )
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
        
        # Create bot application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        application.add_handler(CommandHandler("help", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        # Start bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("✅ Bot started successfully on Render!")
        logger.info("📱 Bot is now listening for messages...")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
    finally:
        # Cleanup
        try:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            await web_runner.cleanup()
        except:
            pass

if __name__ == '__main__':
    asyncio.run(main())

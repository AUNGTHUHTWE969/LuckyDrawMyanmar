import os
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import datetime
import random
import asyncio

# Configure logging for Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()  # This ensures logs go to Render's log system
    ]
)
logger = logging.getLogger(__name__)

# Get Bot Token from Environment Variable (for security)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')

# Database (In-memory for demo - in production use PostgreSQL)
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

channels = {
    "transaction_channel": "https://t.me/+C-60JUm8CKVlOTBl",
    "admin_channel": "https://t.me/+_P7OHmGNs8g2MGE1",
    "official_channel": "@official_channel"
}

groups = {}
transactions = {}
transaction_counter = 1

# Helper Functions
def is_admin(user_id):
    return user_id in admins

def get_random_account(payment_method):
    accounts = payment_accounts.get(payment_method, [])
    return random.choice(accounts) if accounts else None

def generate_transaction_id():
    global transaction_counter
    txn_id = f"TXN{transaction_counter:06d}"
    transaction_counter += 1
    return txn_id

def create_transaction(user_id, amount, transaction_type, payment_method, status="pending"):
    txn_id = generate_transaction_id()
    transactions[txn_id] = {
        "id": txn_id,
        "user_id": user_id,
        "user_name": users[user_id]['full_name'],
        "user_phone": users[user_id]['phone'],
        "amount": amount,
        "type": transaction_type,
        "payment_method": payment_method,
        "status": status,
        "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "processed_at": None,
        "processed_by": None
    }
    return txn_id

# Keyboards
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

# Start Command
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

# Register Command
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

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        # Admin handling would go here
        pass
        
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

# Health check endpoint for Render
from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Start a simple web server for health checks"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use Render's PORT environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Health check server running on port {port}")
    return runner

# Main application setup
async def main():
    logger.info("🚀 Starting Telegram Lottery Bot...")
    
    # Start health check server
    web_runner = await start_web_server()
    
    try:
        # Create Telegram Bot Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Start the bot
        logger.info("✅ Bot is starting...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("🤖 Bot is now running on Render!")
        logger.info("📊 Health check available at /health")
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
            
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
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
    # For Render deployment
    asyncio.run(main())

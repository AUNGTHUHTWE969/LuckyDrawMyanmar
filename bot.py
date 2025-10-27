import os
import logging
import random
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify

import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Render
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({"status": "Lucky Draw Bot is running!", "timestamp": datetime.now().isoformat()})

@flask_app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Rest of your existing bot code continues here...
class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '8070878424').split(',')]
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@luckydrawmyanmar')
    ANNOUNCEMENT_CHANNEL = os.getenv('ANNOUNCEMENT_CHANNEL', '@luckydrawmyanmarofficial')
    PAYMENT_LOG_CHANNEL = os.getenv('PAYMENT_LOG_CHANNEL', '-1002141899845')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    DAILY_DRAW_TIME = "18:00"
    MAX_TICKETS_PER_USER = 50
    TICKET_PRICE = 1000
    
    PAYMENT_METHODS = {
        "KPay": {
            "name": os.getenv('KPAY_NAME', 'AUNG THU HTWE'),
            "phone": os.getenv('KPAY_PHONE', '09789999368')
        },
        "WavePay": {
            "name": os.getenv('WAVEPAY_NAME', 'AUNG THU HTWE'),
            "phone": os.getenv('WAVEPAY_PHONE', '09789999368')
        }
    }

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        self.init_database()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            if Config.DATABASE_URL:
                self.connection = psycopg2.connect(Config.DATABASE_URL, sslmode='require')
            else:
                # Fallback to SQLite for local development
                import sqlite3
                self.connection = sqlite3.connect('lottery.db', check_same_thread=False)
            logger.info("✅ Database connected successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def init_database(self):
        """Initialize database tables"""
        try:
            cursor = self.connection.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    balance DECIMAL DEFAULT 0,
                    total_spent DECIMAL DEFAULT 0,
                    total_won DECIMAL DEFAULT 0,
                    tickets_bought INTEGER DEFAULT 0,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Tickets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    amount DECIMAL,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            self.connection.commit()
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.connection.rollback()

    # ... (ကျန်တဲ့ database methods တွေ ဒီမှာထည့်ပါ)

class LotteryBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Create user if not exists
        self.db.create_user(
            user.id,
            user.username,
            user.first_name,
            getattr(user, 'last_name', '')
        )
        
        welcome_text = f"""
🎉 **Lucky Draw Myanmar မှ ကြိုဆိုပါတယ်!**

👋 မင်္ဂလာပါ {user.first_name}!

**ကံစမ်းမဲအချက်အလက်:**
🎫 ကံစမ်းမဲဈေး: {Config.TICKET_PRICE:,} ကျပ်
⏰ ကံစမ်းမဲဖွင့်ချိန်: နေ့စဉ် {Config.DAILY_DRAW_TIME}
💳 ငွေသွင်းနည်း: KPay, WavePay

**အောက်ပါ button များကိုနှိပ်၍ ဆက်လက်လုပ်ဆောင်ပါ**

#LUCKYDRAWMYANMAR
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=self.get_main_menu(user.id)
        )
    
    def get_main_menu(self, user_id: int = None):
        """Get main menu keyboard"""
        is_admin = self.db.is_admin(user_id) if user_id else False
        
        keyboard = [
            [InlineKeyboardButton("🎫 ကံစမ်းမဲဝယ်ယူရန်", callback_data="buy_ticket")],
            [InlineKeyboardButton("💰 လက်ကျန်ငွေကြည့်ရန်", callback_data="check_balance")],
            [InlineKeyboardButton("💳 ငွေသွင်းရန်", callback_data="deposit_money")],
            [InlineKeyboardButton("🏧 ငွေထုတ်ရန်", callback_data="withdraw_money")],
            [InlineKeyboardButton("📊 ကိုယ်ရေးအချက်အလက်", callback_data="profile")]
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
        
        return InlineKeyboardMarkup(keyboard)

    # ... (ကျန်တဲ့ bot methods တွေ ဒီမှာထည့်ပါ)

    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def run_bot(self):
        """Run the bot"""
        if not Config.BOT_TOKEN:
            logger.error("BOT_TOKEN environment variable is required!")
            return
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self.setup_handlers()
        
        logger.info("🤖 Bot is starting...")
        await self.application.run_polling()

# Create bot instance
bot = LotteryBot()

def run_bot():
    """Run the bot in an async context"""
    asyncio.run(bot.run_bot())

if __name__ == "__main__":
    # Start both Flask app and Telegram bot
    import threading
    
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)

import os
import logging
import asyncio
from datetime import datetime
import random

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

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '8070878424').split(',')]
    DATABASE_URL = os.getenv('DATABASE_URL')
    TICKET_PRICE = 1000

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
                logger.info("✅ PostgreSQL database connected successfully")
            else:
                # Fallback to SQLite for local development
                import sqlite3
                self.connection = sqlite3.connect('lottery.db', check_same_thread=False)
                logger.info("✅ SQLite database connected successfully")
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
                    balance DECIMAL DEFAULT 0,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tickets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    amount DECIMAL,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.connection.commit()
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.connection.rollback()
    
    def create_user(self, user_id: int, username: str, first_name: str):
        """Create a new user"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id, username, first_name))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def get_user(self, user_id: int):
        """Get user by ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_balance(self, user_id: int, amount: float):
        """Update user balance"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE users SET balance = balance + %s WHERE user_id = %s",
                (amount, user_id)
            )
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            self.connection.rollback()
            return False

class LotteryBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Create user if not exists
        self.db.create_user(user.id, user.username, user.first_name)
        
        user_data = self.db.get_user(user.id)
        balance = user_data[3] if user_data else 0
        
        welcome_text = f"""
🎉 **Lucky Draw Myanmar မှ ကြိုဆိုပါတယ်!**

👋 မင်္ဂလာပါ {user.first_name}!

**ကံစမ်းမဲအချက်အလက်:**
🎫 ကံစမ်းမဲဈေး: {Config.TICKET_PRICE:,} ကျပ်
💰 သင့်လက်ကျန်ငွေ: {balance:,.0f} ကျပ်

ကျေးဇူးပြု၍ အောက်ပါ button များကိုနှိပ်၍ ဆက်လက်လုပ်ဆောင်ပါ

#LUCKYDRAWMYANMAR
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=self.get_main_menu(user.id)
        )
    
    def get_main_menu(self, user_id: int = None):
        """Get main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🎫 ကံစမ်းမဲဝယ်ယူရန်", callback_data="buy_ticket")],
            [InlineKeyboardButton("💰 လက်ကျန်ငွေကြည့်ရန်", callback_data="check_balance")],
            [InlineKeyboardButton("📊 ကိုယ်ရေးအချက်အလက်", callback_data="profile")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_ticket_menu(self):
        """Get ticket purchase menu"""
        keyboard = [
            [InlineKeyboardButton("1 ကံစမ်းမဲ", callback_data="buy_1")],
            [InlineKeyboardButton("5 ကံစမ်းမဲ", callback_data="buy_5")],
            [InlineKeyboardButton("10 ကံစမ်းမဲ", callback_data="buy_10")],
            [InlineKeyboardButton("🔙 နောက်သို့", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        data = query.data
        
        if data == "main_menu":
            await query.edit_message_text(
                "**မူလ Menu**\n\nကျေးဇူးပြု၍ ရွေးချယ်ပါ:",
                parse_mode='Markdown',
                reply_markup=self.get_main_menu(user.id)
            )
        
        elif data == "buy_ticket":
            await query.edit_message_text(
                f"**ကံစမ်းမဲဝယ်ယူရန်**\n\n🎫 ကံစမ်းမဲတစ်ခုလျှင်: {Config.TICKET_PRICE:,} ကျပ်",
                parse_mode='Markdown',
                reply_markup=self.get_ticket_menu()
            )
        
        elif data == "check_balance":
            user_data = self.db.get_user(user.id)
            balance = user_data[3] if user_data else 0
            
            await query.edit_message_text(
                f"💰 **သင့်လက်ကျန်ငွေ**\n\nလက်ကျန်ငွေ: {balance:,.0f} ကျပ်",
                parse_mode='Markdown',
                reply_markup=self.get_main_menu(user.id)
            )
        
        elif data == "profile":
            user_data = self.db.get_user(user.id)
            if user_data:
                profile_text = f"""
📊 **ကိုယ်ရေးအချက်အလက်**

👤 အမည်: {user_data[2]}
🆔 အိုင်ဒီ: {user_data[0]}
💰 လက်ကျန်ငွေ: {user_data[3]:,.0f} ကျပ်
📅 အကောင့်ဖွင့်သည့်ရက်: {user_data[4][:10] if user_data[4] else 'N/A'}

#LUCKYDRAWMYANMAR
                """
                
                await query.edit_message_text(
                    profile_text,
                    parse_mode='Markdown',
                    reply_markup=self.get_main_menu(user.id)
                )
        
        elif data.startswith("buy_"):
            if data == "buy_1":
                ticket_count = 1
            elif data == "buy_5":
                ticket_count = 5
            elif data == "buy_10":
                ticket_count = 10
            else:
                ticket_count = 1
            
            await self.process_ticket_purchase(user, ticket_count, query)
    
    async def process_ticket_purchase(self, user, ticket_count: int, query):
        """Process ticket purchase"""
        try:
            total_amount = ticket_count * Config.TICKET_PRICE
            user_data = self.db.get_user(user.id)
            
            if not user_data:
                await query.edit_message_text(
                    "❌ User information not found. Please start the bot again.",
                    reply_markup=self.get_main_menu(user.id)
                )
                return
            
            balance = user_data[3]
            
            if balance < total_amount:
                await query.edit_message_text(
                    f"❌ လက်ကျန်ငွေမလုံလောက်ပါ။\nလက်ရှိလက်ကျန်ငွေ: {balance:,.0f} ကျပ်\nလိုအပ်ငွေ: {total_amount:,.0f} ကျပ်",
                    reply_markup=self.get_main_menu(user.id)
                )
                return
            
            # Update balance
            self.db.update_balance(user.id, -total_amount)
            
            # Create ticket records
            cursor = self.db.connection.cursor()
            for _ in range(ticket_count):
                cursor.execute(
                    "INSERT INTO tickets (user_id, amount) VALUES (%s, %s)",
                    (user.id, Config.TICKET_PRICE)
                )
            
            self.db.connection.commit()
            
            # Get updated balance
            user_data = self.db.get_user(user.id)
            new_balance = user_data[3]
            
            success_message = f"""
✅ ကံစမ်းမဲ {ticket_count} ခု ဝယ်ယူပြီးပါပြီ!

📊 အချက်အလက်များ:
• ဝယ်ယူသောကံစမ်းမဲ: {ticket_count} ခု
• ကံစမ်းမဲတစ်ခုဈေး: {Config.TICKET_PRICE:,} ကျပ်
• စုစုပေါင်းကျသင့်ငွေ: {total_amount:,.0f} ကျပ်
• လက်ကျန်ငွေ: {new_balance:,.0f} ကျပ်

🎊 ကံကောင်းပါစေ!

#LUCKYDRAWMYANMAR
            """
            
            await query.edit_message_text(
                success_message,
                parse_mode='Markdown',
                reply_markup=self.get_main_menu(user.id)
            )
            
        except Exception as e:
            logger.error(f"Error processing ticket purchase: {e}")
            await query.edit_message_text(
                "❌ ကံစမ်းမဲဝယ်ယူရာတွင် အမှားဖြစ်နေသည်",
                reply_markup=self.get_main_menu(user.id)
            )
    
    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def run(self):
        """Run the bot"""
        if not Config.BOT_TOKEN:
            logger.error("BOT_TOKEN environment variable is required!")
            return
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self.setup_handlers()
        
        logger.info("🤖 Bot is starting...")
        await self.application.run_polling()

async def main():
    """Main function"""
    bot = LotteryBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())

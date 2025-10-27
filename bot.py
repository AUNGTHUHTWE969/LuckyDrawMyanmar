import os
import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
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
            
            # Transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    type TEXT,
                    amount DECIMAL,
                    description TEXT,
                    status TEXT DEFAULT 'completed',
                    transaction_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Payment requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    first_name TEXT,
                    amount DECIMAL,
                    payment_method TEXT,
                    transaction_proof TEXT,
                    status TEXT DEFAULT 'pending',
                    admin_id BIGINT,
                    admin_note TEXT,
                    transaction_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Withdrawal requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    username TEXT,
                    first_name TEXT,
                    amount DECIMAL,
                    payment_method TEXT,
                    account_info TEXT,
                    status TEXT DEFAULT 'pending',
                    admin_id BIGINT,
                    admin_note TEXT,
                    transaction_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            self.connection.commit()
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            self.connection.rollback()
    
    def create_user(self, user_id: int, username: str, first_name: str, last_name: str = "", phone: str = ""):
        """Create a new user"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, phone)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id, username, first_name, last_name, phone))
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
            
            if amount > 0:
                cursor.execute(
                    "UPDATE users SET total_won = total_won + %s WHERE user_id = %s",
                    (amount, user_id)
                )
            
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            self.connection.rollback()
            return False
    
    def record_transaction(self, user_id: int, transaction_type: str, amount: float, description: str, status: str = 'completed', transaction_id: str = None):
        """Record a transaction"""
        try:
            if not transaction_id:
                transaction_id = f"TX{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, description, status, transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user_id, transaction_type, amount, description, status, transaction_id))
            
            self.connection.commit()
            return transaction_id
        except Exception as e:
            logger.error(f"Error recording transaction: {e}")
            self.connection.rollback()
            return None
    
    def create_payment_request(self, user_id: int, username: str, first_name: str, amount: float, payment_method: str, transaction_proof: str = None):
        """Create payment request"""
        try:
            transaction_id = f"DEP{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO payment_requests 
                (user_id, username, first_name, amount, payment_method, transaction_proof, transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (user_id, username, first_name, amount, payment_method, transaction_proof, transaction_id))
            
            request_id = cursor.fetchone()[0]
            self.connection.commit()
            return request_id, transaction_id
        except Exception as e:
            logger.error(f"Error creating payment request: {e}")
            self.connection.rollback()
            return None, None
    
    def create_withdrawal_request(self, user_id: int, username: str, first_name: str, amount: float, payment_method: str, account_info: str):
        """Create withdrawal request"""
        try:
            transaction_id = f"WD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO withdrawal_requests 
                (user_id, username, first_name, amount, payment_method, account_info, transaction_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (user_id, username, first_name, amount, payment_method, account_info, transaction_id))
            
            request_id = cursor.fetchone()[0]
            self.connection.commit()
            return request_id, transaction_id
        except Exception as e:
            logger.error(f"Error creating withdrawal request: {e}")
            self.connection.rollback()
            return None, None
    
    def is_admin(self, user_id: int):
        """Check if user is admin"""
        return user_id in Config.ADMIN_IDS

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
    
    def get_ticket_menu(self):
        """Get ticket purchase menu"""
        keyboard = [
            [InlineKeyboardButton("1 ကံစမ်းမဲ", callback_data="buy_1")],
            [InlineKeyboardButton("5 ကံစမ်းမဲ", callback_data="buy_5")],
            [InlineKeyboardButton("10 ကံစမ်းမဲ", callback_data="buy_10")],
            [InlineKeyboardButton("🔙 နောက်သို့", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_deposit_menu(self):
        """Get deposit menu"""
        keyboard = [
            [InlineKeyboardButton("📱 KPay ဖြင့်ငွေသွင်းရန်", callback_data="deposit_kpay")],
            [InlineKeyboardButton("📱 WavePay ဖြင့်ငွေသွင်းရန်", callback_data="deposit_wavepay")],
            [InlineKeyboardButton("🔙 နောက်သို့", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_withdrawal_menu(self):
        """Get withdrawal menu"""
        keyboard = [
            [InlineKeyboardButton("📱 KPay ဖြင့်ငွေထုတ်ရန်", callback_data="withdraw_kpay")],
            [InlineKeyboardButton("📱 WavePay ဖြင့်ငွေထုတ်ရန်", callback_data="withdraw_wavepay")],
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
            balance = user_data[5] if user_data else 0
            
            await query.edit_message_text(
                f"💰 **သင့်လက်ကျန်ငွေ**\n\nလက်ကျန်ငွေ: {balance:,.0f} ကျပ်",
                parse_mode='Markdown',
                reply_markup=self.get_main_menu(user.id)
            )
        
        elif data == "deposit_money":
            await query.edit_message_text(
                "💳 **ငွေသွင်းရန်**\n\nကျေးဇူးပြု၍ ငွေသွင်းလိုသော နည်းလမ်းကိုရွေးချယ်ပါ:",
                parse_mode='Markdown',
                reply_markup=self.get_deposit_menu()
            )
        
        elif data == "withdraw_money":
            await query.edit_message_text(
                "🏧 **ငွေထုတ်ရန်**\n\nကျေးဇူးပြု၍ ငွေထုတ်လိုသော နည်းလမ်းကိုရွေးချယ်ပါ:",
                parse_mode='Markdown',
                reply_markup=self.get_withdrawal_menu()
            )
        
        elif data == "profile":
            user_data = self.db.get_user(user.id)
            if user_data:
                profile_text = f"""
📊 **ကိုယ်ရေးအချက်အလက်**

👤 အမည်: {user_data[2]} {user_data[3]}
🆔 အိုင်ဒီ: {user_data[0]}
📞 ဖုန်း: {user_data[4] or 'မှတ်ပုံတင်မထားရှိ'}
💰 လက်ကျန်ငွေ: {user_data[5]:,.0f} ကျပ်
🎫 ဝယ်ယူပြီးကံစမ်းမဲ: {user_data[8]} ခု
📅 အကောင့်ဖွင့်သည့်ရက်: {user_data[9][:10] if user_data[9] else 'N/A'}

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
        
        elif data.startswith("deposit_"):
            method = "KPay" if data == "deposit_kpay" else "WavePay"
            context.user_data['deposit_method'] = method
            context.user_data['awaiting_deposit_amount'] = True
            
            payment_info = Config.PAYMENT_METHODS[method]
            
            await query.edit_message_text(
                f"""
📱 **{method} ဖြင့်ငွေသွင်းရန်**

💳 **ငွေသွင်းရန်အချက်အလက်:**
• **အမည်:** {payment_info['name']}
• **ဖုန်းနံပါတ်:** {payment_info['phone']}

ကျေးဇူးပြု၍ သွင်းလိုသောငွေပမာဏကို ရိုက်ထည့်ပါ:
ဥပမာ: `10000`

#LUCKYDRAWMYANMAR
                """,
                parse_mode='Markdown'
            )
        
        elif data.startswith("withdraw_"):
            method = "KPay" if data == "withdraw_kpay" else "WavePay"
            context.user_data['withdrawal_method'] = method
            context.user_data['awaiting_withdrawal_amount'] = True
            
            await query.edit_message_text(
                f"""
🏧 **{method} ဖြင့်ငွေထုတ်ရန်**

ကျေးဇူးပြု၍ ထုတ်လိုသောငွေပမာဏကို ရိုက်ထည့်ပါ:
ဥပမာ: `5000`

**မှတ်ချက်:** အနည်းဆုံးထုတ်ယူနိုင်သောပမာဏ - 1,000 ကျပ်

#LUCKYDRAWMYANMAR
                """,
                parse_mode='Markdown'
            )
    
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
            
            balance = user_data[5]
            
            if balance < total_amount:
                await query.edit_message_text(
                    f"❌ လက်ကျန်ငွေမလုံလောက်ပါ။\nလက်ရှိလက်ကျန်ငွေ: {balance:,.0f} ကျပ်\nလိုအပ်ငွေ: {total_amount:,.0f} ကျပ်",
                    reply_markup=self.get_main_menu(user.id)
                )
                return
            
            # Update balance
            self.db.update_balance(user.id, -total_amount)
            
            # Record transaction
            transaction_id = self.db.record_transaction(
                user.id, 'ticket_purchase', -total_amount,
                f'Purchased {ticket_count} tickets'
            )
            
            # Update user stats
            cursor = self.db.connection.cursor()
            cursor.execute(
                "UPDATE users SET total_spent = total_spent + %s, tickets_bought = tickets_bought + %s WHERE user_id = %s",
                (total_amount, ticket_count, user.id)
            )
            
            # Create ticket records
            for _ in range(ticket_count):
                cursor.execute(
                    "INSERT INTO tickets (user_id, username, amount) VALUES (%s, %s, %s)",
                    (user.id, user.username, Config.TICKET_PRICE)
                )
            
            self.db.connection.commit()
            
            # Get updated balance
            user_data = self.db.get_user(user.id)
            new_balance = user_data[5]
            
            success_message = f"""
✅ ကံစမ်းမဲ {ticket_count} ခု ဝယ်ယူပြီးပါပြီ!

📊 အချက်အလက်များ:
• ဝယ်ယူသောကံစမ်းမဲ: {ticket_count} ခု
• ကံစမ်းမဲတစ်ခုဈေး: {Config.TICKET_PRICE:,} ကျပ်
• စုစုပေါင်းကျသင့်ငွေ: {total_amount:,.0f} ကျပ်
• လက်ကျန်ငွေ: {new_balance:,.0f} ကျပ်
• လုပ်ဆောင်မှုအမှတ်: `{transaction_id}`

⏰ ကံစမ်းမဲဖွင့်ချိန်: {Config.DAILY_DRAW_TIME}
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
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user = update.effective_user
        message_text = update.message.text.strip()
        
        # Handle deposit amount
        if context.user_data.get('awaiting_deposit_amount'):
            try:
                amount = float(message_text)
                if amount < 1000:
                    await update.message.reply_text("❌ အနည်းဆုံးငွေသွင်းပမာဏ 1,000 ကျပ်ဖြစ်ပါသည်")
                    return
                
                method = context.user_data['deposit_method']
                payment_info = Config.PAYMENT_METHODS[method]
                
                # Create payment request
                request_id, transaction_id = self.db.create_payment_request(
                    user.id, user.username, user.first_name, amount, method
                )
                
                if request_id:
                    deposit_message = f"""
✅ **သင့်ငွေသွင်းခွင့်ပြုချက် တင်သွင်းပြီးပါပြီ**

💰 **ပမာဏ:** {amount:,.0f} ကျပ်
📱 **ငွေသွင်းနည်း:** {method}
💳 **ငွေသွင်းအချက်အလက်:**
   • အမည်: {payment_info['name']}
   • ဖုန်းနံပါတ်: {payment_info['phone']}
🆔 **Request ID:** #{request_id}
📊 **လုပ်ဆောင်မှုအမှတ်:** `{transaction_id}`

📝 Admin မှအတည်ပြုပြီးနောက် သင့်အကောင့်သို့ငွေထည့်သွင်းပေးပါမည်။
ကျေးဇူးပြု၍ စောင့်ဆိုင်းပေးပါ။

#LUCKYDRAWMYANMAR
                    """
                    
                    await update.message.reply_text(
                        deposit_message,
                        parse_mode='Markdown',
                        reply_markup=self.get_main_menu(user.id)
                    )
                    
                    # Notify admins
                    await self.notify_admins(
                        f"💸 **ငွေသွင်းခွင့်ပြုချက်တောင်းခံခြင်း**\n\n"
                        f"👤 User: {user.first_name} (@{user.username})\n"
                        f"💰 ပမာဏ: {amount:,.0f} ကျပ်\n"
                        f"📱 ငွေသွင်းနည်း: {method}\n"
                        f"🆔 Request ID: #{request_id}"
                    )
                else:
                    await update.message.reply_text("❌ ငွေသွင်းခွင့်ပြုချက်တင်သွင်းရာတွင် အမှားဖြစ်နေသည်")
                
                # Clean up
                context.user_data.pop('awaiting_deposit_amount', None)
                context.user_data.pop('deposit_method', None)
                
            except ValueError:
                await update.message.reply_text("❌ မှားယွင်းသောငွေပမာဏဖြစ်နေသည်")
        
        # Handle withdrawal amount
        elif context.user_data.get('awaiting_withdrawal_amount'):
            try:
                amount = float(message_text)
                if amount < 1000:
                    await update.message.reply_text("❌ အနည်းဆုံးငွေထုတ်ပမာဏ 1,000 ကျပ်ဖြစ်ပါသည်")
                    return
                
                user_data = self.db.get_user(user.id)
                if user_data[5] < amount:
                    await update.message.reply_text(f"❌ လက်ကျန်ငွေမလုံလောက်ပါ\nလက်ရှိလက်ကျန်ငွေ: {user_data[5]:,.0f} ကျပ်")
                    return
                
                method = context.user_data['withdrawal_method']
                
                # Ask for account info
                context.user_data['withdrawal_amount'] = amount
                context.user_data['awaiting_account_info'] = True
                
                await update.message.reply_text(
                    f"🏧 **ငွေထုတ်အချက်အလက်များ**\n\n"
                    f"💰 **ပမာဏ:** {amount:,.0f} ကျပ်\n"
                    f"📱 **ငွေထုတ်နည်း:** {method}\n\n"
                    f"ကျေးဇူးပြု၍ အကောင့်အချက်အလက်ကိုရိုက်ထည့်ပါ:\n"
                    f"ဥပမာ - {method}: `09789999368`\n\n"
                    f"#LUCKYDRAWMYANMAR",
                    parse_mode='Markdown'
                )
                
            except ValueError:
                await update.message.reply_text("❌ မှားယွင်းသောငွေပမာဏဖြစ်နေသည်")
        
        # Handle account info for withdrawal
        elif context.user_data.get('awaiting_account_info'):
            account_info = message_text
            amount = context.user_data['withdrawal_amount']
            method = context.user_data['withdrawal_method']
            
            # Create withdrawal request
            request_id, transaction_id = self.db.create_withdrawal_request(
                user.id, user.username, user.first_name, amount, method, account_info
            )
            
            if request_id:
                # Deduct balance immediately
                self.db.update_balance(user.id, -amount)
                
                withdrawal_message = f"""
✅ **သင့်ငွေထုတ်ခွင့်ပြုချက် တင်သွင်းပြီးပါပြီ**

💰 **ပမာဏ:** {amount:,.0f} ကျပ်
📱 **ငွေထုတ်နည်း:** {method}
📋 **အကောင့်အချက်အလက်:** {account_info}
🆔 **Request ID:** #{request_id}
📊 **လုပ်ဆောင်မှုအမှတ်:** `{transaction_id}`

📝 Admin မှအတည်ပြုပြီးနောက် သင့်အကောင့်သို့ငွေထုတ်ပေးပါမည်။
ကျေးဇူးပြု၍ စောင့်ဆိုင်းပေးပါ။

#LUCKYDRAWMYANMAR
                """
                
                await update.message.reply_text(
                    withdrawal_message,
                    parse_mode='Markdown',
                    reply_markup=self.get_main_menu(user.id)
                )
                
                # Notify admins
                await self.notify_admins(
                    f"🏧 **ငွေထုတ်ခွင့်ပြုချက်တောင်းခံခြင်း**\n\n"
                    f"👤 User: {user.first_name} (@{user.username})\n"
                    f"💰 ပမာဏ: {amount:,.0f} ကျပ်\n"
                    f"📱 ငွေထုတ်နည်း: {method}\n"
                    f"📋 အကောင့်အချက်အလက်: {account_info}\n"
                    f"🆔 Request ID: #{request_id}"
                )
            else:
                await update.message.reply_text("❌ ငွေထုတ်ခွင့်ပြုချက်တင်သွင်းရာတွင် အမှားဖြစ်နေသည်")
            
            # Clean up
            context.user_data.pop('awaiting_account_info', None)
            context.user_data.pop('withdrawal_amount', None)
            context.user_data.pop('withdrawal_method', None)
        
        else:
            # Default response
            await update.message.reply_text(
                "မူလ Menu သို့ပြန်လာပါပြီ။ ကျေးဇူးပြု၍ ရွေးချယ်ပါ:",
                reply_markup=self.get_main_menu(user.id)
            )
    
    async def notify_admins(self, message: str):
        """Notify all admins"""
        for admin_id in Config.ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
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

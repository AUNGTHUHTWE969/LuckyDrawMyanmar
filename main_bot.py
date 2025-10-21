import os
import random
import schedule
import time
import threading
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext, Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import error as telegram_error
import sqlite3
import asyncio
import logging
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration Settings
class Config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8444084929:AAGhso9BSTUkKj8jmrEhKSHmIzg6BvUoYrk")
    ADMIN_IDS = [8070878424]
    ADMIN_USERNAME = "@luckydrawmyanmar"
    ANNOUNCEMENT_CHANNEL = "@luckydrawmyanmarofficial"
    PAYMENT_LOG_CHANNEL = "-1002141899845"
    DAILY_DRAW_TIME = "18:00"
    MAX_TICKETS_PER_USER = 50
    COMMISSION_RATE = 0.20
    DONATION_RATE = 0.05
    PAYMENT_METHODS = ["KPay", "WavePay"]
    
    PAYMENT_DETAILS = {
        "KPay": {
            "name": "AUNG THU HTWE",
            "phone": "09789999368"
        },
        "WavePay": {
            "name": "AUNG THU HTWE", 
            "phone": "09789999368"
        }
    }

class DatabaseManager:
    def __init__(self):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.connection = sqlite3.connect('lottery.db', check_same_thread=False, timeout=30)
                self.connection.execute("PRAGMA journal_mode=WAL")
                self.create_tables()
                self.create_settings_table()
                self.create_faq_table()
                self.create_draw_settings_table()
                self.create_indexes()
                logger.info("✅ Database connected successfully")
                break
            except Exception as e:
                logger.error(f"❌ Database connection failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
    
    def create_tables(self):
        cursor = self.connection.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                balance REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                tickets_bought INTEGER DEFAULT 0,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                amount REAL,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Winners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                win_date TEXT,
                ticket_id TEXT,
                prize_type TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'paid',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Payment requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                amount REAL,
                payment_method TEXT,
                transaction_proof TEXT,
                status TEXT DEFAULT 'pending',
                admin_id INTEGER,
                admin_note TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Withdrawal requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                amount REAL,
                payment_method TEXT,
                account_info TEXT,
                status TEXT DEFAULT 'pending',
                admin_id INTEGER,
                admin_note TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.connection.commit()
        logger.info("✅ Database tables created successfully")

    def create_draw_settings_table(self):
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS draw_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draw_time TEXT DEFAULT '18:00',
                    is_active BOOLEAN DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default draw time if not exists
            cursor.execute('INSERT OR IGNORE INTO draw_settings (draw_time, is_active) VALUES (?, ?)', 
                         (Config.DAILY_DRAW_TIME, 1))
            
            self.connection.commit()
            logger.info("✅ Draw settings table created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating draw settings table: {e}")

    def create_settings_table(self):
        cursor = self.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        default_settings = [
            ('ticket_price', '1000'),
            ('draw_mode', 'auto'),
            ('draw_time', '18:00'),
            ('auto_draw_enabled', 'true'),
            ('prize_structure', '{"first_prize": 0.5, "second_prize": 0.3, "third_prize": 0.15, "consolation": 0.05}'),
            ('announcement_channel', '@luckydrawmyanmarofficial'),
            ('payment_log_group', '-1002141899845'),
            ('admin_usernames', '{}'),
            ('admin_ids', '["8070878424"]')
        ]
        
        for key, value in default_settings:
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        
        self.connection.commit()
        logger.info("✅ Settings table initialized")

    def create_faq_table(self):
        cursor = self.connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                answer TEXT,
                display_order INTEGER,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        default_faq = [
            ("အကောင့်ဖွင့်နည်း / Register လုပ်နည်း", "Bot ကို Start လိုက်တာနဲ့ အလိုအလျောက် အကောင့်ဖွင့်ပေးပါတယ်။ ထပ်မံလုပ်ဆောင်စရာမလိုပါ။", 1),
            ("ကံစမ်းမဲ ဝယ်ယူနည်း", "မူလ Menu မှ '🎫 ကံစမ်းမဲဝယ်ယူရန်' ကိုနှိပ်ပါ။ ကံစမ်းမဲအရေအတွက်ရွေးချယ်၍ ဝယ်ယူနိုင်ပါသည်။", 2),
            ("ငွေသွင်းနည်း / ငွေထုတ်နည်း", "မူလ Menu မှ '💳 ငွေသွင်းနည်း' ကိုနှိပ်ပါ။ KPay သို့မဟုတ် WavePay ဖြင့် ငွေသွင်းနိုင်ပါသည်။", 3),
            ("အကူအညီ", "အကူအညီလိုအပ်ပါက Admin များနှင့်ဆက်သွယ်ပါ။", 4)
        ]
        
        for question, answer, order in default_faq:
            cursor.execute('''
                INSERT OR IGNORE INTO faq_items (question, answer, display_order) 
                VALUES (?, ?, ?)
            ''', (question, answer, order))
        
        self.connection.commit()
        logger.info("✅ FAQ table created with default items")

    def create_indexes(self):
        cursor = self.connection.cursor()
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_user_date ON tickets(user_id, purchase_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_date ON winners(win_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_date ON tickets(purchase_date)')
            self.connection.commit()
            logger.info("✅ Database indexes created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating indexes: {e}")

    def get_setting(self, key, default=None):
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else default
        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return default

    def update_setting(self, key, value):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at) 
                VALUES (?, ?, datetime('now'))
            ''', (key, value))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating setting: {e}")
            return False

    def is_admin(self, user_id):
        return user_id in Config.ADMIN_IDS

    # Draw time management
    def get_draw_time(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT draw_time FROM draw_settings WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # Fallback
            cursor.execute('SELECT draw_time FROM draw_settings LIMIT 1')
            result = cursor.fetchone()
            return result[0] if result else Config.DAILY_DRAW_TIME
        except Exception as e:
            logger.error(f"Error getting draw time: {e}")
            return Config.DAILY_DRAW_TIME

    def update_draw_time(self, draw_time):
        try:
            cursor = self.connection.cursor()
            cursor.execute('UPDATE draw_settings SET is_active = 0')
            cursor.execute('INSERT INTO draw_settings (draw_time, is_active) VALUES (?, 1)', (draw_time,))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating draw time: {e}")
            return False

    # User Management
    def create_user(self, user_id, username, first_name, last_name="", phone=""):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, phone, join_date, last_active) 
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (user_id, username, first_name, last_name, phone))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    def get_user(self, user_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
            return None

    def update_user_activity(self, user_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('UPDATE users SET last_active = datetime("now") WHERE user_id = ?', (user_id,))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")

    def get_all_users(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT user_id FROM users WHERE status = "active"')
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    # Payment Request Methods
    def create_payment_request(self, user_id, username, first_name, amount, payment_method, transaction_proof=None):
        try:
            transaction_id = f"DEP{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO payment_requests 
                (user_id, username, first_name, amount, payment_method, transaction_proof, status, transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            ''', (user_id, username, first_name, amount, payment_method, transaction_proof, transaction_id))
            self.connection.commit()
            return cursor.lastrowid, transaction_id
        except Exception as e:
            logger.error(f"Error creating payment request: {e}")
            return None, None

    def get_pending_payment_requests(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM payment_requests 
                WHERE status = 'pending' 
                ORDER BY created_at DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending payment requests: {e}")
            return []

    def update_payment_request_status(self, request_id, status, admin_id=None, admin_note=None):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE payment_requests 
                SET status = ?, admin_id = ?, admin_note = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (status, admin_id, admin_note, request_id))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating payment request status: {e}")
            return False

    def get_payment_request(self, request_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM payment_requests WHERE id = ?', (request_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting payment request: {e}")
            return None

    def get_user_payment_requests(self, user_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM payment_requests 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user payment requests: {e}")
            return []

    # Withdrawal Request Methods
    def create_withdrawal_request(self, user_id, username, first_name, amount, payment_method, account_info):
        try:
            transaction_id = f"WD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO withdrawal_requests 
                (user_id, username, first_name, amount, payment_method, account_info, status, transaction_id)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            ''', (user_id, username, first_name, amount, payment_method, account_info, transaction_id))
            self.connection.commit()
            return cursor.lastrowid, transaction_id
        except Exception as e:
            logger.error(f"Error creating withdrawal request: {e}")
            return None, None

    def get_pending_withdrawal_requests(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM withdrawal_requests 
                WHERE status = 'pending' 
                ORDER BY created_at DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting pending withdrawal requests: {e}")
            return []

    def update_withdrawal_request_status(self, request_id, status, admin_id=None, admin_note=None):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE withdrawal_requests 
                SET status = ?, admin_id = ?, admin_note = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (status, admin_id, admin_note, request_id))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating withdrawal request status: {e}")
            return False

    def get_withdrawal_request(self, request_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM withdrawal_requests WHERE id = ?', (request_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting withdrawal request: {e}")
            return None

    def get_user_withdrawal_requests(self, user_id):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM withdrawal_requests 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user withdrawal requests: {e}")
            return []

    # Balance and Transaction Methods
    def update_balance(self, user_id, amount):
        try:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            
            if amount > 0:
                cursor.execute("UPDATE users SET total_won = total_won + ? WHERE user_id = ?", (amount, user_id))
            
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return False

    def record_transaction(self, user_id, type, amount, description, status='completed', transaction_id=None):
        try:
            if not transaction_id:
                transaction_id = f"TX{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
            
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, description, status, transaction_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, type, amount, description, status, transaction_id))
            self.connection.commit()
            return transaction_id
        except Exception as e:
            logger.error(f"Error recording transaction: {e}")
            return None

    def get_faq_items(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT id, question, answer, display_order 
                FROM faq_items 
                WHERE is_active = 1 
                ORDER BY display_order ASC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting FAQ items: {e}")
            return []

    def get_today_ticket_buyers(self, date):
        try:
            cursor = self.connection.cursor()
            query = "SELECT DISTINCT user_id, username, first_name FROM tickets WHERE DATE(purchase_date) = ? AND status = 'active'"
            cursor.execute(query, (date,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting ticket buyers: {e}")
            return []

    def get_daily_ticket_sales(self, date):
        try:
            cursor = self.connection.cursor()
            query = "SELECT SUM(amount) FROM tickets WHERE DATE(purchase_date) = ? AND status = 'active'"
            cursor.execute(query, (date,))
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except Exception as e:
            logger.error(f"Error getting daily sales: {e}")
            return 0

    def record_winner(self, user_id, amount, date, ticket_id, prize_type='normal'):
        try:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO winners (user_id, amount, win_date, ticket_id, prize_type, status) VALUES (?, ?, ?, ?, ?, 'paid')", 
                         (user_id, amount, date, ticket_id, prize_type))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error recording winner: {e}")
            return False

class LotterySystem:
    def __init__(self, db_manager, application):
        self.db = db_manager
        self.application = application
        self.setup_daily_draw()

    def setup_daily_draw(self):
        auto_enabled = self.db.get_setting('auto_draw_enabled', 'true')
        if auto_enabled.lower() == 'true':
            draw_time = self.db.get_draw_time()
            try:
                schedule.every().day.at(draw_time).do(self.run_daily_draw)
                
                def run_scheduler():
                    while True:
                        schedule.run_pending()
                        time.sleep(1)
                
                scheduler_thread = threading.Thread(target=run_scheduler)
                scheduler_thread.daemon = True
                scheduler_thread.start()
                logger.info(f"✅ Auto draw scheduler started at {draw_time}")
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
        else:
            logger.info("❌ Auto draw is disabled")

    async def send_live_payment_update(self, user_id, username, first_name, amount, transaction_type, transaction_id=None):
        try:
            if transaction_type == "deposit":
                emoji = "💳"
                action = "ငွေသွင်း"
            elif transaction_type == "withdrawal":
                emoji = "🏧"
                action = "ငွေထုတ်"
            elif transaction_type == "ticket_purchase":
                emoji = "🎫"
                action = "ကံစမ်းမဲဝယ်ယူ"
            else:
                emoji = "🏆"
                action = "ဆုကြေးရရှိ"
            
            transaction_info = f"\n🆔 **လုပ်ဆောင်မှုအမှတ်:** `{transaction_id}`" if transaction_id else ""
            
            live_message = f"""
{emoji} **LIVE PAYMENT UPDATE** {emoji}

👤 **User:** {first_name} (@{username or 'No Username'})
🆔 **User ID:** `{user_id}`
💰 **Amount:** {amount:,.0f} ကျပ်
📊 **Type:** {action}
⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{transaction_info}

🎯 **Real-time Transaction**

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
            """
            
            await self.application.bot.send_message(
                chat_id=Config.PAYMENT_LOG_CHANNEL,
                text=live_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ Error sending live payment update: {e}")

    async def notify_admins(self, message, reply_markup=None):
        for admin_id in Config.ADMIN_IDS:
            try:
                if reply_markup:
                    await self.application.bot.send_message(admin_id, message, parse_mode='Markdown', reply_markup=reply_markup)
                else:
                    await self.application.bot.send_message(admin_id, message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Admin notification error for {admin_id}: {e}")

    # Payment Request Methods
    async def create_payment_request(self, user_id, username, first_name, amount, payment_method, transaction_proof=None):
        request_id, transaction_id = self.db.create_payment_request(user_id, username, first_name, amount, payment_method, transaction_proof)
        if request_id:
            admin_message = f"""
💸 **ငွေသွင်းခွင့်ပြုချက်တောင်းခံခြင်း**

👤 User: {first_name} (@{username})
🆔 User ID: `{user_id}`
💰 ပမာဏ: {amount:,.0f} ကျပ်
📱 ငွေသွင်းနည်း: {payment_method}
🆔 Request ID: #{request_id}
📊 လုပ်ဆောင်မှုအမှတ်: `{transaction_id}`

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ အတည်ပြုရန်", callback_data=f"approve_payment_{request_id}"),
                    InlineKeyboardButton("❌ ငြင်းပယ်ရန်", callback_data=f"reject_payment_{request_id}"),
                    InlineKeyboardButton("⏸️ ဆိုင်းငံ့ထား", callback_data=f"hold_payment_{request_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.notify_admins(admin_message, reply_markup)
            return request_id, transaction_id
        return None, None

    async def approve_payment_request(self, request_id, admin_id, admin_note=None):
        request = self.db.get_payment_request(request_id)
        if not request:
            return False, "Request not found"
        
        if request[7] != 'pending':
            return False, "Request already processed"
        
        success = self.db.update_balance(request[1], request[4])
        if success:
            self.db.update_payment_request_status(request_id, 'approved', admin_id, admin_note)
            
            transaction_id = self.db.record_transaction(
                request[1], 'deposit', request[4], 
                f'Payment request approved - {request[10]}', 'completed', request[10]
            )
            
            try:
                await self.application.bot.send_message(
                    request[1],
                    f"""
✅ **သင့်ငွေသွင်းမှု အောင်မြင်ပါသည်**

💰 **ပမာဏ:** {request[4]:,.0f} ကျပ်
📱 **ငွေသွင်းနည်း:** {request[5]}
🆔 **Request ID:** #{request_id}
📊 **လုပ်ဆောင်မှုအမှတ်:** `{request[10]}`
📅 **အတည်ပြုသည့်အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💎 **လက်ရှိလက်ကျန်ငွေ:** {self.db.get_user(request[1])[5]:,.0f} ကျပ်

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                    """
                )
            except Exception as e:
                logger.error(f"Error notifying user: {e}")
            
            await self.send_live_payment_update(
                request[1], request[2], request[3], request[4], "deposit", request[10]
            )
            
            return True, "Payment approved successfully"
        return False, "Error updating balance"

    async def reject_payment_request(self, request_id, admin_id, admin_note=None):
        request = self.db.get_payment_request(request_id)
        if not request:
            return False, "Request not found"
        
        if request[7] != 'pending':
            return False, "Request already processed"
        
        self.db.update_payment_request_status(request_id, 'rejected', admin_id, admin_note)
        
        try:
            await self.application.bot.send_message(
                request[1],
                f"""
❌ **သင့်ငွေသွင်းမှု ငြင်းပယ်ခံရသည်**

💰 **ပမာဏ:** {request[4]:,.0f} ကျပ်
📱 **ငွေသွင်းနည်း:** {request[5]}
🆔 **Request ID:** #{request_id}
📊 **လုပ်ဆောင်မှုအမှတ်:** `{request[10]}`
📅 **ငြင်းပယ်သည့်အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📝 **အကြောင်းပြချက်:** {admin_note or 'အကြောင်းပြချက်မရှိပါ'}

ကျေးဇူးပြု၍ Admin နှင့်ဆက်သွယ်ပါ။

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                """
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        return True, "Payment rejected successfully"

    async def hold_payment_request(self, request_id, admin_id, admin_note=None):
        request = self.db.get_payment_request(request_id)
        if not request:
            return False, "Request not found"
        
        if request[7] != 'pending':
            return False, "Request already processed"
        
        self.db.update_payment_request_status(request_id, 'on_hold', admin_id, admin_note)
        
        try:
            await self.application.bot.send_message(
                request[1],
                f"""
⏸️ **သင့်ငွေသွင်းမှု ဆိုင်းငံ့ထားသည်**

💰 **ပမာဏ:** {request[4]:,.0f} ကျပ်
📱 **ငွေသွင်းနည်း:** {request[5]}
🆔 **Request ID:** #{request_id}
📊 **လုပ်ဆောင်မှုအမှတ်:** `{request[10]}`
📅 **ဆိုင်းငံ့သည့်အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📝 **အကြောင်းပြချက်:** {admin_note or 'အကြောင်းပြချက်မရှိပါ'}

ကျေးဇူးပြု၍ စောင့်ဆိုင်းပေးပါ။ Admin မှ ဆက်လက်စစ်ဆေးပေးပါမည်။

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                """
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        return True, "Payment put on hold successfully"

    # Withdrawal Request Methods
    async def create_withdrawal_request(self, user_id, username, first_name, amount, payment_method, account_info):
        user = self.db.get_user(user_id)
        if not user or user[5] < amount:
            return None, None, "လက်ကျန်ငွေမလုံလောက်ပါ"
        
        request_id, transaction_id = self.db.create_withdrawal_request(user_id, username, first_name, amount, payment_method, account_info)
        if request_id:
            self.db.update_balance(user_id, -amount)
            self.db.record_transaction(user_id, 'withdrawal', -amount, f'Withdrawal request - {transaction_id}', 'pending', transaction_id)
            
            # Get user info for admin notification
            user_phone = user[4] if user[4] else "မှတ်ပုံတင်မထားရှိ"
            user_full_name = f"{user[2]} {user[3]}" if user[3] else user[2]
            
            admin_message = f"""
🏧 **ငွေထုတ်ခွင့်ပြုချက်တောင်းခံခြင်း**

👤 **User အချက်အလက်:**
• **နာမည်:** {user_full_name}
• **ဖုန်းနံပါတ်:** {user_phone}
• **Username:** @{username or 'N/A'}
• **User ID:** `{user_id}`

💰 **ငွေကြေးအချက်အလက်:**
• **ထုတ်ယူမည့်ပမာဏ:** {amount:,.0f} ကျပ်
• **ငွေထုတ်နည်း:** {payment_method}
• **အကောင့်အချက်အလက်:** {account_info}

📊 **လုပ်ဆောင်မှုအချက်အလက်:**
• **Request ID:** #{request_id}
• **Transaction ID:** `{transaction_id}`
• **လက်ရှိလက်ကျန်ငွေ:** {user[5] - amount:,.0f} ကျပ်

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ အတည်ပြုရန်", callback_data=f"approve_withdrawal_{request_id}"),
                    InlineKeyboardButton("❌ ငြင်းပယ်ရန်", callback_data=f"reject_withdrawal_{request_id}"),
                    InlineKeyboardButton("⏸️ ဆိုင်းငံ့ထား", callback_data=f"hold_withdrawal_{request_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.notify_admins(admin_message, reply_markup)
            return request_id, transaction_id, "Withdrawal request submitted successfully"
        return None, None, "Error creating withdrawal request"

    async def approve_withdrawal_request(self, request_id, admin_id, admin_note=None):
        request = self.db.get_withdrawal_request(request_id)
        if not request:
            return False, "Request not found"
        
        if request[7] != 'pending':
            return False, "Request already processed"
        
        self.db.update_withdrawal_request_status(request_id, 'approved', admin_id, admin_note)
        self.db.record_transaction(
            request[1], 'withdrawal', -request[4], 
            f'Withdrawal approved - {request[10]}', 'completed', request[10]
        )
        
        # Get user info for notification
        user = self.db.get_user(request[1])
        user_phone = user[4] if user[4] else "မှတ်ပုံတင်မထားရှိ"
        user_full_name = f"{user[2]} {user[3]}" if user[3] else user[2]
        
        try:
            await self.application.bot.send_message(
                request[1],
                f"""
✅ **သင့်ငွေထုတ်မှု အောင်မြင်ပါသည်**

👤 **အသုံးပြုသူအချက်အလက်:**
• **နာမည်:** {user_full_name}
• **ဖုန်းနံပါတ်:** {user_phone}

💰 **ငွေကြေးအချက်အလက်:**
• **ထုတ်ယူသည့်ပမာဏ:** {request[4]:,.0f} ကျပ်
• **ငွေထုတ်နည်း:** {request[5]}
• **အကောင့်အချက်အလက်:** {request[6]}

📊 **လုပ်ဆောင်မှုအချက်အလက်:**
• **Request ID:** #{request_id}
• **Transaction ID:** `{request[10]}`
• **လက်ရှိလက်ကျန်ငွေ:** {user[5]:,.0f} ကျပ်
• **အတည်ပြုသည့်အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                """
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        await self.send_live_payment_update(
            request[1], request[2], request[3], request[4], "withdrawal", request[10]
        )
        
        return True, "Withdrawal approved successfully"

    async def reject_withdrawal_request(self, request_id, admin_id, admin_note=None):
        request = self.db.get_withdrawal_request(request_id)
        if not request:
            return False, "Request not found"
        
        if request[7] != 'pending':
            return False, "Request already processed"
        
        self.db.update_balance(request[1], request[4])
        self.db.update_withdrawal_request_status(request_id, 'rejected', admin_id, admin_note)
        self.db.record_transaction(
            request[1], 'withdrawal_refund', request[4], 
            f'Withdrawal rejected - {request[10]}', 'completed', f"REF{request[10]}"
        )
        
        # Get user info for notification
        user = self.db.get_user(request[1])
        user_phone = user[4] if user[4] else "မှတ်ပုံတင်မထားရှိ"
        user_full_name = f"{user[2]} {user[3]}" if user[3] else user[2]
        
        try:
            await self.application.bot.send_message(
                request[1],
                f"""
❌ **သင့်ငွေထုတ်မှု ငြင်းပယ်ခံရသည်**

👤 **အသုံးပြုသူအချက်အလက်:**
• **နာမည်:** {user_full_name}
• **ဖုန်းနံပါတ်:** {user_phone}

💰 **ငွေကြေးအချက်အလက်:**
• **ထုတ်ယူသည့်ပမာဏ:** {request[4]:,.0f} ကျပ်
• **ငွေထုတ်နည်း:** {request[5]}

📊 **လုပ်ဆောင်မှုအချက်အလက်:**
• **Request ID:** #{request_id}
• **Transaction ID:** `{request[10]}`
• **ငြင်းပယ်သည့်အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• **အကြောင်းပြချက်:** {admin_note or 'အကြောင်းပြချက်မရှိပါ'}

💎 **လက်ရှိလက်ကျန်ငွေ:** {user[5]:,.0f} ကျပ်

ကျေးဇူးပြု၍ Admin နှင့်ဆက်သွယ်ပါ။

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                """
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        return True, "Withdrawal rejected successfully"

    async def hold_withdrawal_request(self, request_id, admin_id, admin_note=None):
        request = self.db.get_withdrawal_request(request_id)
        if not request:
            return False, "Request not found"
        
        if request[7] != 'pending':
            return False, "Request already processed"
        
        self.db.update_withdrawal_request_status(request_id, 'on_hold', admin_id, admin_note)
        
        # Get user info for notification
        user = self.db.get_user(request[1])
        user_phone = user[4] if user[4] else "မှတ်ပုံတင်မထားရှိ"
        user_full_name = f"{user[2]} {user[3]}" if user[3] else user[2]
        
        try:
            await self.application.bot.send_message(
                request[1],
                f"""
⏸️ **သင့်ငွေထုတ်မှု ဆိုင်းငံ့ထားသည်**

👤 **အသုံးပြုသူအချက်အလက်:**
• **နာမည်:** {user_full_name}
• **ဖုန်းနံပါတ်:** {user_phone}

💰 **ငွေကြေးအချက်အလက်:**
• **ထုတ်ယူမည့်ပမာဏ:** {request[4]:,.0f} ကျပ်
• **ငွေထုတ်နည်း:** {request[5]}

📊 **လုပ်ဆောင်မှုအချက်အလက်:**
• **Request ID:** #{request_id}
• **Transaction ID:** `{request[10]}`
• **ဆိုင်းငံ့သည့်အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• **အကြောင်းပြချက်:** {admin_note or 'အကြောင်းပြချက်မရှိပါ'}

💎 **လက်ရှိလက်ကျန်ငွေ:** {user[5]:,.0f} ကျပ်

ကျေးဇူးပြု၍ စောင့်ဆိုင်းပေးပါ။ Admin မှ ဆက်လက်စစ်ဆေးပေးပါမည်။

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                """
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        return True, "Withdrawal put on hold successfully"

    def get_ticket_price(self):
        try:
            price = self.db.get_setting('ticket_price', '1000')
            return int(price)
        except:
            return 1000

    def create_or_update_user(self, user_id, username, first_name, last_name="", phone=""):
        return self.db.create_user(user_id, username, first_name, last_name, phone)

    def get_user_profile(self, user_id):
        user = self.db.get_user(user_id)
        
        if user:
            profile_data = {
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3] if user[3] else "",
                'phone': user[4] if user[4] else "",
                'balance': user[5] if user[5] else 0,
                'total_spent': user[6] if user[6] else 0,
                'total_won': user[7] if user[7] else 0,
                'tickets_bought': user[8] if user[8] else 0,
                'join_date': user[9] if user[9] else "N/A",
                'last_active': user[10] if user[10] else "N/A"
            }
            return profile_data
        else:
            return None

    async def buy_ticket_with_confirmation(self, user_id, username, first_name, ticket_count=1):
        """Buy tickets with confirmation"""
        try:
            ticket_price = self.get_ticket_price()
            total_amount = ticket_count * ticket_price
            
            self.create_or_update_user(user_id, username, first_name)
            
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            balance_result = cursor.fetchone()
            balance = balance_result[0] if balance_result else 0
            
            if balance < total_amount:
                return f"❌ လက်ကျန်ငွေမလုံလောက်ပါ။\nလက်ရှိလက်ကျန်ငွေ: {balance:,.0f} ကျပ်\nလိုအပ်ငွေ: {total_amount:,.0f} ကျပ်\n\n💳 ငွေသွင်းရန် 'ငွေသွင်းနည်း' ကိုနှိပ်ပါ", 0, 0
            
            # Return confirmation message instead of buying immediately
            confirmation_text = f"""
🎫 **ကံစမ်းမဲဝယ်ယူမည် - အတည်ပြုခြင်း**

📊 **အချက်အလက်များ:**
• ကံစမ်းမဲအရေအတွက်: {ticket_count} ခု
• ကံစမ်းမဲတစ်ခုဈေး: {ticket_price:,} ကျပ်
• စုစုပေါင်းကျသင့်ငွေ: {total_amount:,.0f} ကျပ်
• လက်ရှိလက်ကျန်ငွေ: {balance:,.0f} ကျပ်
• ဝယ်ယူပြီးနောက်လက်ကျန်ငွေ: {balance - total_amount:,.0f} ကျပ်

⏰ **ကံစမ်းမဲဖွင့်ချိန်:** {self.db.get_draw_time()}

ကျေးဇူးပြု၍ အောက်ပါ Button များကိုနှိပ်ပါ:
            """
            
            return confirmation_text, total_amount, ticket_count
            
        except Exception as e:
            logger.error(f"Error in ticket confirmation: {e}")
            return "❌ ကံစမ်းမဲဝယ်ယူရာတွင် အမှားဖြစ်နေသည်", 0, 0

    async def confirm_ticket_purchase(self, user_id, username, first_name, ticket_count, total_amount):
        """Confirm and process ticket purchase"""
        try:
            cursor = self.db.connection.cursor()
            
            # Deduct balance
            cursor.execute("UPDATE users SET balance = balance - ?, total_spent = total_spent + ?, tickets_bought = tickets_bought + ? WHERE user_id = ?", 
                         (total_amount, total_amount, ticket_count, user_id))
            
            transaction_id = self.db.record_transaction(
                user_id, 'ticket_purchase', -total_amount,
                f'Purchased {ticket_count} tickets'
            )
            
            # Record tickets
            for i in range(ticket_count):
                cursor.execute("INSERT INTO tickets (user_id, username, amount, purchase_date, status) VALUES (?, ?, ?, datetime('now'), 'active')", 
                             (user_id, username, self.get_ticket_price()))
            
            self.db.connection.commit()
            self.db.update_user_activity(user_id)
            
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_balance = cursor.fetchone()[0]
            
            asyncio.create_task(self.send_live_payment_update(
                user_id, username, first_name, total_amount, "ticket_purchase", transaction_id
            ))
            
            return (f"✅ ကံစမ်းမဲ {ticket_count} ခု ဝယ်ယူပြီးပါပြီ!\n\n"
                    f"📊 အချက်အလက်များ:\n"
                    f"• ဝယ်ယူသောကံစမ်းမဲ: {ticket_count} ခု\n"
                    f"• ကံစမ်းမဲတစ်ခုဈေး: {self.get_ticket_price():,} ကျပ်\n"
                    f"• စုစုပေါင်းကျသင့်ငွေ: {total_amount:,.0f} ကျပ်\n"
                    f"• လက်ကျန်ငွေ: {new_balance:,.0f} ကျပ်\n"
                    f"• လုပ်ဆောင်မှုအမှတ်: `{transaction_id}`\n\n"
                    f"⏰ ကံစမ်းမဲဖွင့်ချိန်: {self.db.get_draw_time()}\n"
                    f"🎊 ကံကောင်းပါစေ!\n\n"
                    f"#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER")
            
        except Exception as e:
            logger.error(f"Error confirming ticket purchase: {e}")
            return "❌ ကံစမ်းမဲဝယ်ယူရာတွင် အမှားဖြစ်နေသည်"

    async def run_daily_draw(self):
        """Run the daily lottery draw"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"🎯 Running daily draw for {today}")
            
            # Get today's ticket sales
            daily_sales = self.db.get_daily_ticket_sales(today)
            
            if daily_sales > 0:
                # Select winners and distribute prizes
                buyers = self.db.get_today_ticket_buyers(today)
                if buyers:
                    # Select winners (simplified logic)
                    winner = random.choice(buyers)
                    prize_amount = daily_sales * 0.75  # 75% of sales as prize
                    
                    # Record winner
                    self.db.record_winner(winner[0], prize_amount, today, f"TICKET_{today}")
                    
                    # Update winner's balance
                    self.db.update_balance(winner[0], prize_amount)
                    
                    # Send announcement
                    announcement = f"""
🏆 **DAILY LUCKY DRAW RESULTS** 🏆

🎉 **ကြိုဆိုပါတယ်! ဒီနေ့ရဲ့ ကံထူးရှင်များ!** 🎉

👑 **First Prize Winner:**
👤 {winner[2]} (@{winner[1]})
💰 **ဆုကြေးငွေ:** {prize_amount:,.0f} ကျပ်
🎫 **ကံစမ်းမဲနံပါတ်:** TICKET_{today}

💝 **ကျေးဇူးတင်ရှိပါသည်:**
• ကျေးဇူးတင်လွှာ - ကျေးဇူးပြု၍ Lucky Draw Myanmar ကိုဆက်လက်ပံ့ပိုးပေးပါ
• အလှူငွေ - {daily_sales * 0.05:,.0f} ကျပ်

🎊 **ကံကောင်းခြင်းဟာ သင့်အတွက်ပါ!**
နက်ဖြန်ညပိုင်း ကံစမ်းမဲထပ်ဝယ်ယူပြီး ဆုကြေးကြီးကြီးမားမားရယူလိုက်ပါ!

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                    """
                    
                    # Send to announcement channel
                    announcement_channel = self.db.get_setting('announcement_channel', Config.ANNOUNCEMENT_CHANNEL)
                    if announcement_channel:
                        await self.application.bot.send_message(
                            chat_id=announcement_channel,
                            text=announcement,
                            parse_mode='Markdown'
                        )
                    
                    # Notify winner
                    try:
                        await self.application.bot.send_message(
                            chat_id=winner[0],
                            text=f"""
🎉 **Congratulations! You Won!** 🎉

သင့်အား ယနေ့ကံစမ်းမဲပွဲတွင် ဆုကြေးငွေ ရရှိပါသည်!

💰 **ဆုကြေးငွေ:** {prize_amount:,.0f} ကျပ်
🎫 **ကံစမ်းမဲနံပါတ်:** TICKET_{today}
📅 **ရက်စွဲ:** {today}

ကျေးဇူးတင်ပါသည်! နက်ဖြန်ညပိုင်း ထပ်မံဝယ်ယူကံစမ်းနိုင်ပါသည်!

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
                            """,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Could not notify winner: {e}")
            
            logger.info(f"✅ Daily draw completed for {today}")
            
        except Exception as e:
            logger.error(f"❌ Error running daily draw: {e}")

# Menu Builder Functions
def get_main_menu(user_id=None, db_manager=None):
    is_admin = db_manager.is_admin(user_id) if db_manager and user_id else False
    
    # Get today's donation and prize pool
    today = datetime.now().strftime('%Y-%m-%d')
    daily_sales = db_manager.get_daily_ticket_sales(today) if db_manager else 0
    today_donation = daily_sales * 0.05
    today_prize_pool = daily_sales * 0.75
    
    # Get user profile if available
    user_profile = None
    if user_id and db_manager:
        user_profile = db_manager.get_user(user_id)
    
    # Get current draw time
    draw_time = db_manager.get_draw_time() if db_manager else Config.DAILY_DRAW_TIME
    
    menu_text = f"""
🏆 **Lucky Draw Myanmar**🏆

💝 **အများကောင်းမှုအတွက် အလှူငွေ** - {today_donation:,.0f} ကျပ်

"""
    
    if user_profile:
        menu_text += f"""
NAME         - {user_profile[2]} {user_profile[3] if user_profile[3] else ''}
Ph No         - {user_profile[4] if user_profile[4] else 'မှတ်ပုံတင်မထားရှိ'}
ID                - {user_profile[0]}
လက်ကျန်ငွေ - {user_profile[5]:,.0f} ကျပ်
"""
    else:
        menu_text += """
NAME         - ????????
Ph No         - ????????
ID                - ????????
လက်ကျန်ငွေ - ?????????
"""
    
    menu_text += f"""
🏆 **ဤယနေ့ ဆုငွေ စုစုပေါင်း** - {today_prize_pool:,.0f} ကျပ်
⏰ **ကံစမ်း�မဲဖွင့်ချိန်** - {draw_time}

- နေ့စဉ် ကံထူးရှင်များ ဖြစ်ကြပါစေ 

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
"""
    
    return menu_text

def get_reply_keyboard(user_id=None, db_manager=None):
    """Create a custom reply keyboard"""
    is_admin = db_manager.is_admin(user_id) if db_manager and user_id else False
    
    keyboard = [
        [KeyboardButton("🎫 ကံစမ်းမဲဝယ်ယူရန်"), KeyboardButton("💰 လက်ကျန်ငွေ")],
        [KeyboardButton("💳 ငွေသွင်းရန်"), KeyboardButton("🏧 ငွေထုတ်ရန်")],
        [KeyboardButton("🏆 ကံထူးရှင်ကြီးများ"), KeyboardButton("📊 ကိုယ်ရေးအချက်အလက်")],
        [KeyboardButton("❓ အကူအညီ"), KeyboardButton("🔙 မူလ Menu")]
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton("👑 Admin Panel")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_buy_ticket_menu():
    keyboard = [
        [InlineKeyboardButton("1 ကံစမ်းမဲ", callback_data="buy_1"), InlineKeyboardButton("5 ကံစမ်းမဲ", callback_data="buy_5")],
        [InlineKeyboardButton("10 ကံစမ်းမဲ", callback_data="buy_10"), InlineKeyboardButton("📝 ကိုယ်ပိုင်အရေအတွက်ရွေးရန်", callback_data="custom_amount")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ticket_confirmation_menu(ticket_count, total_amount):
    keyboard = [
        [InlineKeyboardButton("✅ အတည်ပြုဝယ်ယူမည်", callback_data=f"confirm_ticket_{ticket_count}_{total_amount}")],
        [InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data="cancel_ticket")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deposit_menu():
    keyboard = [
        [InlineKeyboardButton("📱 KPay ဖြင့်ငွေသွင်းရန်", callback_data="deposit_kpay"), InlineKeyboardButton("📱 WavePay ဖြင့်ငွေသွင်းရန်", callback_data="deposit_wavepay")],
        [InlineKeyboardButton("📋 ငွေသွင်းမှတ်တမ်း", callback_data="payment_history"), InlineKeyboardButton("👨‍💼 Admin နှင့်ဆက်သွယ်ရန်", url=f"tg://user?id={8070878424}")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_withdrawal_menu():
    keyboard = [
        [InlineKeyboardButton("📱 KPay ဖြင့်ငွေထုတ်ရန်", callback_data="withdraw_kpay"), InlineKeyboardButton("📱 WavePay ဖြင့်ငွေထုတ်ရန်", callback_data="withdraw_wavepay")],
        [InlineKeyboardButton("📋 ငွေထုတ်မှတ်တမ်း", callback_data="withdrawal_history"), InlineKeyboardButton("👨‍💼 Admin နှင့်ဆက်သွယ်ရန်", url=f"tg://user?id={8070878424}")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("📋 User စာရင်း", callback_data="users_list"), InlineKeyboardButton("🏆 ထိပ်တန်း User", callback_data="top_users")],
        [InlineKeyboardButton("💰 ငွေသွင်းခွင့်ပြုချက်များ", callback_data="pending_payments"), InlineKeyboardButton("🏧 ငွေထုတ်ခွင့်ပြုချက်များ", callback_data="pending_withdrawals")],
        [InlineKeyboardButton("🎫 ကံစမ်းမဲဈေးနှုန်း", callback_data="set_ticket_price"), InlineKeyboardButton("⏰ ကံစမ်းမဲဖွင့်ချိန်", callback_data="set_draw_time")],
        [InlineKeyboardButton("👑 Admin Management", callback_data="admin_management")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_confirm_menu():
    keyboard = [
        [InlineKeyboardButton("✅ အတည်ပြုရန်", callback_data="confirm_payment")],
        [InlineKeyboardButton("✏️ ပြန်လည်ပြင်ဆင်ရန်", callback_data="edit_payment")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_withdrawal_confirm_menu():
    keyboard = [
        [InlineKeyboardButton("✅ အတည်ပြုရန်", callback_data="confirm_withdrawal")],
        [InlineKeyboardButton("✏️ ပြန်လည်ပြင်ဆင်ရန်", callback_data="edit_withdrawal")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    keyboard = [
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_faq_menu():
    keyboard = [
        [InlineKeyboardButton("1 - အကောင့်ဖွင့်နည်း", callback_data="faq_1"), InlineKeyboardButton("2 - ကံစမ်း�မဲဝယ်နည်း", callback_data="faq_2")],
        [InlineKeyboardButton("3 - ငွေသွင်းနည်း", callback_data="faq_3"), InlineKeyboardButton("4 - အကူအညီ", callback_data="faq_4")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_winners_menu():
    keyboard = [
        [InlineKeyboardButton("📅 ယနေ့ကံထူးရှင်များ", callback_data="today_winners")],
        [InlineKeyboardButton("📊 ပြီးခဲ့သောကံထူးရှင်များ", callback_data="past_winners")],
        [InlineKeyboardButton("🏆 ထိပ်တန်းကံထူးရှင်များ", callback_data="top_winners")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_help_menu():
    keyboard = [
        [InlineKeyboardButton("📖 FAQ", callback_data="faq_menu")],
        [InlineKeyboardButton("👨‍💼 Admin နှင့်ဆက်သွယ်ရန်", url=f"tg://user?id={8070878424}")],
        [InlineKeyboardButton("🔙 မူလ Menu", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Bot command handlers
async def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    lottery_system = context.bot_data.get('lottery_system')
    db_manager = context.bot_data.get('db_manager')
    
    if lottery_system:
        lottery_system.create_or_update_user(
            user.id, 
            user.username, 
            user.first_name, 
            getattr(user, 'last_name', '')
        )
    
    menu_text = get_main_menu(user.id, db_manager)
    
    await update.message.reply_text(
        menu_text, 
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard(user.id, db_manager)
    )

async def buy_ticket_command(update: Update, context: CallbackContext):
    user = update.effective_user
    lottery_system = context.bot_data.get('lottery_system')
    
    if lottery_system:
        lottery_system.create_or_update_user(
            user.id, 
            user.username, 
            user.first_name, 
            getattr(user, 'last_name', '')
        )
    
    ticket_price = lottery_system.get_ticket_price() if lottery_system else 1000
    await update.message.reply_text(
        f"**ကံစမ်းမဲဝယ်ယူရန်**\n\n🎫 ကံစမ်းမဲတစ်ခုလျှင်: {ticket_price:,} ကျပ်\n\nမည်မျှကံစမ်းမဲဝယ်ယူမည်နည်း?\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
        parse_mode='Markdown',
        reply_markup=get_buy_ticket_menu()
    )

async def balance_command(update: Update, context: CallbackContext):
    user = update.effective_user
    try:
        db_manager = context.bot_data.get('db_manager')
        if db_manager:
            user_data = db_manager.get_user(user.id)
            balance = user_data[5] if user_data else 0
            
            await update.message.reply_text(
                f"💰 **သင့်လက်ကျန်ငွေ**\n\nလက်ကျန်ငွေ: {balance:,.0f} ကျပ်\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                parse_mode='Markdown',
                reply_markup=get_reply_keyboard(user.id, db_manager)
            )
    except Exception as e:
        logger.error(f"Balance command error: {e}")
        await update.message.reply_text(
            "❌ လက်ကျန်ငွေကြည့်ရာတွင် အမှားဖြစ်နေသည်\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
            reply_markup=get_reply_keyboard(user.id, context.bot_data.get('db_manager'))
        )

async def deposit_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "💳 **ငွေသွင်းရန်**\n\nကျေးဇူးပြု၍ ငွေသွင်းလိုသော နည်းလမ်းကိုရွေးချယ်ပါ:\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
        parse_mode='Markdown',
        reply_markup=get_deposit_menu()
    )

async def withdraw_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🏧 **ငွေထုတ်ရန်**\n\nကျေးဇူးပြု၍ ငွေထုတ်လိုသော နည်းလမ်းကိုရွေးချယ်ပါ:\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
        parse_mode='Markdown',
        reply_markup=get_withdrawal_menu()
    )

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🏆 **Lucky Draw Myanmar Help**\n\nကျေးဇူးပြု၍ အောက်ပါ option များထဲမှ တစ်ခုခုရွေးချယ်ပါ:\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
        parse_mode='Markdown',
        reply_markup=get_help_menu()
    )

async def profile_command(update: Update, context: CallbackContext):
    user = update.effective_user
    lottery_system = context.bot_data.get('lottery_system')
    db_manager = context.bot_data.get('db_manager')
    
    if lottery_system:
        profile = lottery_system.get_user_profile(user.id)
        if profile:
            today = datetime.now().strftime('%Y-%m-%d')
            daily_sales = lottery_system.db.get_daily_ticket_sales(today)
            today_prize_pool = daily_sales * 0.75
            today_donation = daily_sales * 0.05
            
            profile_text = f"""
🏆 **Lucky Draw Profile**

💝 **အများကောင်းမှုအတွက် အလှူငွေ** - {today_donation:,.0f} ကျပ်

👤 **ကိုယ်ရေးအချက်အလက်:**
• NAME - {profile['first_name']} {profile.get('last_name', '')}
• ID - {profile['user_id']}
• Ph no. - {profile['phone'] if profile['phone'] else 'မှတ်ပုံတင်မထားရှိ'}
• Register Date - {profile['join_date'][:10] if profile['join_date'] else 'N/A'}
• လက်ကျန်ငွေ - {profile['balance']:,.0f} ကျပ်

🏆 **ဤယနေ့ ဆုငွေ စုစုပေါင်း** - {today_prize_pool:,.0f} ကျပ်

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
            """
            
            await update.message.reply_text(
                profile_text,
                parse_mode='Markdown',
                reply_markup=get_reply_keyboard(user.id, db_manager)
            )

async def winners_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🏆 **ကံထူးရှင်ကြီးများ**\n\nကျေးဇူးပြု၍ ကြည့်ရှုလိုသော ကံထူးရှင်စာရင်းကို ရွေးချယ်ပါ:\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
        parse_mode='Markdown',
        reply_markup=get_winners_menu()
    )

async def admin_panel_command(update: Update, context: CallbackContext):
    user = update.effective_user
    db_manager = context.bot_data.get('db_manager')
    
    if db_manager and db_manager.is_admin(user.id):
        await update.message.reply_text(
            "👑 **Admin Panel**\n\nကျေးဇူးပြု၍ စီမံခန့်ခွဲမှုလုပ်ငန်းတစ်ခုခုရွေးချယ်ပါ:\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
            parse_mode='Markdown',
            reply_markup=get_admin_menu()
        )
    else:
        await update.message.reply_text(
            "❌ Admin permission required\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
            reply_markup=get_reply_keyboard(user.id, db_manager)
        )

# Button handler
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    data = query.data
    
    logger.info(f"🎯 Button clicked: {data} by user {user.id}")
    
    lottery_system = context.bot_data.get('lottery_system')
    db_manager = context.bot_data.get('db_manager')
    
    try:
        # Main navigation
        if data == "back_main":
            menu_text = get_main_menu(user.id, db_manager)
            await query.edit_message_text(
                menu_text,
                parse_mode='Markdown',
                reply_markup=get_reply_keyboard(user.id, db_manager)
            )
            return
        
        # Buy ticket buttons with confirmation
        elif data.startswith("buy_"):
            if data == "buy_1":
                ticket_count = 1
            elif data == "buy_5":
                ticket_count = 5
            elif data == "buy_10":
                ticket_count = 10
            elif data == "custom_amount":
                context.user_data['waiting_for_custom_amount'] = True
                await query.edit_message_text(
                    "📝 **ကိုယ်ပိုင်ကံစမ်းမဲအရေအတွက်**\n\nကျေးဇူးပြု၍ ဝယ်ယူလိုသော ကံစမ်းမဲအရေအတွက်ကို ရိုက်ထည့်ပါ:\n\nဥပမာ: `3`\n\n**မှတ်ချက်:** တစ်ကြိမ်လျှင် အများဆုံး 50 ကံစမ်းမဲအထိသာ ဝယ်ယူနိုင်ပါသည်။\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    parse_mode='Markdown',
                    reply_markup=get_back_menu()
                )
                return
            else:
                ticket_count = 1
            
            if lottery_system:
                result, total_amount, ticket_count = await lottery_system.buy_ticket_with_confirmation(
                    user.id, user.username, user.first_name, ticket_count
                )
                
                if result.startswith("❌"):
                    await query.edit_message_text(
                        result,
                        parse_mode='Markdown'
                    )
                else:
                    context.user_data['pending_ticket_purchase'] = {
                        'ticket_count': ticket_count,
                        'total_amount': total_amount
                    }
                    
                    await query.edit_message_text(
                        result,
                        parse_mode='Markdown',
                        reply_markup=get_ticket_confirmation_menu(ticket_count, total_amount)
                    )
            return
        
        # Ticket purchase confirmation
        elif data.startswith("confirm_ticket_"):
            if lottery_system and 'pending_ticket_purchase' in context.user_data:
                purchase_data = context.user_data['pending_ticket_purchase']
                ticket_count = purchase_data['ticket_count']
                total_amount = purchase_data['total_amount']
                
                result = await lottery_system.confirm_ticket_purchase(
                    user.id, user.username, user.first_name, ticket_count, total_amount
                )
                
                await query.edit_message_text(
                    result,
                    parse_mode='Markdown'
                )
                
                context.user_data.pop('pending_ticket_purchase', None)
            return
        
        elif data == "cancel_ticket":
            if 'pending_ticket_purchase' in context.user_data:
                context.user_data.pop('pending_ticket_purchase', None)
            
            await query.edit_message_text(
                "❌ ကံစမ်းမဲဝယ်ယူမှု ပယ်ဖျက်လိုက်ပါပြီ။\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                parse_mode='Markdown',
                reply_markup=get_buy_ticket_menu()
            )
            return
        
        # Admin draw time setting
        elif data == "set_draw_time":
            if db_manager and db_manager.is_admin(user.id):
                context.user_data['setting_draw_time'] = True
                current_time = db_manager.get_draw_time()
                await query.edit_message_text(
                    f"⏰ **ကံစမ်းမဲဖွင့်ချိန် ပြင်ဆင်ရန်**\n\nလက်ရှိဖွင့်ချိန်: `{current_time}`\n\nကျေးဇူးပြု၍ အသစ်ပြင်ဆင်လိုသော အချိန်ကို ရိုက်ထည့်ပါ:\n\nဥပမာ: `18:30`\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    parse_mode='Markdown',
                    reply_markup=get_back_menu()
                )
            return
        
        # ... (ကျန်တဲ့ button handler တွေကို မူရင်းအတိုင်းထားခဲ့ပါ) ...
        
        else:
            # For other buttons, show coming soon message
            await query.edit_message_text(
                f"🔘 Button: {data}\n\nThis feature is coming soon!\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                reply_markup=get_back_menu()
            )
            
    except Exception as e:
        logger.error(f"❌ Button handler error: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again.\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
            reply_markup=get_back_menu()
        )

# Text message handler
async def handle_text_message(update: Update, context: CallbackContext):
    user = update.effective_user
    message_text = update.message.text.strip()
    
    lottery_system = context.bot_data.get('lottery_system')
    db_manager = context.bot_data.get('db_manager')
    
    # Handle reply keyboard buttons
    if message_text == "🎫 ကံစမ်းမဲဝယ်ယူရန်":
        await buy_ticket_command(update, context)
        return
    elif message_text == "💰 လက်ကျန်ငွေ":
        await balance_command(update, context)
        return
    elif message_text == "💳 ငွေသွင်းရန်":
        await deposit_command(update, context)
        return
    elif message_text == "🏧 ငွေထုတ်ရန်":
        await withdraw_command(update, context)
        return
    elif message_text == "📊 ကိုယ်ရေးအချက်အလက်":
        await profile_command(update, context)
        return
    elif message_text == "🏆 ကံထူးရှင်ကြီးများ":
        await winners_command(update, context)
        return
    elif message_text == "❓ အကူအညီ":
        await help_command(update, context)
        return
    elif message_text == "👑 Admin Panel":
        await admin_panel_command(update, context)
        return
    elif message_text == "🔙 မူလ Menu":
        menu_text = get_main_menu(user.id, db_manager)
        await update.message.reply_text(
            menu_text,
            parse_mode='Markdown',
            reply_markup=get_reply_keyboard(user.id, db_manager)
        )
        return
    
    # Handle custom ticket amount
    if 'waiting_for_custom_amount' in context.user_data:
        try:
            ticket_count = int(message_text)
            if ticket_count <= 0:
                await update.message.reply_text(
                    "❌ ကံစမ်းမဲအရေအတွက်သည် 0 ထက်ကြီးရပါမည်\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    reply_markup=get_reply_keyboard(user.id, db_manager)
                )
                return
            
            if ticket_count > Config.MAX_TICKETS_PER_USER:
                await update.message.reply_text(
                    f"❌ တစ်ကြိမ်လျှင် ကံစမ်းမဲ {Config.MAX_TICKETS_PER_USER} ခုထက်မပိုနိုင်ပါ\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    reply_markup=get_reply_keyboard(user.id, db_manager)
                )
                return
            
            if lottery_system:
                result, total_amount, ticket_count = await lottery_system.buy_ticket_with_confirmation(
                    user.id, user.username, user.first_name, ticket_count
                )
                
                if result.startswith("❌"):
                    await update.message.reply_text(
                        result,
                        parse_mode='Markdown',
                        reply_markup=get_reply_keyboard(user.id, db_manager)
                    )
                else:
                    context.user_data['pending_ticket_purchase'] = {
                        'ticket_count': ticket_count,
                        'total_amount': total_amount
                    }
                    
                    await update.message.reply_text(
                        result,
                        parse_mode='Markdown',
                        reply_markup=get_ticket_confirmation_menu(ticket_count, total_amount)
                    )
            
            context.user_data.pop('waiting_for_custom_amount', None)
            
        except ValueError:
            await update.message.reply_text(
                "❌ မှားယွင်းသောအရေအတွက်ဖြစ်နေသည်\nကျေးဇူးပြု၍ နံပါတ်သက်သက်ရိုက်ထည့်ပါ\n\nဥပမာ: `5`\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                parse_mode='Markdown',
                reply_markup=get_reply_keyboard(user.id, db_manager)
            )
        return
    
    # Handle draw time setting for admin
    elif 'setting_draw_time' in context.user_data and db_manager and db_manager.is_admin(user.id):
        try:
            # Validate time format
            import re
            time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
            
            if not time_pattern.match(message_text):
                await update.message.reply_text(
                    "❌ မှားယွင်းသောအချိန်ဖော်မတ်ဖြစ်နေသည်\nကျေးဇူးပြု၍ HH:MM ဖော်မတ်ဖြင့် ရိုက်ထည့်ပါ\n\nဥပမာ: `18:30`\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    reply_markup=get_admin_menu()
                )
                return
            
            # Update draw time
            success = db_manager.update_draw_time(message_text)
            if success:
                # Restart scheduler with new time
                lottery_system.setup_daily_draw()
                
                await update.message.reply_text(
                    f"✅ ကံစမ်းမဲဖွင့်ချိန်ကို `{message_text}` သို့ ပြောင်းလဲပြီးပါပြီ\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    parse_mode='Markdown',
                    reply_markup=get_admin_menu()
                )
            else:
                await update.message.reply_text(
                    "❌ ကံစမ်းမဲဖွင့်ချိန် ပြောင်းလဲရာတွင် အမှားဖြစ်နေသည်\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                    reply_markup=get_admin_menu()
                )
            
            context.user_data.pop('setting_draw_time', None)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ အချိန်ပြောင်းလဲရာတွင် အမှားဖြစ်နေသည်: {e}\n\n#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER",
                reply_markup=get_admin_menu()
            )
        return
    
    # Default response for any other text
    menu_text = get_main_menu(user.id, db_manager)
    await update.message.reply_text(
        menu_text,
        parse_mode='Markdown',
        reply_markup=get_reply_keyboard(user.id, db_manager)
    )

# Photo handler for payment screenshots
async def handle_photo(update: Update, context: CallbackContext):
    user = update.effective_user
    db_manager = context.bot_data.get('db_manager')
    
    # Check if user is in deposit confirmation step
    if 'deposit_info' in context.user_data and context.user_data['deposit_info']['step'] == 'confirm':
        photo = update.message.photo[-1]
        context.user_data['deposit_info']['screenshot'] = photo.file_id
        
        deposit_info = context.user_data['deposit_info']
        
        await update.message.reply_text(
            f"""
📸 **Screenshot လက်ခံရရှိပါသည်**

💰 **ပမာဏ:** {deposit_info['amount']:,.0f} ကျပ်
📱 **ငွေသွင်းနည်း:** {deposit_info['method']}

ကျေးဇူးပြု၍ အောက်ပါ Button များကိုနှိပ်ပါ:

#LUCKYDRAWMYANMAR #ATH #EAGLEDEVELOPER
            """,
            parse_mode='Markdown',
            reply_markup=get_payment_confirm_menu()
        )

# Error handler
async def error_handler(update: Update, context: CallbackContext):
    """Handle errors in the bot."""
    try:
        logger.error(f"❌ Bot error: {context.error}")
    except Exception as e:
        logger.error(f"❌ Error in error handler: {e}")

# Webhook setup for Render
async def setup_webhook(application):
    # Get Render external URL from environment
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url}/telegram"
        await application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=Update.ALL_TYPES
        )
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("❌ RENDER_EXTERNAL_URL not set, using polling")

# Starlette web application for Render
async def telegram_webhook(request: Request):
    """Handle Telegram webhook requests"""
    try:
        application = request.app.state.application
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response()
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)

async def health_check(request: Request):
    """Health check endpoint for Render"""
    return PlainTextResponse("OK")

async def main():
    """Main function to run the bot"""
    # Initialize database
    db_manager = DatabaseManager()
    
    # Create Telegram application
    application = (
        Application.builder()
        .token(Config.BOT_TOKEN)
        .build()
    )
    
    # Store objects in bot_data
    application.bot_data['db_manager'] = db_manager
    lottery_system = LotterySystem(db_manager, application)
    application.bot_data['lottery_system'] = lottery_system
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("buy", buy_ticket_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("winners", winners_command))
    application.add_handler(CommandHandler("admin", admin_panel_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    application.add_error_handler(error_handler)
    
    # Check if running on Render
    if os.environ.get("RENDER"):
        # Webhook mode for Render
        await setup_webhook(application)
        
        # Create Starlette app
        starlette_app = Starlette()
        starlette_app.state.application = application
        
        # Add routes
        starlette_app.router.add_route("/telegram", telegram_webhook, methods=["POST"])
        starlette_app.router.add_route("/healthcheck", health_check, methods=["GET"])
        
        return starlette_app
    else:
        # Polling mode for local development
        logger.info("🤖 Starting bot in polling mode...")
        await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

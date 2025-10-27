from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    ContextTypes, 
    filters,
    ConversationHandler,
    JobQueue
)
from telegram.constants import ParseMode
import sqlite3
import random
from datetime import datetime, timedelta
import asyncio
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token and Admin Settings
BOT_TOKEN = "8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc"
ADMIN_USERS = [8070878424]

# Channel Links for alarms
PAYMENT_CHANNEL = "https://t.me/+C-60JUm8CKVlOTBl"
OFFICIAL_CHANNEL = "https://t.me/+_P7OHmGNs8g2MGE1"

# Conversation states for prize management
PRIZE_NAME_1ST, PRIZE_AMOUNT_1ST, PRIZE_NAME_2ND, PRIZE_AMOUNT_2ND, PRIZE_NAME_3RD, PRIZE_AMOUNT_3RD, PRIZE_NAME_4TH, PRIZE_AMOUNT_4TH, PRIZE_NAME_OTHER, PRIZE_AMOUNT_OTHER = range(10)

# System settings with prizes including names
SYSTEM_SETTINGS = {
    "ticket_price": 1000,
    "auto_draw_time": "18:00", 
    "auto_draw_enabled": True,
    "kpay_name": "AUNG THU HTWE",
    "kpay_phone": "09789999368",
    "wavepay_name": "AUNG THU HTWE",  
    "wavepay_phone": "09789999368",
    "admin_name": "AUNG THU HTWE",
    "admin_phone": "09789999368",
    "alarm_times": ["17:30", "17:45", "17:50", "17:55", "17:58", "17:59"],
    "prizes": {
        "1st": {"name": "ဆုကြီး", "amount": "10,000,000 Ks"},
        "2nd": {"name": "ဒုတိယဆု", "amount": "5,000,000 Ks"}, 
        "3rd": {"name": "တတိယဆု", "amount": "1,000,000 Ks"},
        "4th": {"name": "စတုတ္ထဆု", "amount": "500,000 Ks"},
        "other": {"name": "ပဉ္စမဆု", "amount": "100,000 Ks"}
    }
}

# ==============================
# DATABASE SETUP
# ==============================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('luckydraw.db', check_same_thread=False)
        self.create_tables()
        self.load_settings()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                email TEXT,
                balance INTEGER DEFAULT 0,
                tickets INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prize_rank TEXT,
                prize_name TEXT,
                prize_amount TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default prizes with names
        default_prizes = [
            ('1st', 'ဆုကြီး', '10,000,000 Ks'),
            ('2nd', 'ဒုတိယဆု', '5,000,000 Ks'),
            ('3rd', 'တတိယဆု', '1,000,000 Ks'), 
            ('4th', 'စတုတ္ထဆု', '500,000 Ks'),
            ('other', 'ပဉ္စမဆု', '100,000 Ks')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO prizes (prize_rank, prize_name, prize_amount) VALUES (?, ?, ?)
        ''', default_prizes)
        
        # Insert default settings
        default_settings = [
            ('kpay_name', 'AUNG THU HTWE'),
            ('kpay_phone', '09789999368'),
            ('wavepay_name', 'AUNG THU HTWE'),
            ('wavepay_phone', '09789999368'),
            ('admin_name', 'AUNG THU HTWE'),
            ('admin_phone', '09789999368'),
            ('ticket_price', '1000'),
            ('auto_draw_time', '18:00'),
            ('auto_draw_enabled', 'True'),
            ('alarm_times', '["17:30", "17:45", "17:50", "17:55", "17:58", "17:59"]'),
            ('prizes', '{"1st": {"name": "ဆုကြီး", "amount": "10,000,000 Ks"}, "2nd": {"name": "ဒုတိယဆု", "amount": "5,000,000 Ks"}, "3rd": {"name": "တတိယဆု", "amount": "1,000,000 Ks"}, "4th": {"name": "စတုတ္ထဆု", "amount": "500,000 Ks"}, "other": {"name": "ပဉ္စမဆု", "amount": "100,000 Ks"}}')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        ''', default_settings)
        
        self.conn.commit()
    
    def load_settings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings = cursor.fetchall()
        
        for key, value in settings:
            if key in SYSTEM_SETTINGS:
                if key in ['ticket_price']:
                    SYSTEM_SETTINGS[key] = int(value)
                elif key in ['auto_draw_enabled']:
                    SYSTEM_SETTINGS[key] = value.lower() == 'true'
                elif key in ['alarm_times', 'prizes']:
                    SYSTEM_SETTINGS[key] = eval(value)
                else:
                    SYSTEM_SETTINGS[key] = value
    
    def save_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES (?, ?)
        ''', (key, str(value)))
        self.conn.commit()
        SYSTEM_SETTINGS[key] = value
    
    def get_prizes(self):
        """Get prizes from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT prize_rank, prize_name, prize_amount FROM prizes")
        prizes = cursor.fetchall()
        prize_dict = {}
        for rank, name, amount in prizes:
            prize_dict[rank] = {"name": name, "amount": amount}
        return prize_dict
    
    def update_prize(self, rank, name, amount):
        """Update prize name and amount"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO prizes (prize_rank, prize_name, prize_amount) 
            VALUES (?, ?, ?)
        ''', (rank, name, amount))
        self.conn.commit()
        # Update system settings
        SYSTEM_SETTINGS['prizes'][rank] = {"name": name, "amount": amount}
        self.save_setting('prizes', SYSTEM_SETTINGS['prizes'])

db = Database()

# ==============================
# BEAUTIFUL PRIZE DISPLAY FOR MAIN MENU
# ==============================
def get_prizes_display():
    """လှလှလေးပေါ်အောင် ဆုကြေးများပြသခြင်း"""
    prizes = db.get_prizes()
    
    prize_display = f"""
🏆 *LUCKY DRAW MYANMAR - ဆုကြေးများ* 🏆

┌─────────────────────────┐
│       💎 ဆုကြီးများ      │
└─────────────────────────┘

"""
    
    prize_emojis = {
        "1st": "🥇",
        "2nd": "🥈", 
        "3rd": "🥉",
        "4th": "🎯",
        "other": "🎁"
    }
    
    for rank in ["1st", "2nd", "3rd", "4th", "other"]:
        if rank in prizes:
            prize_data = prizes[rank]
            emoji = prize_emojis.get(rank, "🎁")
            prize_display += f"{emoji} *{prize_data['name']}* - {prize_data['amount']}\n"
    
    prize_display += f"""
┌─────────────────────────┐
│   🎰 ကံစမ်းမဲဝယ်ယူရန်   │
└─────────────────────────┘

💰 *တစ်ကြိမ်လျှင် {SYSTEM_SETTINGS['ticket_price']} ကျပ်*
⏰ *နေ့စဉ်ကံစမ်းမဲထွက်ချိန်: {SYSTEM_SETTINGS['auto_draw_time']}*

✨ *သင့်ကံကို စမ်းကြည့်ပါ!* ✨
"""
    
    return prize_display

# ==============================
# PRIZE MANAGEMENT SYSTEM
# ==============================
async def handle_prize_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prize management for admin"""
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return
    
    prizes = db.get_prizes()
    
    prize_text = f"""
🏆 *ဆုကြေးများ စီမံခန့်ခွဲမှု*

*လက်ရှိဆုကြေးများ:*

"""
    
    for rank in ["1st", "2nd", "3rd", "4th", "other"]:
        if rank in prizes:
            prize_data = prizes[rank]
            prize_text += f"• {prize_data['name']}: *{prize_data['amount']}*\n"
    
    prize_text += "\nအောက်ပါခလုတ်များဖြင့် ဆုနာမည်နှင့် ဆုကြေးပမာဏများကို ပြင်ဆင်နိုင်ပါသည်:"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🥇 1st Prize", callback_data="edit_1st_prize"),
         InlineKeyboardButton("🥈 2nd Prize", callback_data="edit_2nd_prize")],
        [InlineKeyboardButton("🥉 3rd Prize", callback_data="edit_3rd_prize"),
         InlineKeyboardButton("🎯 4th Prize", callback_data="edit_4th_prize")],
        [InlineKeyboardButton("🎁 Other Prizes", callback_data="edit_other_prize")],
        [InlineKeyboardButton("👀 Main Menu Preview", callback_data="preview_prizes")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin")]
    ])
    
    await update.message.reply_text(
        prize_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# EDIT PRIZE FUNCTIONS (Name and Amount)
# ==============================
async def edit_1st_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prizes = db.get_prizes()
    prize_data = prizes.get('1st', {'name': 'ဆုကြီး', 'amount': '10,000,000 Ks'})
    
    await query.edit_message_text(
        f"🥇 *1st Prize ပြင်ဆင်ရန်*\n\n"
        f"လက်ရှိ: {prize_data['name']} - {prize_data['amount']}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် ဆုနာမည် ထည့်ပါ:\n"
        f"ဥပမာ: `ဆုကြီး` သို့မဟုတ် `Grand Prize`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_NAME_1ST

async def edit_2nd_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prizes = db.get_prizes()
    prize_data = prizes.get('2nd', {'name': 'ဒုတိယဆု', 'amount': '5,000,000 Ks'})
    
    await query.edit_message_text(
        f"🥈 *2nd Prize ပြင်ဆင်ရန်*\n\n"
        f"လက်ရှိ: {prize_data['name']} - {prize_data['amount']}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် ဆုနာမည် ထည့်ပါ:\n"
        f"ဥပမာ: `ဒုတိယဆု` သို့မဟုတ် `Second Prize`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_NAME_2ND

async def edit_3rd_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prizes = db.get_prizes()
    prize_data = prizes.get('3rd', {'name': 'တတိယဆု', 'amount': '1,000,000 Ks'})
    
    await query.edit_message_text(
        f"🥉 *3rd Prize ပြင်ဆင်ရန်*\n\n"
        f"လက်ရှိ: {prize_data['name']} - {prize_data['amount']}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် ဆုနာမည် ထည့်ပါ:\n"
        f"ဥပမာ: `တတိယဆု` သို့မဟုတ် `Third Prize`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_NAME_3RD

async def edit_4th_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prizes = db.get_prizes()
    prize_data = prizes.get('4th', {'name': 'စတုတ္ထဆု', 'amount': '500,000 Ks'})
    
    await query.edit_message_text(
        f"🎯 *4th Prize ပြင်ဆင်ရန်*\n\n"
        f"လက်ရှိ: {prize_data['name']} - {prize_data['amount']}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် ဆုနာမည် ထည့်ပါ:\n"
        f"ဥပမာ: `စတုတ္ထဆု` သို့မဟုတ် `Fourth Prize`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_NAME_4TH

async def edit_other_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prizes = db.get_prizes()
    prize_data = prizes.get('other', {'name': 'ပဉ္စမဆု', 'amount': '100,000 Ks'})
    
    await query.edit_message_text(
        f"🎁 *Other Prizes ပြင်ဆင်ရန်*\n\n"
        f"လက်ရှိ: {prize_data['name']} - {prize_data['amount']}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် ဆုနာမည် ထည့်ပါ:\n"
        f"ဥပမာ: `ပဉ္စမဆု` သို့မဟုတ် `Consolation Prize`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_NAME_OTHER

# ==============================
# HANDLE PRIZE NAME INPUTS
# ==============================
async def handle_prize_name_1st_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_name = update.message.text.strip()
    if not prize_name:
        await update.message.reply_text("❌ ဆုနာမည် ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_NAME_1ST
    
    context.user_data['temp_prize_name_1st'] = prize_name
    await update.message.reply_text(
        f"✅ *ဆုနာမည် သိမ်းဆည်းပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n\n"
        f"ကျေးဇူးပြု၍ ဆုကြေးပမာဏ ထည့်ပါ:\n"
        f"ဥပမာ: `10,000,000 Ks`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_AMOUNT_1ST

async def handle_prize_name_2nd_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_name = update.message.text.strip()
    if not prize_name:
        await update.message.reply_text("❌ ဆုနာမည် ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_NAME_2ND
    
    context.user_data['temp_prize_name_2nd'] = prize_name
    await update.message.reply_text(
        f"✅ *ဆုနာမည် သိမ်းဆည်းပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n\n"
        f"ကျေးဇူးပြု၍ ဆုကြေးပမာဏ ထည့်ပါ:\n"
        f"ဥပမာ: `5,000,000 Ks`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_AMOUNT_2ND

async def handle_prize_name_3rd_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_name = update.message.text.strip()
    if not prize_name:
        await update.message.reply_text("❌ ဆုနာမည် ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_NAME_3RD
    
    context.user_data['temp_prize_name_3rd'] = prize_name
    await update.message.reply_text(
        f"✅ *ဆုနာမည် သိမ်းဆည်းပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n\n"
        f"ကျေးဇူးပြု၍ ဆုကြေးပမာဏ ထည့်ပါ:\n"
        f"ဥပမာ: `1,000,000 Ks`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_AMOUNT_3RD

async def handle_prize_name_4th_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_name = update.message.text.strip()
    if not prize_name:
        await update.message.reply_text("❌ ဆုနာမည် ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_NAME_4TH
    
    context.user_data['temp_prize_name_4th'] = prize_name
    await update.message.reply_text(
        f"✅ *ဆုနာမည် သိမ်းဆည်းပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n\n"
        f"ကျေးဇူးပြု၍ ဆုကြေးပမာဏ ထည့်ပါ:\n"
        f"ဥပမာ: `500,000 Ks`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_AMOUNT_4TH

async def handle_prize_name_other_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_name = update.message.text.strip()
    if not prize_name:
        await update.message.reply_text("❌ ဆုနာမည် ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_NAME_OTHER
    
    context.user_data['temp_prize_name_other'] = prize_name
    await update.message.reply_text(
        f"✅ *ဆုနာမည် သိမ်းဆည်းပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n\n"
        f"ကျေးဇူးပြု၍ ဆုကြေးပမာဏ ထည့်ပါ:\n"
        f"ဥပမာ: `100,000 Ks`",
        parse_mode=ParseMode.MARKDOWN
    )
    return PRIZE_AMOUNT_OTHER

# ==============================
# HANDLE PRIZE AMOUNT INPUTS
# ==============================
async def handle_prize_amount_1st_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_amount = update.message.text.strip()
    if not prize_amount:
        await update.message.reply_text("❌ ဆုကြေးပမာဏ ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_AMOUNT_1ST
    
    prize_name = context.user_data.get('temp_prize_name_1st', 'ဆုကြီး')
    db.update_prize('1st', prize_name, prize_amount)
    
    await update.message.reply_text(
        f"✅ *1st Prize ပြင်ဆင်ပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n"
        f"ဆုကြေး: {prize_amount}",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

async def handle_prize_amount_2nd_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_amount = update.message.text.strip()
    if not prize_amount:
        await update.message.reply_text("❌ ဆုကြေးပမာဏ ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_AMOUNT_2ND
    
    prize_name = context.user_data.get('temp_prize_name_2nd', 'ဒုတိယဆု')
    db.update_prize('2nd', prize_name, prize_amount)
    
    await update.message.reply_text(
        f"✅ *2nd Prize ပြင်ဆင်ပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n"
        f"ဆုကြေး: {prize_amount}",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

async def handle_prize_amount_3rd_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_USERS:
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    prize_amount = update.message.text.strip()
    if not prize_amount:
        await update.message.reply_text("❌ ဆုကြေးပမာဏ ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return PRIZE_AMOUNT_3RD
    
    prize_name = context.user_data.get('temp_prize_name_3rd', 'တတိယဆု')
    db.update_prize('3rd', prize_name, prize_amount)
    
    await update.message.reply_text(
        f"✅ *3rd Prize ပြင်ဆင်ပြီးပါပြီ!*\n\n"
        f"ဆုနာမည်: {prize_name}\n"
        f"ဆုကြေး: {pri_amount}",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

# ... (4th and other prize amount handlers similar to above)

# ==============================
# PREVIEW PRIZES IN MAIN MENU STYLE
# ==============================
async def preview_prizes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prize_display = get_prizes_display()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ ဆုများပြင်ဆင်ရန်", callback_data="edit_prizes")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_prize_management")]
    ])
    
    await query.edit_message_text(
        prize_display,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# ENHANCED START COMMAND WITH BEAUTIFUL PRIZE DISPLAY
# ==============================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Create user if not exists
    cursor = db.conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) 
        VALUES (?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, user.last_name))
    db.conn.commit()
    
    if user.id in ADMIN_USERS:
        await update.message.reply_text(
            f"👨‍💼 *Admin Panel* သို့ ကြိုဆိုပါတယ်\n\nAdmin: {SYSTEM_SETTINGS.get('admin_name', 'AUNG THU HTWE')}",
            reply_markup=get_admin_reply_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Show beautiful prize display
    prize_display = get_prizes_display()
    
    keyboard = ReplyKeyboardMarkup([
        ["🎰 ကံစမ်းမဲ ဝယ်ယူရန်", "🏆 ဆုကြေးများကြည့်ရန်"],
        ["👤 ကျွန်တော့်ပရိုဖိုင်", "📊 ရလဒ်များကြည့်ရန်"],
        ["📢 Channel များ", "❓ အကူအညီ"]
    ], resize_keyboard=True, persistent=True)
    
    await update.message.reply_text(
        prize_display,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# PRIZE VIEW COMMAND FOR USERS
# ==============================
async def view_prizes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Users can view prizes with beautiful display"""
    prize_display = get_prizes_display()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 ကံစမ်းမဲ ဝယ်ယူရန်", callback_data="buy_tickets")],
        [InlineKeyboardButton("📢 Official Channel", url=OFFICIAL_CHANNEL)]
    ])
    
    await update.message.reply_text(
        prize_display,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# ADMIN REPLY KEYBOARD
# ==============================
def get_admin_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 စာရင်းဇယားများ", "👥 သုံးစွဲသူများ"],
        ["🎯 ကံစမ်းမဲ စီမံခန့်ခွဲမှု", "🏆 ဆုကြေးများ"],
        ["💰 ငွေလွှဲအကောင့်များ", "📞 အဆက်အသွယ်"],
        ["🚨 Alarm System", "🏠 Main Menu"]
    ], resize_keyboard=True, persistent=True)

# ==============================
# CONVERSATION HANDLER FOR PRIZE MANAGEMENT
# ==============================
def get_prize_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_1st_prize, pattern='^edit_1st_prize$'),
            CallbackQueryHandler(edit_2nd_prize, pattern='^edit_2nd_prize$'),
            CallbackQueryHandler(edit_3rd_prize, pattern='^edit_3rd_prize$'),
            CallbackQueryHandler(edit_4th_prize, pattern='^edit_4th_prize$'),
            CallbackQueryHandler(edit_other_prize, pattern='^edit_other_prize$'),
        ],
        states={
            PRIZE_NAME_1ST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_name_1st_input)],
            PRIZE_AMOUNT_1ST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_amount_1st_input)],
            PRIZE_NAME_2ND: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_name_2nd_input)],
            PRIZE_AMOUNT_2ND: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_amount_2nd_input)],
            PRIZE_NAME_3RD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_name_3rd_input)],
            PRIZE_AMOUNT_3RD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_amount_3rd_input)],
            PRIZE_NAME_4TH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_name_4th_input)],
            PRIZE_AMOUNT_4TH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_amount_4th_input)],
            PRIZE_NAME_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_name_other_input)],
            PRIZE_AMOUNT_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prize_amount_other_input)],
        },
        fallbacks=[]
    )

# ==============================
# MAIN APPLICATION
# ==============================
def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("prizes", view_prizes_command))
        application.add_handler(get_prize_conversation_handler())
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))
        application.add_handler(CallbackQueryHandler(handle_inline_buttons))
        
        print("🤖 LUCKY DRAW MYANMAR Bot with Prize Management starting...")
        print("🏆 Prize Management: Activated")
        print("🎨 Beautiful Prize Display: Enabled")
        
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()

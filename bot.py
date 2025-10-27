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
    ConversationHandler
)
from telegram.constants import ParseMode
import sqlite3
import random
from datetime import datetime
import os

# Bot Token and Admin Settings
BOT_TOKEN = "8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc"
ADMIN_USERS = [8070878424]  # Admin user ID

# Channel Links
PAYMENT_CHANNEL = "https://t.me/+C-60JUm8CKVlOTBl"
OFFICIAL_CHANNEL = "https://t.me/+_P7OHmGNs8g2MGE1"

# Conversation states for payment info
KPAY_NAME, KPAY_PHONE, WAVEPAY_NAME, WAVEPAY_PHONE, ADMIN_NAME, ADMIN_PHONE = range(6)

# System settings with your provided information
SYSTEM_SETTINGS = {
    "ticket_price": 1000,
    "auto_draw_time": "18:00",
    "auto_draw_enabled": True,
    "kpay_name": "AUNG THU HTWE",
    "kpay_phone": "09789999368",
    "wavepay_name": "AUNG THU HTWE",  
    "wavepay_phone": "09789999368",
    "admin_name": "AUNG THU HTWE",
    "admin_phone": "09789999368"
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
            CREATE TABLE IF NOT EXISTS draws (
                draw_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                numbers TEXT,
                draw_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                prize TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
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
            ('auto_draw_enabled', 'True')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        ''', default_settings)
        
        self.conn.commit()
    
    def load_settings(self):
        """Load settings from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings = cursor.fetchall()
        
        for key, value in settings:
            if key in SYSTEM_SETTINGS:
                if key in ['ticket_price']:
                    SYSTEM_SETTINGS[key] = int(value)
                elif key in ['auto_draw_enabled']:
                    SYSTEM_SETTINGS[key] = value.lower() == 'true'
                else:
                    SYSTEM_SETTINGS[key] = value
    
    def save_setting(self, key, value):
        """Save setting to database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES (?, ?)
        ''', (key, str(value)))
        self.conn.commit()
        SYSTEM_SETTINGS[key] = value

db = Database()

# ==============================
# REPLY KEYBOARDS
# ==============================
def get_main_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🎰 ကံစမ်းမဲ ဝယ်ယူရန်", "📊 ပြိုင်ပွဲများ ရလဒ်များ"],
        ["👤 My Profile", "📺 ကြော်ငြာ အပ်ရန်"],
        ["📢 Channel & Group", "👨‍💼 Admin"],
        ["🤝 Referral", "❓ FAQ"],
        ["ℹ️ About Us"]
    ], resize_keyboard=True, persistent=True)

def get_admin_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 စာရင်းဇယားများ", "👥 သုံးစွဲသူများ"],
        ["🎯 ကံစမ်းမဲ စီမံခန့်ခွဲမှု", "⚙️ ဆက်တင်များ"],
        ["💰 ငွေလွှဲအကောင့်များ", "📞 အဆက်အသွယ်"],
        ["🏠 Main Menu"]
    ], resize_keyboard=True, persistent=True)

def get_payment_management_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 KPay Name", callback_data="set_kpay_name"),
         InlineKeyboardButton("📞 KPay Phone", callback_data="set_kpay_phone")],
        [InlineKeyboardButton("💙 WavePay Name", callback_data="set_wavepay_name"),
         InlineKeyboardButton("📞 WavePay Phone", callback_data="set_wavepay_phone")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin")]
    ])

def get_contact_management_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Admin Name", callback_data="set_admin_name"),
         InlineKeyboardButton("📞 Admin Phone", callback_data="set_admin_phone")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin")]
    ])

def get_channel_keyboard():
    """Channel links keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 ငွေသွင်း/ထုတ် Alarms", url=PAYMENT_CHANNEL)],
        [InlineKeyboardButton("📢 Official Channel", url=OFFICIAL_CHANNEL)],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])

# ==============================
# ADMIN CHECK
# ==============================
def is_admin(user_id):
    return user_id in ADMIN_USERS

# ==============================
# START COMMAND
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
    
    if is_admin(user.id):
        await update.message.reply_text(
            f"👨‍💼 *Admin Panel* သို့ ကြိုဆိုပါတယ်\n\nAdmin: {SYSTEM_SETTINGS.get('admin_name', 'AUNG THU HTWE')}",
            reply_markup=get_admin_reply_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    welcome_text = f"""
┌─────────────────────────┐
│    LUCKY DRAW MYANMAR   │
└─────────────────────────┘

✨ *မင်္ဂလာပါ {user.first_name}!* ✨

ကံစမ်းမဲ ငွေစုစုပေါင်း - 10,000,000 ကျပ်

ကံစမ်းမဲကမ္ဘာထဲကို ကြိုဆိုပါတယ်။
အောက်ပါခလုတ်များဖြင့် စတင်နိုင်ပါသည်။
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# PAYMENT & CONTACT MANAGEMENT
# ==============================
async def handle_payment_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return
        
    payment_text = f"""
💳 *ငွေလွှဲအကောင့်များ စီမံခန့်ခွဲမှု*

*Current Payment Information:*

📱 *KPay:*
   - Name: {SYSTEM_SETTINGS.get('kpay_name', 'AUNG THU HTWE')}
   - Phone: {SYSTEM_SETTINGS.get('kpay_phone', '09789999368')}

💙 *WavePay:*
   - Name: {SYSTEM_SETTINGS.get('wavepay_name', 'AUNG THU HTWE')}
   - Phone: {SYSTEM_SETTINGS.get('wavepay_phone', '09789999368')}

အောက်ပါခလုတ်များဖြင့် ပြင်ဆင်နိုင်ပါသည်:
"""
    
    await update.message.reply_text(
        payment_text,
        reply_markup=get_payment_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_contact_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return
        
    contact_text = f"""
📞 *အဆက်အသွယ် အချက်အလက်များ*

*Current Contact Information:*

👤 *Admin Name:* {SYSTEM_SETTINGS.get('admin_name', 'AUNG THU HTWE')}
📞 *Admin Phone:* {SYSTEM_SETTINGS.get('admin_phone', '09789999368')}

အောက်ပါခလုတ်များဖြင့် ပြင်ဆင်နိုင်ပါသည်:
"""
    
    await update.message.reply_text(
        contact_text,
        reply_markup=get_contact_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# CHANNEL & GROUP HANDLER
# ==============================
async def handle_channel_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Channel and Group information"""
    channel_text = f"""
📢 *Channel & Group Links*

*ကျေးဇူးပြု၍ အောက်ပါ Channel များကို Join ပါ:*

• 💰 *ငွေသွင်း/ငွေထုတ် Alarms Channel* - ငွေကြေးကိစ္စများအတွက်
• 📢 *Official Channel* - အဓိကသတင်းများအတွက်

Join ပြီးမှ ဆက်လက်အသုံးပြုနိုင်ပါမည်။
"""
    
    await update.message.reply_text(
        channel_text,
        reply_markup=get_channel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# SET PAYMENT INFO
# ==============================
async def set_kpay_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📱 *KPay Account Name သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ KPay Name: {SYSTEM_SETTINGS.get('kpay_name', 'AUNG THU HTWE')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် KPay Account Name ထည့်ပါ:"
    )
    return KPAY_NAME

async def set_kpay_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *KPay Phone Number သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ KPay Phone: {SYSTEM_SETTINGS.get('kpay_phone', '09789999368')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် KPay Phone Number ထည့်ပါ (09XXXXXXXXX):"
    )
    return KPAY_PHONE

async def set_wavepay_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"💙 *WavePay Account Name သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ WavePay Name: {SYSTEM_SETTINGS.get('wavepay_name', 'AUNG THU HTWE')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် WavePay Account Name ထည့်ပါ:"
    )
    return WAVEPAY_NAME

async def set_wavepay_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *WavePay Phone Number သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ WavePay Phone: {SYSTEM_SETTINGS.get('wavepay_phone', '09789999368')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် WavePay Phone Number ထည့်ပါ (09XXXXXXXXX):"
    )
    return WAVEPAY_PHONE

async def set_admin_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"👤 *Admin Name သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ Admin Name: {SYSTEM_SETTINGS.get('admin_name', 'AUNG THU HTWE')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် Admin Name ထည့်ပါ:"
    )
    return ADMIN_NAME

async def set_admin_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *Admin Phone သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ Admin Phone: {SYSTEM_SETTINGS.get('admin_phone', '09789999368')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် Admin Phone ထည့်ပါ (09XXXXXXXXX):"
    )
    return ADMIN_PHONE

# ==============================
# HANDLE INPUTS
# ==============================
async def handle_kpay_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    kpay_name = update.message.text.strip()
    if not kpay_name:
        await update.message.reply_text("❌ KPay Account Name ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return KPAY_NAME
    
    db.save_setting('kpay_name', kpay_name)
    await update.message.reply_text(f"✅ *KPay Account Name သတ်မှတ်ပြီးပါပြီ!*\n\nအသစ် KPay Name: {kpay_name}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

async def handle_kpay_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    kpay_phone = update.message.text.strip()
    if not kpay_phone.startswith('09') or len(kpay_phone) != 11 or not kpay_phone[1:].isdigit():
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်! ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ထည့်ပါ (09XXXXXXXXX):")
        return KPAY_PHONE
    
    db.save_setting('kpay_phone', kpay_phone)
    await update.message.reply_text(f"✅ *KPay Phone Number သတ်မှတ်ပြီးပါပြီ!*\n\nအသစ် KPay Phone: {kpay_phone}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

async def handle_wavepay_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    wavepay_name = update.message.text.strip()
    if not wavepay_name:
        await update.message.reply_text("❌ WavePay Account Name ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return WAVEPAY_NAME
    
    db.save_setting('wavepay_name', wavepay_name)
    await update.message.reply_text(f"✅ *WavePay Account Name သတ်မှတ်ပြီးပါပြီ!*\n\nအသစ် WavePay Name: {wavepay_name}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

async def handle_wavepay_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    wavepay_phone = update.message.text.strip()
    if not wavepay_phone.startswith('09') or len(wavepay_phone) != 11 or not wavepay_phone[1:].isdigit():
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်! ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ထည့်ပါ (09XXXXXXXXX):")
        return WAVEPAY_PHONE
    
    db.save_setting('wavepay_phone', wavepay_phone)
    await update.message.reply_text(f"✅ *WavePay Phone Number သတ်မှတ်ပြီးပါပြီ!*\n\nအသစ် WavePay Phone: {wavepay_phone}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

async def handle_admin_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    admin_name = update.message.text.strip()
    if not admin_name:
        await update.message.reply_text("❌ Admin Name ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return ADMIN_NAME
    
    db.save_setting('admin_name', admin_name)
    await update.message.reply_text(f"✅ *Admin Name သတ်မှတ်ပြီးပါပြီ!*\n\nအသစ် Admin Name: {admin_name}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

async def handle_admin_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required")
        return ConversationHandler.END
        
    admin_phone = update.message.text.strip()
    if not admin_phone.startswith('09') or len(admin_phone) != 11 or not admin_phone[1:].isdigit():
        await update.message.reply_text("❌ မှားယွင်းနေပါသည်! ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ထည့်ပါ (09XXXXXXXXX):")
        return ADMIN_PHONE
    
    db.save_setting('admin_phone', admin_phone)
    await update.message.reply_text(f"✅ *Admin Phone သတ်မှတ်ပြီးပါပြီ!*\n\nအသစ် Admin Phone: {admin_phone}", parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# ==============================
# DEPOSIT FUNCTION
# ==============================
async def handle_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deposit_text = f"""
💵 *ငွေသွင်းရန်*

*ငွေလွှဲနည်းလမ်းများ:*

📱 *KPay:*
   - Name: {SYSTEM_SETTINGS.get('kpay_name', 'AUNG THU HTWE')}
   - Phone: {SYSTEM_SETTINGS.get('kpay_phone', '09789999368')}

💙 *WavePay:*
   - Name: {SYSTEM_SETTINGS.get('wavepay_name', 'AUNG THU HTWE')}
   - Phone: {SYSTEM_SETTINGS.get('wavepay_phone', '09789999368')}

*Contact:*
👤 Admin: {SYSTEM_SETTINGS.get('admin_name', 'AUNG THU HTWE')}
📞 Phone: {SYSTEM_SETTINGS.get('admin_phone', '09789999368')}

*Channel Links:*
💰 ငွေသွင်း/ထုတ် Alarms: {PAYMENT_CHANNEL}

ငွေလွှဲပြီးပါက Screenshot ပို့ပါ

*Admin မှ အတည်ပြုပြီးမှ Balance တက်မည်*
"""
    await update.message.reply_text(deposit_text, parse_mode=ParseMode.MARKDOWN)

# ==============================
# MAIN HANDLER
# ==============================
async def handle_reply_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        if text == "💰 ငွေလွှဲအကောင့်များ":
            await handle_payment_management(update, context)
            return
        elif text == "📞 အဆက်အသွယ်":
            await handle_contact_management(update, context)
            return
        elif text == "🏠 Main Menu":
            await start_command(update, context)
            return
    
    if text == "💵 ငွေသွင်းရန်":
        await handle_deposit(update, context)
    elif text == "👤 My Profile":
        await handle_my_profile(update, context)
    elif text == "🎰 ကံစမ်းမဲ ဝယ်ယူရန်":
        await handle_buy_tickets(update, context)
    elif text == "📢 Channel & Group":
        await handle_channel_group(update, context)

# ==============================
# INLINE BUTTON HANDLERS
# ==============================
async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_admin":
        if is_admin(query.from_user.id):
            await start_command(update, context)
        else:
            await query.message.reply_text("❌ Admin access required")
    elif data == "back_to_main":
        await start_command(update, context)

# ==============================
# PLACEHOLDER FUNCTIONS
# ==============================
async def handle_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 My Profile - Under development")

async def handle_buy_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎰 Buy Tickets - Under development")

# ==============================
# CONVERSATION HANDLER
# ==============================
def get_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(set_kpay_name, pattern='^set_kpay_name$'),
            CallbackQueryHandler(set_kpay_phone, pattern='^set_kpay_phone$'),
            CallbackQueryHandler(set_wavepay_name, pattern='^set_wavepay_name$'),
            CallbackQueryHandler(set_wavepay_phone, pattern='^set_wavepay_phone$'),
            CallbackQueryHandler(set_admin_name, pattern='^set_admin_name$'),
            CallbackQueryHandler(set_admin_phone, pattern='^set_admin_phone$'),
        ],
        states={
            KPAY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_kpay_name_input)],
            KPAY_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_kpay_phone_input)],
            WAVEPAY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wavepay_name_input)],
            WAVEPAY_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wavepay_phone_input)],
            ADMIN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_name_input)],
            ADMIN_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_phone_input)],
        },
        fallbacks=[]
    )

# ==============================
# MAIN APPLICATION
# ==============================
def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(get_conversation_handler())
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))
        app.add_handler(CallbackQueryHandler(handle_inline_buttons))
        
        print("🤖 LUCKY DRAW MYANMAR Bot starting...")
        print(f"👤 Admin ID: {ADMIN_USERS[0]}")
        print(f"📱 KPay/WavePay: {SYSTEM_SETTINGS['kpay_name']} - {SYSTEM_SETTINGS['kpay_phone']}")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()

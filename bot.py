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

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Admin users list
ADMIN_USERS = [123456789, 987654321]

# Conversation states for payment info
KPAY_NAME, KPAY_PHONE, WAVEPAY_NAME, WAVEPAY_PHONE = range(4)

# System settings with detailed payment info
SYSTEM_SETTINGS = {
    "ticket_price": 1000,
    "auto_draw_time": "18:00",
    "auto_draw_enabled": True,
    "kpay_name": "KPay Account",  # KPay account name
    "kpay_phone": "09XXXXXXXXX",  # KPay phone number
    "wavepay_name": "WavePay Account",  # WavePay account name  
    "wavepay_phone": "09XXXXXXXXX",  # WavePay phone number
    "admin_name": "Admin",
    "admin_phone": "09XXXXXXXXX"
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
    """Payment management keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 KPay Name", callback_data="set_kpay_name"),
         InlineKeyboardButton("📞 KPay Phone", callback_data="set_kpay_phone")],
        [InlineKeyboardButton("💙 WavePay Name", callback_data="set_wavepay_name"),
         InlineKeyboardButton("📞 WavePay Phone", callback_data="set_wavepay_phone")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin")]
    ])

def get_contact_management_keyboard():
    """Contact management keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Admin Name", callback_data="set_admin_name"),
         InlineKeyboardButton("📞 Admin Phone", callback_data="set_admin_phone")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin")]
    ])

# ==============================
# ADMIN CHECK DECORATOR
# ==============================
def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_USERS:
            await update.message.reply_text("❌ ဤလုပ်ဆောင်ချက်အတွက် Admin ခွင့်ပြုချက်လိုအပ်ပါသည်။")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==============================
# PAYMENT & CONTACT MANAGEMENT
# ==============================
@admin_required
async def handle_payment_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Payment account management"""
    payment_text = f"""
💳 *ငွေလွှဲအကောင့်များ စီမံခန့်ခွဲမှု*

*Current Payment Information:*

📱 *KPay:*
   - Name: {SYSTEM_SETTINGS.get('kpay_name', 'Not set')}
   - Phone: {SYSTEM_SETTINGS.get('kpay_phone', 'Not set')}

💙 *WavePay:*
   - Name: {SYSTEM_SETTINGS.get('wavepay_name', 'Not set')}
   - Phone: {SYSTEM_SETTINGS.get('wavepay_phone', 'Not set')}

အောက်ပါခလုတ်များဖြင့် ပြင်ဆင်နိုင်ပါသည်:
"""
    
    await update.message.reply_text(
        payment_text,
        reply_markup=get_payment_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@admin_required
async def handle_contact_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Contact information management"""
    contact_text = f"""
📞 *အဆက်အသွယ် အချက်အလက်များ*

*Current Contact Information:*

👤 *Admin Name:* {SYSTEM_SETTINGS.get('admin_name', 'Not set')}
📞 *Admin Phone:* {SYSTEM_SETTINGS.get('admin_phone', 'Not set')}

အောက်ပါခလုတ်များဖြင့် ပြင်ဆင်နိုင်ပါသည်:
"""
    
    await update.message.reply_text(
        contact_text,
        reply_markup=get_contact_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# SET PAYMENT INFO - KPAY
# ==============================
@admin_required
async def set_kpay_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set KPay account name"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📱 *KPay Account Name သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ KPay Name: {SYSTEM_SETTINGS.get('kpay_name', 'Not set')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် KPay Account Name ထည့်ပါ:"
    )
    return KPAY_NAME

@admin_required
async def set_kpay_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set KPay phone number"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *KPay Phone Number သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ KPay Phone: {SYSTEM_SETTINGS.get('kpay_phone', 'Not set')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် KPay Phone Number ထည့်ပါ (09XXXXXXXXX):"
    )
    return KPAY_PHONE

# ==============================
# SET PAYMENT INFO - WAVEPAY
# ==============================
@admin_required
async def set_wavepay_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set WavePay account name"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"💙 *WavePay Account Name သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ WavePay Name: {SYSTEM_SETTINGS.get('wavepay_name', 'Not set')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် WavePay Account Name ထည့်ပါ:"
    )
    return WAVEPAY_NAME

@admin_required
async def set_wavepay_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set WavePay phone number"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *WavePay Phone Number သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ WavePay Phone: {SYSTEM_SETTINGS.get('wavepay_phone', 'Not set')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် WavePay Phone Number ထည့်ပါ (09XXXXXXXXX):"
    )
    return WAVEPAY_PHONE

# ==============================
# SET CONTACT INFO
# ==============================
@admin_required
async def set_admin_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set admin name"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"👤 *Admin Name သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ Admin Name: {SYSTEM_SETTINGS.get('admin_name', 'Not set')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် Admin Name ထည့်ပါ:"
    )
    return ADMIN_NAME

@admin_required
async def set_admin_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set admin phone"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *Admin Phone သတ်မှတ်ရန်*\n\n"
        f"လက်ရှိ Admin Phone: {SYSTEM_SETTINGS.get('admin_phone', 'Not set')}\n\n"
        f"ကျေးဇူးပြု၍ အသစ် Admin Phone ထည့်ပါ (09XXXXXXXXX):"
    )
    return ADMIN_PHONE

# ==============================
# HANDLE USER INPUT FOR PAYMENT INFO
# ==============================
@admin_required
async def handle_kpay_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle KPay name input"""
    kpay_name = update.message.text.strip()
    
    if not kpay_name:
        await update.message.reply_text("❌ KPay Account Name ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return KPAY_NAME
    
    db.save_setting('kpay_name', kpay_name)
    
    await update.message.reply_text(
        f"✅ *KPay Account Name သတ်မှတ်ပြီးပါပြီ!*\n\n"
        f"အသစ် KPay Name: {kpay_name}",
        reply_markup=get_payment_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

@admin_required
async def handle_kpay_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle KPay phone input"""
    kpay_phone = update.message.text.strip()
    
    # Validate phone number format
    if not kpay_phone.startswith('09') or len(kpay_phone) != 11 or not kpay_phone[1:].isdigit():
        await update.message.reply_text(
            "❌ မှားယွင်းနေပါသည်! ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ထည့်ပါ (09XXXXXXXXX):"
        )
        return KPAY_PHONE
    
    db.save_setting('kpay_phone', kpay_phone)
    
    await update.message.reply_text(
        f"✅ *KPay Phone Number သတ်မှတ်ပြီးပါပြီ!*\n\n"
        f"အသစ် KPay Phone: {kpay_phone}",
        reply_markup=get_payment_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

@admin_required
async def handle_wavepay_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle WavePay name input"""
    wavepay_name = update.message.text.strip()
    
    if not wavepay_name:
        await update.message.reply_text("❌ WavePay Account Name ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return WAVEPAY_NAME
    
    db.save_setting('wavepay_name', wavepay_name)
    
    await update.message.reply_text(
        f"✅ *WavePay Account Name သတ်မှတ်ပြီးပါပြီ!*\n\n"
        f"အသစ် WavePay Name: {wavepay_name}",
        reply_markup=get_payment_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

@admin_required
async def handle_wavepay_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle WavePay phone input"""
    wavepay_phone = update.message.text.strip()
    
    # Validate phone number format
    if not wavepay_phone.startswith('09') or len(wavepay_phone) != 11 or not wavepay_phone[1:].isdigit():
        await update.message.reply_text(
            "❌ မှားယွင်းနေပါသည်! ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ထည့်ပါ (09XXXXXXXXX):"
        )
        return WAVEPAY_PHONE
    
    db.save_setting('wavepay_phone', wavepay_phone)
    
    await update.message.reply_text(
        f"✅ *WavePay Phone Number သတ်မှတ်ပြီးပါပြီ!*\n\n"
        f"အသစ် WavePay Phone: {wavepay_phone}",
        reply_markup=get_payment_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

@admin_required
async def handle_admin_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin name input"""
    admin_name = update.message.text.strip()
    
    if not admin_name:
        await update.message.reply_text("❌ Admin Name ထည့်သွင်းရန်လိုအပ်ပါသည်။")
        return ADMIN_NAME
    
    db.save_setting('admin_name', admin_name)
    
    await update.message.reply_text(
        f"✅ *Admin Name သတ်မှတ်ပြီးပါပြီ!*\n\n"
        f"အသစ် Admin Name: {admin_name}",
        reply_markup=get_contact_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

@admin_required
async def handle_admin_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin phone input"""
    admin_phone = update.message.text.strip()
    
    # Validate phone number format
    if not admin_phone.startswith('09') or len(admin_phone) != 11 or not admin_phone[1:].isdigit():
        await update.message.reply_text(
            "❌ မှားယွင်းနေပါသည်! ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ထည့်ပါ (09XXXXXXXXX):"
        )
        return ADMIN_PHONE
    
    db.save_setting('admin_phone', admin_phone)
    
    await update.message.reply_text(
        f"✅ *Admin Phone သတ်မှတ်ပြီးပါပြီ!*\n\n"
        f"အသစ် Admin Phone: {admin_phone}",
        reply_markup=get_contact_management_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

# ==============================
# UPDATED DEPOSIT FUNCTION
# ==============================
async def handle_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ငွေသွင်းရန် - Admin သတ်မှတ်ထားသော payment information ဖြင့်"""
    deposit_text = f"""
💵 *ငွေသွင်းရန်*

*ငွေလွှဲနည်းလမ်းများ:*

📱 *KPay:*
   - Name: {SYSTEM_SETTINGS.get('kpay_name', 'KPay Account')}
   - Phone: {SYSTEM_SETTINGS.get('kpay_phone', '09XXXXXXXXX')}

💙 *WavePay:*
   - Name: {SYSTEM_SETTINGS.get('wavepay_name', 'WavePay Account')}
   - Phone: {SYSTEM_SETTINGS.get('wavepay_phone', '09XXXXXXXXX')}

*Contact:*
👤 Admin: {SYSTEM_SETTINGS.get('admin_name', 'Admin')}
📞 Phone: {SYSTEM_SETTINGS.get('admin_phone', '09XXXXXXXXX')}

ငွေလွှဲပြီးပါက Screenshot ပို့ပါ

*Admin မှ အတည်ပြုပြီးမှ Balance တက်မည်*
"""
    await update.message.reply_text(
        deposit_text,
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# MAIN REPLY BUTTON HANDLER
# ==============================
async def handle_reply_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # Admin panel routes
    if user_id in ADMIN_USERS:
        if text == "💰 ငွေလွှဲအကောင့်များ":
            await handle_payment_management(update, context)
            return
        elif text == "📞 အဆက်အသွယ်":
            await handle_contact_management(update, context)
            return
        elif text == "🏠 Main Menu":
            await start_command(update, context)
            return
    
    # Normal user routes
    if text == "💵 ငွေသွင်းရန်":
        await handle_deposit(update, context)

# ==============================
# INLINE BUTTON HANDLERS
# ==============================
async def handle_admin_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_USERS:
        await query.message.reply_text("❌ Admin access required")
        return
    
    data = query.data
    
    if data == "set_kpay_name":
        await set_kpay_name(update, context)
    elif data == "set_kpay_phone":
        await set_kpay_phone(update, context)
    elif data == "set_wavepay_name":
        await set_wavepay_name(update, context)
    elif data == "set_wavepay_phone":
        await set_wavepay_phone(update, context)
    elif data == "set_admin_name":
        await set_admin_name(update, context)
    elif data == "set_admin_phone":
        await set_admin_phone(update, context)
    elif data == "back_to_admin":
        await start_command(update, context)

# ==============================
# CONVERSATION HANDLER
# ==============================
def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_admin_inline_buttons, pattern='^(set_kpay_name|set_kpay_phone|set_wavepay_name|set_wavepay_phone|set_admin_name|set_admin_phone)$')],
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
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    
    # Admin conversation handler
    app.add_handler(get_admin_conversation_handler())
    
    # Reply keyboard handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))
    
    # Inline button handlers
    app.add_handler(CallbackQueryHandler(handle_admin_inline_buttons))
    
    print("🎰 LUCKY DRAW MYANMAR Bot with Customizable Payment Details is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

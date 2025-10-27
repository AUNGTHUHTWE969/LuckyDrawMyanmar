import logging
import sqlite3
from datetime import datetime
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Updater, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    Filters,
    ConversationHandler,
    CallbackContext
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token and Admin Settings
BOT_TOKEN = "8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc"
ADMIN_USERS = [8070878424]

# Conversation states
DEPOSIT_NAME, DEPOSIT_PHONE, DEPOSIT_AMOUNT, DEPOSIT_SCREENSHOT = range(4)
WITHDRAW_NAME, WITHDRAW_METHOD, WITHDRAW_PHONE, WITHDRAW_AMOUNT = range(4, 8)

# System settings
SYSTEM_SETTINGS = {
    "ticket_price": 1000,
    "kpay_name": "AUNG THU HTWE",
    "kpay_phone": "09789999368",
    "wavepay_name": "AUNG THU HTWE",  
    "wavepay_phone": "09789999368",
}

# ==============================
# DATABASE SETUP
# ==============================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('luckydraw.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
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
        
        # Deposit requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposit_requests (
                deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                user_phone TEXT,
                amount INTEGER,
                screenshot_file_id TEXT,
                status TEXT DEFAULT 'pending',
                admin_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                processed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Withdraw requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                withdraw_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                payment_method TEXT,
                phone_number TEXT,
                amount INTEGER,
                status TEXT DEFAULT 'pending',
                admin_note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                processed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def create_deposit_request(self, user_id, user_name, user_phone, amount, screenshot_file_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO deposit_requests 
            (user_id, user_name, user_phone, amount, screenshot_file_id) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, user_name, user_phone, amount, screenshot_file_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def create_withdraw_request(self, user_id, user_name, payment_method, phone_number, amount):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO withdraw_requests 
            (user_id, user_name, payment_method, phone_number, amount) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, user_name, payment_method, phone_number, amount))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_deposit_status(self, deposit_id, status, admin_id, note=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE deposit_requests 
            SET status = ?, processed_at = CURRENT_TIMESTAMP, 
                processed_by = ?, admin_note = ?
            WHERE deposit_id = ?
        ''', (status, admin_id, note, deposit_id))
        
        if status == 'approved':
            cursor.execute('SELECT user_id, amount FROM deposit_requests WHERE deposit_id = ?', (deposit_id,))
            result = cursor.fetchone()
            if result:
                user_id, amount = result
                cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        
        self.conn.commit()
    
    def update_withdraw_status(self, withdraw_id, status, admin_id, note=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE withdraw_requests 
            SET status = ?, processed_at = CURRENT_TIMESTAMP, 
                processed_by = ?, admin_note = ?
            WHERE withdraw_id = ?
        ''', (status, admin_id, note, withdraw_id))
        
        if status == 'approved':
            cursor.execute('SELECT user_id, amount FROM withdraw_requests WHERE withdraw_id = ?', (withdraw_id,))
            result = cursor.fetchone()
            if result:
                user_id, amount = result
                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        
        self.conn.commit()
    
    def get_pending_deposits(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT deposit_id, user_id, user_name, user_phone, amount, screenshot_file_id, created_at
            FROM deposit_requests 
            WHERE status = 'pending'
            ORDER BY created_at DESC
        ''')
        return cursor.fetchall()
    
    def get_pending_withdraws(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT withdraw_id, user_id, user_name, payment_method, phone_number, amount, created_at
            FROM withdraw_requests 
            WHERE status = 'pending'
            ORDER BY created_at DESC
        ''')
        return cursor.fetchall()

db = Database()

# ==============================
# REPLY KEYBOARDS
# ==============================
def get_main_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🎰 ကံစမ်းမဲ ဝယ်ယူရန်", "🏆 ဆုကြေးများကြည့်ရန်"],
        ["💵 ငွေသွင်းရန်", "💰 ငွေထုတ်ရန်"],
        ["👤 ကျွန်တော့်ပရိုဖိုင်", "📊 ရလဒ်များကြည့်ရန်"]
    ], resize_keyboard=True)

def get_admin_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 စာရင်းဇယားများ", "👥 သုံးစွဲသူများ"],
        ["💳 ငွေသွင်းမှုများ", "💸 ငွေထုတ်မှုများ"],
        ["🏆 ဆုကြေးများ", "⚙️ ဆက်တင်များ"],
        ["🏠 Main Menu"]
    ], resize_keyboard=True)

# ==============================
# SIMPLE START COMMAND
# ==============================
def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    
    # Create user if not exists
    cursor = db.conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) 
        VALUES (?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, user.last_name))
    db.conn.commit()
    
    if user.id in ADMIN_USERS:
        update.message.reply_text(
            "👨‍💼 *Admin Panel* သို့ ကြိုဆိုပါတယ်",
            reply_markup=get_admin_reply_keyboard(),
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            "🎰 *LUCKY DRAW MYANMAR* မှ ကြိုဆိုပါတယ်!\n\n"
            "အောက်ပါခလုတ်များဖြင့် စတင်အသုံးပြုနိုင်ပါသည်။",
            reply_markup=get_main_reply_keyboard(),
            parse_mode='Markdown'
        )

# ==============================
# DEPOSIT SYSTEM
# ==============================
def handle_deposit_start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "💵 *ငွေသွင်းရန်*\n\nကျေးဇူးပြု၍ သင့်အမည်ထည့်ပါ:",
        parse_mode='Markdown'
    )
    return DEPOSIT_NAME

def handle_deposit_name(update: Update, context: CallbackContext):
    context.user_data['deposit_name'] = update.message.text
    update.message.reply_text(
        "📞 *ကျေးဇူးပြု၍ သင့်ဖုန်းနံပါတ်ထည့်ပါ:*\nဥပမာ: 09123456789",
        parse_mode='Markdown'
    )
    return DEPOSIT_PHONE

def handle_deposit_phone(update: Update, context: CallbackContext):
    phone = update.message.text
    if not phone.startswith('09') or len(phone) != 11:
        update.message.reply_text("❌ ဖုန်းနံပါတ် မှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ ပြန်ထည့်ပါ။")
        return DEPOSIT_PHONE
    
    context.user_data['deposit_phone'] = phone
    update.message.reply_text(
        "💰 *သွင်းလိုသောငွေပမာဏ ထည့်ပါ:*\nဥပမာ: 10000",
        parse_mode='Markdown'
    )
    return DEPOSIT_AMOUNT

def handle_deposit_amount(update: Update, context: CallbackContext):
    try:
        amount = int(update.message.text)
        if amount < 1000:
            update.message.reply_text("❌ အနည်းဆုံး 1000 ကျပ် သွင်းရန် လိုအပ်ပါသည်။")
            return DEPOSIT_AMOUNT
        
        context.user_data['deposit_amount'] = amount
        update.message.reply_text(
            "📸 *ကျေးဇူးပြု၍ ငွေလွှဲပြီး Screenshot ပို့ပါ:*\n\n"
            f"📱 KPay: {SYSTEM_SETTINGS['kpay_phone']} ({SYSTEM_SETTINGS['kpay_name']})\n"
            f"💙 WavePay: {SYSTEM_SETTINGS['wavepay_phone']} ({SYSTEM_SETTINGS['wavepay_name']})",
            parse_mode='Markdown'
        )
        return DEPOSIT_SCREENSHOT
    except ValueError:
        update.message.reply_text("❌ ငွေပမာဏ မှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ ဂဏန်းဖြင့်ထည့်ပါ။")
        return DEPOSIT_AMOUNT

def handle_deposit_screenshot(update: Update, context: CallbackContext):
    if not update.message.photo:
        update.message.reply_text("❌ ကျေးဇူးပြု၍ Screenshot ပုံတစ်ပုံ ပို့ပါ။")
        return DEPOSIT_SCREENSHOT
    
    # Get the largest photo
    photo_file = update.message.photo[-1].get_file()
    file_id = photo_file.file_id
    
    user_id = update.effective_user.id
    deposit_id = db.create_deposit_request(
        user_id=user_id,
        user_name=context.user_data['deposit_name'],
        user_phone=context.user_data['deposit_phone'],
        amount=context.user_data['deposit_amount'],
        screenshot_file_id=file_id
    )
    
    update.message.reply_text(
        f"✅ *ငွေသွင်းမှု လက်ခံရရှိပါသည်!*\n\n"
        f"📝 အမည်: {context.user_data['deposit_name']}\n"
        f"📞 ဖုန်း: {context.user_data['deposit_phone']}\n"
        f"💰 ပမာဏ: {context.user_data['deposit_amount']} Ks\n\n"
        f"⏳ Admin မှ အတည်ပြုပြီးမှ Balance တက်မည်။",
        reply_markup=get_main_reply_keyboard(),
        parse_mode='Markdown'
    )
    
    # Notify admins
    notify_admins_about_deposit(
        context.bot, deposit_id, user_id,
        context.user_data['deposit_name'],
        context.user_data['deposit_phone'],
        context.user_data['deposit_amount'],
        file_id
    )
    
    context.user_data.clear()
    return ConversationHandler.END

# ==============================
# WITHDRAW SYSTEM
# ==============================
def handle_withdraw_start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "💰 *ငွေထုတ်ရန်*\n\nကျေးဇူးပြု၍ သင့်အမည်ထည့်ပါ:",
        parse_mode='Markdown'
    )
    return WITHDRAW_NAME

def handle_withdraw_name(update: Update, context: CallbackContext):
    context.user_data['withdraw_name'] = update.message.text
    
    keyboard = ReplyKeyboardMarkup([
        ["📱 KPay", "💙 WavePay"],
        ["🔙 နောက်သို့"]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    update.message.reply_text(
        "💳 *ငွေလွှဲနည်းလမ်း ရွေးချယ်ပါ:*",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return WITHDRAW_METHOD

def handle_withdraw_method(update: Update, context: CallbackContext):
    method = update.message.text
    if method not in ["📱 KPay", "💙 WavePay"]:
        update.message.reply_text("❌ ကျေးဇူးပြု၍ ငွေလွှဲနည်းလမ်း ရွေးချယ်ပါ။")
        return WITHDRAW_METHOD
    
    context.user_data['withdraw_method'] = "KPay" if method == "📱 KPay" else "WavePay"
    
    update.message.reply_text(
        f"📞 *{context.user_data['withdraw_method']} ဖုန်းနံပါတ် ထည့်ပါ:*\nဥပမာ: 09123456789",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    return WITHDRAW_PHONE

def handle_withdraw_phone(update: Update, context: CallbackContext):
    phone = update.message.text
    if not phone.startswith('09') or len(phone) != 11:
        update.message.reply_text("❌ ဖုန်းနံပါတ် မှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ ပြန်ထည့်ပါ။")
        return WITHDRAW_PHONE
    
    context.user_data['withdraw_phone'] = phone
    update.message.reply_text(
        "💰 *ထုတ်လိုသောငွေပမာဏ ထည့်ပါ:*\nဥပမာ: 10000\n\n⚠️ အနည်းဆုံး 1000 ကျပ်",
        parse_mode='Markdown'
    )
    return WITHDRAW_AMOUNT

def handle_withdraw_amount(update: Update, context: CallbackContext):
    try:
        amount = int(update.message.text)
        if amount < 1000:
            update.message.reply_text("❌ အနည်းဆုံး 1000 ကျပ် ထုတ်ရန် လိုအပ်ပါသည်။")
            return WITHDRAW_AMOUNT
        
        user_id = update.effective_user.id
        cursor = db.conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        user_balance = result[0] if result else 0
        
        if amount > user_balance:
            update.message.reply_text(
                f"❌ သင့်လက်ကျန်ငွေ မလုံလောက်ပါ။\n"
                f"💳 လက်ကျန်ငွေ: {user_balance} Ks\n"
                f"💰 ထုတ်လိုငွေ: {amount} Ks"
            )
            return WITHDRAW_AMOUNT
        
        withdraw_id = db.create_withdraw_request(
            user_id=user_id,
            user_name=context.user_data['withdraw_name'],
            payment_method=context.user_data['withdraw_method'],
            phone_number=context.user_data['withdraw_phone'],
            amount=amount
        )
        
        update.message.reply_text(
            f"✅ *ငွေထုတ်မှု လက်ခံရရှိပါသည်!*\n\n"
            f"📝 အမည်: {context.user_data['withdraw_name']}\n"
            f"💳 နည်းလမ်း: {context.user_data['withdraw_method']}\n"
            f"📞 ဖုန်း: {context.user_data['withdraw_phone']}\n"
            f"💰 ပမာဏ: {amount} Ks\n\n"
            f"⏳ Admin မှ အတည်ပြုပြီးမှ ငွေထုတ်ပေးမည်။",
            reply_markup=get_main_reply_keyboard(),
            parse_mode='Markdown'
        )
        
        notify_admins_about_withdraw(
            context.bot, withdraw_id, user_id,
            context.user_data['withdraw_name'],
            context.user_data['withdraw_method'],
            context.user_data['withdraw_phone'],
            amount
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        update.message.reply_text("❌ ငွေပမာဏ မှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ ဂဏန်းဖြင့်ထည့်ပါ။")
        return WITHDRAW_AMOUNT

# ==============================
# ADMIN NOTIFICATIONS
# ==============================
def notify_admins_about_deposit(bot, deposit_id, user_id, name, phone, amount, screenshot_file_id):
    message_text = f"""
🚨 *အသစ်ငွေသွင်းမှု* 🚨

📝 အမည်: {name}
📞 ဖုန်း: {phone}
💰 ပမာဏ: {amount} Ks
👤 User ID: {user_id}
📅 ရက်စွဲ: {datetime.now().strftime("%Y-%m-%d %H:%M")}
🆔 Deposit ID: #{deposit_id}
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ အတည်ပြုမည်", callback_data=f"approve_deposit_{deposit_id}"),
         InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data=f"reject_deposit_{deposit_id}")],
        [InlineKeyboardButton("⏳ စောင့်ဆိုင်းမည်", callback_data=f"pending_deposit_{deposit_id}")]
    ])
    
    for admin_id in ADMIN_USERS:
        try:
            bot.send_photo(
                chat_id=admin_id,
                photo=screenshot_file_id,
                caption=message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

def notify_admins_about_withdraw(bot, withdraw_id, user_id, name, method, phone, amount):
    message_text = f"""
🚨 *အသစ်ငွေထုတ်မှု* 🚨

📝 အမည်: {name}
💳 နည်းလမ်း: {method}
📞 ဖုန်း: {phone}
💰 ပမာဏ: {amount} Ks
👤 User ID: {user_id}
📅 ရက်စွဲ: {datetime.now().strftime("%Y-%m-%d %H:%M")}
🆔 Withdraw ID: #{withdraw_id}
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ အတည်ပြုမည်", callback_data=f"approve_withdraw_{withdraw_id}"),
         InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data=f"reject_withdraw_{withdraw_id}")],
        [InlineKeyboardButton("⏳ စောင့်ဆိုင်းမည်", callback_data=f"pending_withdraw_{withdraw_id}")]
    ])
    
    for admin_id in ADMIN_USERS:
        try:
            bot.send_message(
                chat_id=admin_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to notify admin {admin_id}: {e}")

# ==============================
# ADMIN PANEL HANDLERS
# ==============================
def handle_deposit_management(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_USERS:
        update.message.reply_text("❌ Admin access required")
        return
    
    pending_deposits = db.get_pending_deposits()
    
    if not pending_deposits:
        update.message.reply_text("✅ စောင့်ဆိုင်းနေသော ငွေသွင်းမှုမရှိပါ။")
        return
    
    message_text = f"💳 *စောင့်ဆိုင်းနေသော ငွေသွင်းမှုများ - {len(pending_deposits)} ခု*\n\n"
    
    for deposit in pending_deposits[:5]:
        deposit_id, user_id, name, phone, amount, screenshot_id, created_at = deposit
        message_text += f"🆔 #{deposit_id} | {name} | {amount} Ks\n"
        message_text += f"📞 {phone} | 📅 {created_at[:16]}\n\n"
    
    update.message.reply_text(message_text, parse_mode='Markdown')

def handle_withdraw_management(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMIN_USERS:
        update.message.reply_text("❌ Admin access required")
        return
    
    pending_withdraws = db.get_pending_withdraws()
    
    if not pending_withdraws:
        update.message.reply_text("✅ စောင့်ဆိုင်းနေသော ငွေထုတ်မှုမရှိပါ။")
        return
    
    message_text = f"💸 *စောင့်ဆိုင်းနေသော ငွေထုတ်မှုများ - {len(pending_withdraws)} ခု*\n\n"
    
    for withdraw in pending_withdraws[:5]:
        withdraw_id, user_id, name, method, phone, amount, created_at = withdraw
        message_text += f"🆔 #{withdraw_id} | {name} | {amount} Ks\n"
        message_text += f"💳 {method} | 📞 {phone}\n"
        message_text += f"📅 {created_at[:16]}\n\n"
    
    update.message.reply_text(message_text, parse_mode='Markdown')

# ==============================
# ADMIN APPROVAL HANDLERS
# ==============================
def handle_admin_approval(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.from_user.id not in ADMIN_USERS:
        query.message.reply_text("❌ Admin access required")
        return
    
    data = query.data
    
    if data.startswith('approve_deposit_'):
        deposit_id = int(data.split('_')[2])
        db.update_deposit_status(deposit_id, 'approved', query.from_user.id)
        query.edit_message_caption(
            caption=query.message.caption + f"\n\n✅ *အတည်ပြုပြီးပါပြီ!*\n👨‍💼 Admin: {query.from_user.first_name}",
            parse_mode='Markdown'
        )
        
    elif data.startswith('reject_deposit_'):
        deposit_id = int(data.split('_')[2])
        db.update_deposit_status(deposit_id, 'rejected', query.from_user.id, "ပယ်ဖျက်ထားသည်")
        query.edit_message_caption(
            caption=query.message.caption + f"\n\n❌ *ပယ်ဖျက်ပြီးပါပြီ!*\n👨‍💼 Admin: {query.from_user.first_name}",
            parse_mode='Markdown'
        )
        
    elif data.startswith('approve_withdraw_'):
        withdraw_id = int(data.split('_')[2])
        db.update_withdraw_status(withdraw_id, 'approved', query.from_user.id)
        query.edit_message_text(
            text=query.message.text + f"\n\n✅ *အတည်ပြုပြီးပါပြီ!*\n👨‍💼 Admin: {query.from_user.first_name}",
            parse_mode='Markdown'
        )
        
    elif data.startswith('reject_withdraw_'):
        withdraw_id = int(data.split('_')[2])
        db.update_withdraw_status(withdraw_id, 'rejected', query.from_user.id, "ပယ်ဖျက်ထားသည်")
        query.edit_message_text(
            text=query.message.text + f"\n\n❌ *ပယ်ဖျက်ပြီးပါပြီ!*\n👨‍💼 Admin: {query.from_user.first_name}",
            parse_mode='Markdown'
        )

# ==============================
# MAIN HANDLER
# ==============================
def handle_reply_buttons(update: Update, context: CallbackContext):
    text = update.message.text
    user_id = update.effective_user.id
    
    if user_id in ADMIN_USERS:
        if text == "💳 ငွေသွင်းမှုများ":
            handle_deposit_management(update, context)
            return
        elif text == "💸 ငွေထုတ်မှုများ":
            handle_withdraw_management(update, context)
            return
        elif text == "🏠 Main Menu":
            start_command(update, context)
            return
    
    if text == "💵 ငွေသွင်းရန်":
        handle_deposit_start(update, context)
    elif text == "💰 ငွေထုတ်ရန်":
        handle_withdraw_start(update, context)
    elif text == "🏆 ဆုကြေးများကြည့်ရန်":
        show_prizes(update, context)
    elif text == "👤 ကျွန်တော့်ပရိုဖိုင်":
        show_profile(update, context)

# ==============================
# SIMPLE PLACEHOLDER FUNCTIONS
# ==============================
def show_prizes(update: Update, context: CallbackContext):
    prize_text = """
🏆 *LUCKY DRAW MYANMAR - ဆုကြေးများ* 🏆

🥇 ဆုကြီး - 10,000,000 Ks
🥈 ဒုတိယဆု - 5,000,000 Ks  
🥉 တတိယဆု - 1,000,000 Ks
🎯 စတုတ္ထဆု - 500,000 Ks
🎁 ပဉ္စမဆု - 100,000 Ks

💰 တစ်ကြိမ်လျှင် 1000 ကျပ်
⏰ နေ့စဉ်ကံစမ်းမဲထွက်ချိန်: 18:00
"""
    update.message.reply_text(prize_text, parse_mode='Markdown')

def show_profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cursor = db.conn.cursor()
    cursor.execute("SELECT first_name, balance, tickets FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        name, balance, tickets = result
        profile_text = f"""
👤 *သင့်ပရိုဖိုင်*

📝 အမည်: {name}
💳 လက်ကျန်ငွေ: {balance} Ks
🎫 ကံစမ်းမဲ: {tickets} tickets
        """
    else:
        profile_text = "👤 *သင့်ပရိုဖိုင်*\n\nအချက်အလက်များ မတွေ့ရှိပါ။"
    
    update.message.reply_text(profile_text, parse_mode='Markdown')

# ==============================
# CONVERSATION HANDLERS
# ==============================
def get_deposit_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^💵 ငွေသွင်းရန်$'), handle_deposit_start)],
        states={
            DEPOSIT_NAME: [MessageHandler(Filters.text & ~Filters.command, handle_deposit_name)],
            DEPOSIT_PHONE: [MessageHandler(Filters.text & ~Filters.command, handle_deposit_phone)],
            DEPOSIT_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_deposit_amount)],
            DEPOSIT_SCREENSHOT: [MessageHandler(Filters.photo, handle_deposit_screenshot)],
        },
        fallbacks=[]
    )

def get_withdraw_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^💰 ငွေထုတ်ရန်$'), handle_withdraw_start)],
        states={
            WITHDRAW_NAME: [MessageHandler(Filters.text & ~Filters.command, handle_withdraw_name)],
            WITHDRAW_METHOD: [MessageHandler(Filters.text & ~Filters.command, handle_withdraw_method)],
            WITHDRAW_PHONE: [MessageHandler(Filters.text & ~Filters.command, handle_withdraw_phone)],
            WITHDRAW_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, handle_withdraw_amount)],
        },
        fallbacks=[]
    )

# ==============================
# MAIN APPLICATION
# ==============================
def main():
    try:
        updater = Updater(BOT_TOKEN)
        dispatcher = updater.dispatcher
        
        # Add handlers
        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(get_deposit_conversation_handler())
        dispatcher.add_handler(get_withdraw_conversation_handler())
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_reply_buttons))
        dispatcher.add_handler(CallbackQueryHandler(handle_admin_approval))
        
        print("🤖 LUCKY DRAW MYANMAR Bot starting...")
        print("✅ Payment System: Activated")
        print("👨‍💼 Admin Panel: Ready")
        
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()

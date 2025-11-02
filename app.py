from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import datetime
import random
import logging

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database
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

# Channel & Group Database
channels = {
    "transaction_channel": "https://t.me/+C-60JUm8CKVlOTBl",
    "admin_channel": "https://t.me/+_P7OHmGNs8g2MGE1",
    "official_channel": "@official_channel"
}

groups = {}

# Transaction Database
transactions = {}
transaction_counter = 1

# FAQ Database - Admin can edit these
faq_data = {
    "register_how": "Register ပြုလုပ်နည်း",
    "register_answer": "……………",
    "deposit_how": "ငွေသွင်းနည်း", 
    "deposit_answer": "……………",
    "withdraw_how": "ငွေထုတ်နည်း",
    "withdraw_answer": "…………..",
    "lottery_how": "ကံစမ်းမဲ ဝယ်ယူနည်း",
    "lottery_answer": "…………..",
    "extra1_question": "+",
    "extra1_answer": "+",
    "extra2_question": "+", 
    "extra2_answer": "+",
    "extra3_question": "+",
    "extra3_answer": "+"
}

# About Us Database - Admin can edit this
about_us_data = {
    "content": "အကြောင်းအရာ ရေးရန်"
}

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

def get_user_transactions(user_id):
    user_txns = []
    for txn_id, txn_data in transactions.items():
        if txn_data['user_id'] == user_id:
            user_txns.append(txn_data)
    user_txns.sort(key=lambda x: x['created_at'], reverse=True)
    return user_txns

def get_pending_transactions():
    pending_txns = []
    for txn_id, txn_data in transactions.items():
        if txn_data['status'] == 'pending':
            pending_txns.append(txn_data)
    pending_txns.sort(key=lambda x: x['created_at'])
    return pending_txns

def get_today_transactions():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    today_txns = []
    for txn_id, txn_data in transactions.items():
        if txn_data['created_at'].startswith(today):
            today_txns.append(txn_data)
    return today_txns

# Desktop Keyboards - UPDATED WITH NEW BUTTONS
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

def admin_main_keyboard():
    keyboard = [
        ["📊 စနစ်စစ်တမ်း", "👥 အသုံးပြုသူများ"],
        ["💰 ငွေသွင်းအကောင့်များ", "🔍 စောင့်ဆိုင်းငွေလွှဲမှုများ"],
        ["📺 Channel & Group များ", "📈 ယနေ့အစီရင်ခံ"],
        ["⚙️ Admin စီမံခန့်ခွဲမှု", "🏠 ပင်မမီနူး"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# Inline Keyboards
def deposit_method_inline():
    keyboard = [
        [
            InlineKeyboardButton("📱 KPay", callback_data="deposit_kpay"),
            InlineKeyboardButton("📱 WavePay", callback_data="deposit_wavepay")
        ],
        [InlineKeyboardButton("🔙 နောက်သို့", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def withdraw_method_inline():
    keyboard = [
        [
            InlineKeyboardButton("📱 KPay", callback_data="withdraw_kpay"),
            InlineKeyboardButton("📱 WavePay", callback_data="withdraw_wavepay")
        ],
        [InlineKeyboardButton("🔙 နောက်သို့", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def lottery_tickets_inline():
    keyboard = [
        [
            InlineKeyboardButton("1 Ticket", callback_data="buy_1_ticket"),
            InlineKeyboardButton("2 Tickets", callback_data="buy_2_tickets")
        ],
        [
            InlineKeyboardButton("5 Tickets", callback_data="buy_5_tickets"),
            InlineKeyboardButton("7 Tickets", callback_data="buy_7_tickets")
        ],
        [InlineKeyboardButton("🎫 မိမိကြိုက်နှစ်သက်ရာ ဝယ်ယူရန် Tickets", callback_data="buy_custom_tickets")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def competition_results_inline():
    keyboard = [
        [InlineKeyboardButton("နေ့စဉ် ကံထူးရှင်ဆု ရလာဒ်များ", callback_data="daily_results")],
        [InlineKeyboardButton("လစဉ် ကံထူးရှင်ဆု ရလာဒ်များ", callback_data="monthly_results")],
        [InlineKeyboardButton("နှစ်စဉ် ကံထူးရှင်ဆု ရလာဒ်များ", callback_data="yearly_results")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def advertise_inline():
    keyboard = [
        [InlineKeyboardButton("မိမိ channel / groups", callback_data="ad_channel_input")],
        [InlineKeyboardButton("Link ထည့်ရန်", callback_data="ad_link_input")],
        [InlineKeyboardButton("ဖုန်းနံပါတ်", callback_data="ad_phone_input")],
        [InlineKeyboardButton("ဖုန်းနံပါတ် ထည့်ရန်", callback_data="ad_phone_enter")],
        [InlineKeyboardButton("ရက်ရွေးရန်", callback_data="ad_select_days")],
        [InlineKeyboardButton("…… Days", callback_data="ad_days_input")],
        [InlineKeyboardButton("Total amount", callback_data="ad_total_amount")],
        [InlineKeyboardButton("………. Ks", callback_data="ad_amount_input")],
        [InlineKeyboardButton("ငွေလွှဲရန်", callback_data="ad_payment_method")],
        [InlineKeyboardButton("ငွေလွှဲ ပြီး Screenshot ထည့်ရန်", callback_data="ad_upload_screenshot")],
        [
            InlineKeyboardButton("Kpay", callback_data="ad_kpay"),
            InlineKeyboardButton("Wavepay", callback_data="ad_wavepay")
        ],
        [
            InlineKeyboardButton("အတည်ပြုရန်", callback_data="ad_confirm"),
            InlineKeyboardButton("ပယ်ဖျက်ရန်", callback_data="ad_cancel"),
            InlineKeyboardButton("ပြန်လည်ပြင်ဆင်ရန်", callback_data="ad_edit")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("⚙️ Admin", callback_data="admin_main"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def channel_group_inline():
    keyboard = [
        [InlineKeyboardButton("Official Channel", url="https://t.me/official_channel")],
        [InlineKeyboardButton("JOIN", url="https://t.me/official_channel")],
        [InlineKeyboardButton("Group", url="https://t.me/discussion_group")],
        [InlineKeyboardButton("JOIN", url="https://t.me/discussion_group")],
        [InlineKeyboardButton("ငွေသွင်း / ငွေထုတ် Channel", url="https://t.me/transaction_channel")],
        [InlineKeyboardButton("JOIN", url="https://t.me/transaction_channel")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_contact_inline():
    keyboard = [
        [InlineKeyboardButton("စကားပြောရန်", url="https://t.me/Admin")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def referral_inline():
    keyboard = [
        [
            InlineKeyboardButton("Referral", callback_data="referral_info"),
            InlineKeyboardButton(".....Link.....", callback_data="referral_link")
        ],
        [
            InlineKeyboardButton("Total", callback_data="referral_total"),
            InlineKeyboardButton("........ ယောက်", callback_data="referral_count")
        ],
        [
            InlineKeyboardButton("Referral Earnings", callback_data="referral_earnings"),
            InlineKeyboardButton("..........KS", callback_data="referral_amount")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def faq_inline():
    keyboard = [
        [
            InlineKeyboardButton(faq_data["register_how"], callback_data="faq_register"),
            InlineKeyboardButton(faq_data["register_answer"], callback_data="faq_register")
        ],
        [
            InlineKeyboardButton(faq_data["deposit_how"], callback_data="faq_deposit"),
            InlineKeyboardButton(faq_data["deposit_answer"], callback_data="faq_deposit")
        ],
        [
            InlineKeyboardButton(faq_data["withdraw_how"], callback_data="faq_withdraw"),
            InlineKeyboardButton(faq_data["withdraw_answer"], callback_data="faq_withdraw")
        ],
        [
            InlineKeyboardButton(faq_data["lottery_how"], callback_data="faq_lottery"),
            InlineKeyboardButton(faq_data["lottery_answer"], callback_data="faq_lottery")
        ],
        [
            InlineKeyboardButton(faq_data["extra1_question"], callback_data="faq_extra1"),
            InlineKeyboardButton(faq_data["extra1_answer"], callback_data="faq_extra1")
        ],
        [
            InlineKeyboardButton(faq_data["extra2_question"], callback_data="faq_extra2"),
            InlineKeyboardButton(faq_data["extra2_answer"], callback_data="faq_extra2")
        ],
        [
            InlineKeyboardButton(faq_data["extra3_question"], callback_data="faq_extra3"),
            InlineKeyboardButton(faq_data["extra3_answer"], callback_data="faq_extra3")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def about_us_inline():
    keyboard = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="main_menu"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in users:
        user_data = users[user_id]
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(
                f"👋 ပြန်လည်ကြိုဆိုပါတယ် {user_data['full_name']}!",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                f"👋 ပြန်လည်ကြိုဆိုပါတယ် {user_data['full_name']}!",
                reply_markup=main_menu_keyboard()
            )
    else:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(
                "မှတ်ပုံတင်ရန် /register ကိုနှိပ်ပါ",
                reply_markup=ReplyKeyboardMarkup([["/register"]], resize_keyboard=True)
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
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(
                "✅ သင်မှတ်ပုံတင်ပြီးသားဖြစ်ပါသည်!",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "✅ သင်မှတ်ပုံတင်ပြီးသားဖြစ်ပါသည်!",
                reply_markup=main_menu_keyboard()
            )
        return
        
    context.user_data['register_step'] = 'name'
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text("👤 ကျေးဇူးပြု၍ သင့်နာမည်ကိုရိုက်ထည့်ပါ:")
    else:
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

# Profile Function - UPDATED
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        else:
            await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        return
        
    user_data = users[user_id]
    
    # Create profile message with the requested format
    message = f"""
👤 **My Profile**

**NAME**
{user_data['full_name']}

**PH NO.**
{user_data['phone']}

**Register Date** 
{user_data['registered_at']}

**Balance**
{user_data['balance']:,} Ks

**Referral Code**
{user_data['referral_code']}

**Referral Earnings**
{user_data['total_earnings']:,} Ks
"""
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Main Application
def main():
    # Bot Token
    BOT_TOKEN = "8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc"
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        print("🤖 Bot is starting...")
        print("✅ Bot is running successfully!")
        print("🚀 Press Ctrl+C to stop the bot")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()

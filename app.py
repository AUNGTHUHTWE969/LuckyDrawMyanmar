from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import datetime
import random
import logging
import os
import asyncio
from flask import Flask

# Flask app for health check
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database (in-memory for demo)
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

# FAQ Database
faq_data = {
    "register_how": "Register ပြုလုပ်နည်း",
    "register_answer": "Start ကိုနှိပ်ပြီး Register လုပ်ပါ",
    "deposit_how": "ငွေသွင်းနည်း", 
    "deposit_answer": "ငွေသွင်းမီနူးမှ ရွေးချယ်ပါ",
    "withdraw_how": "ငွေထုတ်နည်း",
    "withdraw_answer": "ငွေထုတ်မီနူးမှ ရွေးချယ်ပါ",
}

# About Us Database
about_us_data = {
    "content": "ကျွန်ုပ်တို့၏ စနစ်သည် စိတ်ချရသော ငွေကြေးလွှဲပြောင်းမှုအတွက် ရည်ရွယ်ပါသည်"
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

# Desktop Keyboards
def main_menu_keyboard():
    keyboard = [
        ["👤 My Profile", "🎫 ကံစမ်းမဲ ဝယ်ယူရန်"],
        ["📊 မှတ်တမ်းကြည့်ရန️်", "💳 လက်ကျန်ကြည့်ရန်"],
        ["💰 ငွေသွင်း", "📤 ငွေထုတ်"],
        ["🏠 ပင်မမီနူး"]
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

# Profile Function
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        return
        
    user_data = users[user_id]
    
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
"""
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown'
    )

# Deposit System
async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("❌ ငွေသွင်းရန် မှတ်ပုံတင်ရန်လိုအပ်ပါသည်")
        return
    
    await update.message.reply_text(
        "ငွေသွင်းနည်းလမ်းရွေးပါ:",
        reply_markup=deposit_method_inline()
    )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("❌ ငွေထုတ်ရန် မှတ်ပုံတင်ရန်လိုအပ်ပါသည်")
        return
    
    await update.message.reply_text(
        "ငွေထုတ်နည်းလမ်းရွေးပါ:",
        reply_markup=withdraw_method_inline()
    )

async def process_deposit_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    query = update.callback_query
    await query.answer()
    
    account = get_random_account(method)
    
    if not account:
        await query.message.reply_text(f"❌ {method.upper()} account မရှိသေးပါ")
        return
    
    context.user_data['pending_deposit'] = {
        'method': method,
        'account': account
    }
    
    message = f"""
💰 {method.upper()} ငွေသွင်းရန်:

👤 အကောင့်အမည်: {account['account_name']}
📞 အကောင့်နံပါတ်: {account['phone_number']}

ကျေးဇူးပြု၍ သွင်းမည့်ငွေပမာဏကို ရိုက်ထည့်ပါ:
ဥပမာ: 10000
"""
    await query.message.reply_text(message)

async def process_withdraw_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = users[user_id]
    
    context.user_data['pending_withdraw'] = {
        'method': method
    }
    
    await query.message.reply_text(
        f"📤 {method.upper()} ဖြင့်ငွေထုတ်ယူမည့်ပမာဏရိုက်ထည့်ပါ:\n"
        f"လက်ရှိလက်ကျန်: {user_data['balance']:,} Ks"
    )

# Handle Deposit Amount
async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_deposit' not in context.user_data:
        return
    
    try:
        amount = int(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ ငွေပမာဏသည် 0 ထက်ကြီးရမည်")
            return
        
        deposit_info = context.user_data['pending_deposit']
        method = deposit_info['method']
        account = deposit_info['account']
        
        txn_id = create_transaction(
            user_id=update.effective_user.id,
            amount=amount,
            transaction_type="deposit",
            payment_method=method
        )
        
        message = f"""
⏳ **ငွေသွင်းမှုတောင်းဆိုချက် လက်ခံရရှိပါသည်**

📋 **သင့်ငွေသွင်းမှုအချက်အလက်:**
├ 💰 ငွေပမာဏ: {amount:,} Ks
├ 📱 ငွေသွင်းနည်း: {method.upper()}
├ 👤 လွှဲပြောင်းရမည့်အမည်: {account['account_name']}
├ 📞 လွှဲပြောင်းရမည့်ဖုန်း: {account['phone_number']}
└ 🔢 လုပ်ဆောင်ချက်နံပါတ်: `{txn_id}`

💡 **ကျေးဇူးပြု၍ အောက်ပါအဆင့်များအတိုင်းဆောင်ရွက်ပါ:**
1. {method.upper()} ဖြင့် ငွေလွှဲပါ
2. ငွေလွှဲ Screenshot ရိုက်ယူပါ
3. Screenshot ကိုဤဘော့သို့ပို့ပါ

🕒 **Admin မှစစ်ဆေးအတည်ပြုချိန်:** 2-5 မိနစ်
"""
        await update.message.reply_text(message)
        
        del context.user_data['pending_deposit']
        
    except ValueError:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းဖြစ်သောငွေပမာဏရိုက်ထည့်ပါ")

# Handle Withdraw Amount
async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_withdraw' not in context.user_data:
        return
    
    try:
        amount = int(update.message.text)
        user_id = update.effective_user.id
        user_data = users[user_id]
        
        if amount <= 0:
            await update.message.reply_text("❌ ငွေပမာဏသည် 0 ထက်ကြီးရမည်")
            return
            
        if user_data['balance'] < amount:
            await update.message.reply_text(f"❌ လက်ကျန်ငွေမလုံလောက်ပါ။\n💳 သင့်လက်ကျန်ငွေ: {user_data['balance']:,} Ks")
            return
        
        withdraw_info = context.user_data['pending_withdraw']
        method = withdraw_info['method']
        
        txn_id = create_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type="withdraw",
            payment_method=method
        )
        
        message = f"""
⏳ **ငွေထုတ်ယူမှုတောင်းဆိုချက် လက်ခံရရှိပါသည်**

📋 **သင့်ငွေထုတ်မှုအချက်အလက်:**
├ 💰 ထုတ်ယူမည့်ပမာဏ: {amount:,} Ks
├ 📱 ငွေလက်ခံမည့်နည်း: {method.upper()}
├ 👤 သင့်အမည်: {user_data['full_name']}
├ 💳 လက်ရှိလက်ကျန်: {user_data['balance']:,} Ks
└ 🔢 လုပ်ဆောင်ချက်နံပါတ်: `{txn_id}`

🕒 **Admin မှစစ်ဆေးအတည်ပြုချိန်:** 2-5 မိနစ်
"""
        await update.message.reply_text(message)
        
        del context.user_data['pending_withdraw']
        
    except ValueError:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းဖြစ်သောငွေပမာဏရိုက်ထည့်ပါ")

# Check Balance
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        return
        
    user_data = users[user_id]
    await update.message.reply_text(f"💳 သင့်လက်ကျန်ငွေ: {user_data['balance']:,} Ks")

# Transaction History
async def transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        return
    
    user_txns = get_user_transactions(user_id)
    user_data = users[user_id]
    
    if not user_txns:
        message = """
📊 **သင့်ငွေသွင်း/ထုတ်မှတ်တမ်းများ**

📝 **မည်သည့်ငွေသွင်း/ထုတ်မှတ်တမ်းမျှမရှိသေးပါ**

💡 **စတင်ငွေသွင်းရန် ငွေသွင်းခလုတ်ကိုနှိပ်ပါ**
"""
        await update.message.reply_text(message)
        return
    
    message = f"""
📊 **သင့်ငွေသွင်း/ထုတ်မှတ်တမ်းများ**

💳 **လက်ရှိလက်ကျန်ငွေ:** {user_data['balance']:,} Ks
📈 **စုစုပေါင်းငွေသွင်း/ထုတ်မှုရေတွက်ချက်:** {len(user_txns)} ကြိမ်

🔢 **နောက်ဆုံးလုပ်ဆောင်ချက်များ:**
"""
    
    for txn in user_txns[:5]:
        status_emoji = "⏳" if txn['status'] == 'pending' else "✅" if txn['status'] == 'approved' else "❌"
        type_emoji = "💰" if txn['type'] == 'deposit' else "📤"
        type_text = "ငွေသွင်း" if txn['type'] == 'deposit' else "ငွေထုတ်"
        status_text = "စောင့်ဆိုင်းနေ" if txn['status'] == 'pending' else "အောင်မြင်ပြီ" if txn['status'] == 'approved' else "ပယ်ဖျက်ပြီ"
        
        message += f"\n{type_emoji} **{type_text}** {status_emoji}"
        message += f"\n├ 💵 {txn['amount']:,} Ks"
        message += f"\n├ 📱 {txn['payment_method'].upper()}"
        message += f"\n├ 🔢 {txn['id']}"
        message += f"\n└ 📊 {status_text}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# Message Handler for Users
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "/start":
        await start(update, context)
    elif text == "/register":
        await register(update, context)
    elif 'register_step' in context.user_data:
        await handle_register_steps(update, context)
    elif text == "👤 My Profile":
        await profile(update, context)
    elif text == "📊 မှတ်တမ်းကြည့်ရန️်":
        await transaction_history(update, context)
    elif text == "💳 လက်ကျန်ကြည့်ရန်":
        await check_balance(update, context)
    elif text == "💰 ငွေသွင်း":
        await deposit_menu(update, context)
    elif text == "📤 ငွေထုတ်":
        await withdraw_menu(update, context)
    elif text == "🏠 ပင်မမီနူး":
        await start(update, context)
    elif 'pending_deposit' in context.user_data:
        await handle_deposit_amount(update, context)
    elif 'pending_withdraw' in context.user_data:
        await handle_withdraw_amount(update, context)

# Callback Query Handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    if data == "main_menu":
        await start(update, context)
    elif data == "deposit_menu":
        await deposit_menu(update, context)
    elif data == "withdraw_menu":
        await withdraw_menu(update, context)
    elif data == "check_balance":
        await check_balance(update, context)
    elif data == "transaction_history":
        await transaction_history(update, context)
    elif data == "deposit_kpay":
        await process_deposit_selection(update, context, "kpay")
    elif data == "deposit_wavepay":
        await process_deposit_selection(update, context, "wavepay")
    elif data == "withdraw_kpay":
        await process_withdraw_selection(update, context, "kpay")
    elif data == "withdraw_wavepay":
        await process_withdraw_selection(update, context, "wavepay")

# Main Bot Function
async def run_bot():
    # Bot Token from environment variable
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is not set")
        return
    
    try:
        # Create Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        application.add_handler(CommandHandler("balance", check_balance))
        application.add_handler(CommandHandler("history", transaction_history))
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        logger.info("🤖 Bot is starting...")
        
        # Start the Bot
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")

# Run Flask app and bot together
def main():
    import threading
    
    # Run Flask in a separate thread
    def run_flask():
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
    
    # Run bot in main thread
    def run_bot_sync():
        asyncio.run(run_bot())
    
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("🚀 Starting Telegram Bot on Render...")
    
    # Run bot in main thread
    run_bot_sync()

if __name__ == '__main__':
    main()

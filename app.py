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

# FAQ Database
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

# About Us Database
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

# FIXED: Notify Admins Function
async def notify_admins_new_transaction(context: ContextTypes.DEFAULT_TYPE, transaction):
    for admin_id in admins:
        try:
            status_emoji = "⏳" if transaction['status'] == 'pending' else "✅" if transaction['status'] == 'approved' else "❌"
            transaction_type = "ငွေသွင်း" if transaction['type'] == 'deposit' else "ငွေထုတ်"
            
            account_info = ""
            if transaction['type'] == 'deposit':
                for account in payment_accounts.get(transaction['payment_method'], []):
                    if account['phone_number'] in [acc['phone_number'] for acc in payment_accounts[transaction['payment_method']]]:
                        account_info = f"👤 လွှဲရမည့်အမည်: {account['account_holder']}"
                        break
            
            message = f"""
🆕 **အသစ်ငွေလွှဲမှု**

{status_emoji} **အခြေအနေ:** {transaction['status']}
👤 **အသုံးပြုသူ:** {transaction['user_name']}
📞 **ဖုန်း:** {transaction['user_phone']}
💰 **ပမာဏ:** {transaction['amount']:,} Ks
📱 **အမျိုးအစား:** {transaction_type}
💳 **နည်းလမ်း:** {transaction['payment_method'].upper()}
{account_info}
🔢 **ငွေလွှဲနံပါတ်:** {transaction['id']}
⏰ **အချိန်:** {transaction['created_at']}

**Admin စစ်ဆေးရန်:**
• ငွေလွှဲ Screenshot စစ်ဆေးပါ
• ငွေလွှဲသူအမည် ကိုက်ညီမှုရှိမရှိစစ်ဆေးပါ
• ငွေပမာဏ ကိုက်ညီမှုရှိမရှိစစ်ဆေးပါ

/admin ဖြင့်စီမံခန့်ခွဲနိုင်ပါသည်
"""
            await context.bot.send_message(chat_id=admin_id, text=message)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# FIXED: Notify User Transaction Approved
async def notify_user_transaction_approved(context: ContextTypes.DEFAULT_TYPE, txn_id: str):
    txn = transactions.get(txn_id)
    if not txn:
        return
    
    user_id = txn['user_id']
    user_data = users[user_id]
    
    if txn['type'] == 'deposit':
        message = f"""
✅ **သင့်ငွေသွင်းမှု အတည်ပြုပြီးပါပြီ!**

🎉 **ငွေသွင်းမှုအောင်မြင်စွာပြီးစီးပါပြီ**

📋 **အချက်အလက်များ:**
├ 🔢 ငွေသွင်းနံပါတ်: `{txn_id}`
├ 💰 သွင်းငွေပမာဏ: {txn['amount']:,} Ks
├ 📱 ငွေသွင်းနည်း: {txn['payment_method'].upper()}
├ ⏰ အတည်ပြုချိန်: {txn['processed_at']}
└ 👨‍💼 အတည်ပြုသူ: Admin

💳 **လက်ရှိလက်ကျန်ငွေ:** {user_data['balance']:,} Ks

🌟 **ကျေးဇူးတင်ပါတယ်! နောက်တစ်ကြိမ်ထပ်မံငွေသွင်းနိုင်ပါသည်**
"""
    else:
        message = f"""
✅ **သင့်ငွေထုတ်ယူမှု အတည်ပြုပြီးပါပြီ!**

🎉 **ငွေထုတ်ယူမှုအောင်မြင်စွာပြီး�စီးပါပြီ**

📋 **အချက်အလက်များ:**
├ 🔢 ငွေထုတ်နံပါတ်: `{txn_id}`
├ 💰 ထုတ်ယူငွေပမာဏ: {txn['amount']:,} Ks
├ 📱 ငွေလက်ခံနည်း: {txn['payment_method'].upper()}
├ ⏰ အတည်ပြုချိန်: {txn['processed_at']}
└ 👨‍💼 အတည်ပြုသူ: Admin

💳 **လက်ရှိလက်ကျန်ငွေ:** {user_data['balance']:,} Ks

💸 **သင့်ငွေအား {txn['payment_method'].upper()} သို့ လွှဲပြောင်းပေးပါမည်**

🌟 **ကျေးဇူးတင်ပါတယ်! နောက်တစ်ကြိမ်ထပ်မံအသုံးပြုနိုင်ပါသည်**
"""
    
    keyboard = [
        [InlineKeyboardButton("💰 ထပ်မံငွေသွင်းရန်", callback_data="deposit_menu")],
        [InlineKeyboardButton("📤 ထပ်မံငွေထုတ်ရန်", callback_data="withdraw_menu")],
        [InlineKeyboardButton("💳 လက်ကျန်ကြည့်ရန်", callback_data="check_balance")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message, 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

# FIXED: Notify User Transaction Rejected
async def notify_user_transaction_rejected(context: ContextTypes.DEFAULT_TYPE, txn_id: str, reason: str):
    txn = transactions.get(txn_id)
    if not txn:
        return
    
    user_id = txn['user_id']
    user_data = users[user_id]
    
    transaction_type = "ငွေသွင်း" if txn['type'] == 'deposit' else "ငွေထုတ်"
    
    message = f"""
❌ **သင့်{transaction_type}မှု ပယ်ဖျက်ခံရပါသည်**

😔 **ဝမ်းနည်းပါတယ်၊ သင့်{transaction_type}မှုကိုပယ်ဖျက်လိုက်ရပါတယ်**

📋 **အချက်အလက်များ:**
├ 🔢 ငွေလွှဲနံပါတ်: `{txn_id}`
├ 💰 ငွေပမာဏ: {txn['amount']:,} Ks
├ 📱 ငွေလွှဲနည်း: {txn['payment_method'].upper()}
├ 📝 ပယ်ဖျက်ရသည့်အကြောင်း: {reason}
└ ⏰ ပယ်ဖျက်ချိန်: {txn['processed_at']}

💡 **ညွှန်ကြားချက်များ:**
• {transaction_type}မှုပြန်လုပ်လိုပါက အောက်ပါခလုတ်ကိုနှိပ်ပါ
• ပြဿနာရှိပါက Admin နှင့်ဆက်သွယ်ပါ

💳 **လက်ရှိလက်ကျန်ငွေ:** {user_data['balance']:,} Ks
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💰 {transaction_type}မှုပြန်လုပ်ရန်", callback_data="deposit_menu" if txn['type'] == 'deposit' else "withdraw_menu")],
        [InlineKeyboardButton("📞 Admin နှင့်ဆက်သွယ်ရန်", url="https://t.me/Admin")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message, 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

# FIXED: Handle Deposit Amount Function
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
├ 👑 လွှဲရမည့်အမည်: **{account['account_holder']}**
└ 🔢 လုပ်ဆောင်ချက်နံပါတ်: `{txn_id}`

💡 **ကျေးဇူးပြု၍ အောက်ပါအဆင့်များအတိုင်းဆောင်ရွက်ပါ:**
1. {method.upper()} ဖြင့် ငွေလွှဲပါ
2. **ငွေလွှဲသည့်သူ၏အမည်ကို {account['account_holder']} အတိုင်းရေးပါ**
3. ငွေလွှဲ Screenshot ရိုက်ယူပါ
4. Screenshot ကိုဤဘော့သို့ပို့ပါ

🕒 **Admin မှစစ်ဆေးအတည်ပြုချိန်:** 2-5 မိနစ်

📞 **အကူအညီလိုပါက Admin နှင့်ဆက်သွယ်ပါ**
"""
        await update.message.reply_text(message)
        
        # FIXED: Use context.bot instead of context.application
        await notify_admins_new_transaction(context, transactions[txn_id])
        
        del context.user_data['pending_deposit']
        
    except ValueError:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းဖြစ်သောငွေပမာဏရိုက်ထည့်ပါ")

# FIXED: Handle Withdraw Amount Function
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
├ 📞 သင့်ဖုန်းနံပါတ်: {user_data['phone']}
├ 💳 လက်ရှိလက်ကျန်: {user_data['balance']:,} Ks
└ 🔢 လုပ်ဆောင်ချက်နံပါတ်: `{txn_id}`

🕒 **Admin မှစစ်ဆေးအတည်ပြုချိန်:** 2-5 မိနစ်

💡 **ငွေထုတ်ယူမှုအောင်မြင်ပါက သင့်လက်ကျန်:** {user_data['balance'] - amount:,} Ks

📞 **အကူအညီလိုပါက Admin နှင့်ဆက်သွယ်ပါ**
"""
        await update.message.reply_text(message)
        
        # FIXED: Use context.bot instead of context.application
        await notify_admins_new_transaction(context, transactions[txn_id])
        
        del context.user_data['pending_withdraw']
        
    except ValueError:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းဖြစ်သောငွေပမာဏရိုက်ထည့်ပါ")

# Desktop Keyboards
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

# Main function
def main():
    # Bot Token
    BOT_TOKEN = "8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc"
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        application.add_handler(CommandHandler("admin", start))  # Temporary
        
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        print("🤖 Bot is starting...")
        print("✅ Bot is running successfully!")
        print("🚀 Press Ctrl+C to stop the bot")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        print(f"❌ Error: {e}")

# Message Handler for Users
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await handle_admin_messages(update, context)
        return
        
    text = update.message.text
    
    if text == "/start":
        await start(update, context)
    elif text == "/register":
        await register(update, context)
    elif 'register_step' in context.user_data:
        await handle_register_steps(update, context)
    elif text == "👤 My Profile":
        await profile(update, context)
    elif text == "💰 ငွေသွင်း":
        await deposit_menu(update, context)
    elif text == "📤 ငွေထုတ်":
        await withdraw_menu(update, context)
    elif text == "📊 မှတ်တမ်းကြည့်ရန်":
        await transaction_history(update, context)
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
    elif data == "deposit_kpay":
        await process_deposit_selection(update, context, "kpay")
    elif data == "deposit_wavepay":
        await process_deposit_selection(update, context, "wavepay")
    elif data == "withdraw_kpay":
        await process_withdraw_selection(update, context, "kpay")
    elif data == "withdraw_wavepay":
        await process_withdraw_selection(update, context, "wavepay")

# Deposit and Withdraw menus
async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("❌ ငွေသွင်းရန် မှတ်ပုံတင်ရန်လိုအပ်ပါသည်")
        else:
            await update.message.reply_text("❌ ငွေသွင်းရန် မှတ်ပုံတင်ရန်လိုအပ်ပါသည်")
        return
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text(
            "ငွေသွင်းနည်းလမ်းရွေးပါ:",
            reply_markup=deposit_method_inline()
        )
    else:
        await update.message.reply_text(
            "ငွေသွင်းနည်းလမ်းရွေးပါ:",
            reply_markup=deposit_method_inline()
        )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("❌ ငွေထုတ်ရန် မှတ်ပုံတင်ရန်လိုအပ်ပါသည်")
        else:
            await update.message.reply_text("❌ ငွေထုတ်ရန် မှတ်ပုံတင်ရန်လိုအပ်ပါသည်")
        return
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text(
            "ငွေထုတ်နည်းလမ်းရွေးပါ:",
            reply_markup=withdraw_method_inline()
        )
    else:
        await update.message.reply_text(
            "ငွေထုတ်နည်းလမ်းရွေးပါ:",
            reply_markup=withdraw_method_inline()
        )

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

# Process deposit/withdraw selection
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

# Profile function
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        else:
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

**Referral Earnings**
{user_data['total_earnings']:,} Ks
"""
    
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

# Transaction History
async def transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        else:
            await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        return
    
    user_txns = get_user_transactions(user_id)
    user_data = users[user_id]
    
    if not user_txns:
        message = """
📊 **သင့်ငွေသွင်း/ထုတ်မှတ်တမ်းများ**

📝 **မည်သည့်ငွေသွင်း/ထုတ်မှတ်တမ်းမျှမရှိသေးပါ**

💡 **စတင်ငွေသွင်းရန် အောက်ပါခလုတ်ကိုနှိပ်ပါ**
"""
        keyboard = [
            [InlineKeyboardButton("💰 ငွေသွင်းရန်", callback_data="deposit_menu")],
            [InlineKeyboardButton("💳 လက်ကျန်ကြည့်ရန်", callback_data="check_balance")]
        ]
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
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
        message += f"\n├ 🕒 {txn['created_at']}"
        message += f"\n└ 📊 {status_text}\n"
    
    if len(user_txns) > 5:
        message += f"\n📋 ... နှင့် အခြား {len(user_txns) - 5} ခု"
    
    keyboard = [
        [InlineKeyboardButton("💰 ငွေသွင်းရန်", callback_data="deposit_menu"),
         InlineKeyboardButton("📤 ငွေထုတ်ရန်", callback_data="withdraw_menu")],
        [InlineKeyboardButton("💳 လက်ကျန်ကြည့်ရန်", callback_data="check_balance"),
         InlineKeyboardButton("🔄 မှတ်တမ်းပြန်စစ်ရန်", callback_data="transaction_history")]
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

# Check Balance
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        else:
            await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ")
        return
        
    user_data = users[user_id]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text(f"💳 သင့်လက်ကျန်ငွေ: {user_data['balance']:,} Ks")
    else:
        await update.message.reply_text(f"💳 သင့်လက်ကျန်ငွေ: {user_data['balance']:,} Ks")

# Admin message handler (simplified)
async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
        
    text = update.message.text
    
    if text == "/start" or text == "🏠 ပင်မမီနူး":
        await start(update, context)
    elif text == "/admin":
        await admin_panel(update, context)

# Admin panel (simplified)
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text("❌ Admin သာဝင်ရောက်နိုင်သည်")
        return
        
    admin_data = admins[update.effective_user.id]
    
    message = f"""
🔧 **Admin Panel**

👨‍💼 **Admin:** {admin_data['username']}
📅 **ဝင်ရောက်သည့်ရက်:** {admin_data['added_date']}
🎯 **အဆင့်:** {admin_data['level']}

**ရနိုင်သော commands များ:**
• 📊 စနစ်စစ်တမ်း - စနစ်စာရင်းဇယားများ
• 👥 အသုံးပြုသူများ - အသုံးပြုသူအားလုံးကြည့်ရန်

**အမြန်စစ်တမ်း:**
• အသုံးပြုသူများ: {len(users)}
• စောင့်ဆိုင်းငွေလွှဲမှုများ: {len(get_pending_transactions())}
• ယနေ့ငွေလွှဲမှုများ: {len(get_today_transactions())}
"""
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.reply_text(
            message,
            reply_markup=admin_main_keyboard()
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=admin_main_keyboard()
        )

if __name__ == '__main__':
    main()

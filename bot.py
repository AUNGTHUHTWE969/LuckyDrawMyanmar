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
    filters
)
from telegram.constants import ParseMode

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ==============================
# REPLY KEYBOARD (DESKBOARD BUTTONS)
# ==============================
def get_main_reply_keyboard():
    """ပင်မရှေ့သို့/နောက်သို့ ခလုတ်များ"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎰 ကံစမ်းမဲထုတ်မယ်"), KeyboardButton("📊 ရလဒ်ကြည့်မယ်")],
        [KeyboardButton("👤 အကောင့်"), KeyboardButton("🏆 ဆုကြေးများ")],
        [KeyboardButton("🆘 အကူအညီ"), KeyboardButton("⚙️ ဆက်တင်")]
    ], resize_keyboard=True, persistent=True)

def get_back_reply_keyboard():
    """နောက်သို့ပြန်ရန် ခလုတ်"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔙 နောက်သို့")]
    ], resize_keyboard=True, persistent=True)

def get_auth_reply_keyboard():
    """Login/Register ခလုတ်များ"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📝 အကောင့်အသစ်ဖွင့်မယ်"), KeyboardButton("🔐 အကောင့်ဝင်မယ်")],
        [KeyboardButton("🔙 နောက်သို့")]
    ], resize_keyboard=True, persistent=True)

# ==============================
# INLINE KEYBOARDS
# ==============================
def get_main_inline_keyboard():
    """ပင်မ Inline ခလုတ်များ"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 စတင်ရန်", callback_data="get_started")],
        [InlineKeyboardButton("📱 ဆက်သွယ်ရန်", url="https://t.me/youradmin")],
        [InlineKeyboardButton("ℹ️ အကူအညီ", callback_data="help")]
    ])

def get_register_inline_keyboard():
    """Register Inline ခလုတ်များ"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ အတည်ပြုမည်", callback_data="confirm_register")],
        [InlineKeyboardButton("✏️ ပြန်လည်ပြင်ဆင်မည်", callback_data="edit_register")],
        [InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data="cancel_register")]
    ])

def get_login_inline_keyboard():
    """Login Inline ခလုတ်များ"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 OTP ရယူမည်", callback_data="get_otp")],
        [InlineKeyboardButton("📧 လိပ်စာမေ့နေပါသလား", callback_data="forgot_email")],
        [InlineKeyboardButton("🔑 လျှို့ဝှက်နံပါတ် မေ့နေပါသလား", callback_data="forgot_password")]
    ])

def get_navigation_inline_keyboard():
    """ရှေ့သို့/နောက်သို့ Inline ခလုတ်များ"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data="prev_page"),
            InlineKeyboardButton("➡️ နောက်သို့", callback_data="next_page")
        ],
        [InlineKeyboardButton("🏠 ပင်မစာမျက်နှာ", callback_data="main_menu")]
    ])

# ==============================
# BOT HANDLERS - START & MAIN
# ==============================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အစပြုခြင်း"""
    user = update.effective_user
    
    welcome_text = f"""
┌─────────────────────────┐
│    🎊 LUCKY DRAW MYANMAR   │
└─────────────────────────┘

✨ *မင်္ဂလာပါ {user.first_name}!* ✨

ကံစမ်းမဲကမ္ဘာထဲကို ကြိုဆိုပါတယ်။ 
အောက်ပါခလုတ်များဖြင့် စတင်နိုင်ပါသည်။
"""
    
    # Inline buttons for quick actions
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_inline_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Reply keyboard for main navigation (always visible)
    await update.message.reply_text(
        "👇 *အောက်ပါခလုတ်များကို နှိပ်၍ ဆက်လက်လုပ်ဆောင်ပါ*",
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# REPLY KEYBOARD HANDLERS
# ==============================
async def handle_reply_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply keyboard buttons များကိုကိုင်တွယ်ခြင်း"""
    text = update.message.text
    
    if text == "🎰 ကံစမ်းမဲထုတ်မယ်":
        await handle_lottery_draw(update, context)
    elif text == "📊 ရလဒ်ကြည့်မယ်":
        await handle_view_results(update, context)
    elif text == "👤 အကောင့်":
        await handle_account(update, context)
    elif text == "🏆 ဆုကြေးများ":
        await handle_prizes(update, context)
    elif text == "🆘 အကူအညီ":
        await handle_help(update, context)
    elif text == "⚙️ ဆက်တင်":
        await handle_settings(update, context)
    elif text == "🔙 နောက်သို့":
        await handle_back(update, context)
    elif text == "📝 အကောင့်အသစ်ဖွင့်မယ်":
        await handle_register_start(update, context)
    elif text == "🔐 အကောင့်ဝင်မယ်":
        await handle_login_start(update, context)

# ==============================
# INLINE BUTTON HANDLERS
# ==============================
async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline buttons များကိုကိုင်တွယ်ခြင်း"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "get_started":
        await handle_get_started(query, context)
    elif data == "help":
        await handle_help_inline(query, context)
    elif data == "confirm_register":
        await handle_confirm_register(query, context)
    elif data == "edit_register":
        await handle_edit_register(query, context)
    elif data == "cancel_register":
        await handle_cancel_register(query, context)
    elif data == "get_otp":
        await handle_get_otp(query, context)
    elif data == "forgot_email":
        await handle_forgot_email(query, context)
    elif data == "forgot_password":
        await handle_forgot_password(query, context)
    elif data == "prev_page":
        await handle_prev_page(query, context)
    elif data == "next_page":
        await handle_next_page(query, context)
    elif data == "main_menu":
        await handle_main_menu(query, context)

# ==============================
# SPECIFIC HANDLERS
# ==============================
async def handle_get_started(query, context):
    """စတင်ရန် inline button"""
    await query.edit_message_text(
        "🎯 *ကံစမ်းမဲစတင်ရန် ပြင်ဆင်ပြီးပါပြီ!*\n\n"
        "အောက်ပါခလုတ်များမှ ရွေးချယ်နိုင်ပါသည်။",
        reply_markup=get_auth_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register စတင်ခြင်း"""
    register_text = """
┌─────────────────────────┐
│   📝 အကောင့်အသစ်ဖွင့်ရန်   │
└─────────────────────────┘

*ကျေးဇူးပြု၍ သင့်အီးမေးလ်လိပ်စာထည့်ပါ:*
"""
    
    await update.message.reply_text(
        register_text,
        reply_markup=get_back_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Login စတင်ခြင်း"""
    login_text = """
┌─────────────────────────┐
│      🔐 အကောင့်ဝင်ရန်     │
└─────────────────────────┘

*ကျေးဇူးပြု၍ သင့်အီးမေးလ် (သို့) ဖုန်းနံပါတ်ထည့်ပါ:*
"""
    
    await update.message.reply_text(
        login_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 OTP ဖြင့်ဝင်မည်", callback_data="get_otp")],
            [InlineKeyboardButton("🔐 လျှို့ဝှက်နံပါတ်ဖြင့်ဝင်မည်", callback_data="password_login")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_lottery_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ကံစမ်းမဲထုတ်ခြင်း"""
    await update.message.reply_text(
        "🎰 *ကံစမ်းမဲထုတ်ယူခြင်း*\n\n"
        "သင့်ကံစမ်းမဲဂဏန်းများ: 12 - 25 - 07 - 33 - 41 - 18\n\n"
        "🍀 *ကံကောင်းပါစေ!*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 နောက်တစ်ကြိမ်ထပ်ကံစမ်းမယ်", callback_data="draw_again")],
            [InlineKeyboardButton("📊 ရလဒ်များကြည့်မယ်", callback_data="view_results")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အကောင့်စီမံခန့်ခွဲခြင်း"""
    await update.message.reply_text(
        "👤 *သင့်အကောင့်အချက်အလက်များ*\n\n"
        "📧 အီးမေးလ်: user@example.com\n"
        "📱 ဖုန်းနံပါတ်: 09XXXXXXXXX\n"
        "🎰 ကံစမ်းမဲအရေအတွက်: 15\n"
        "🏆 ဆုရရှိမှု: 3\n\n"
        "အောက်ပါခလုတ်များဖြင့် စီမံနိုင်ပါသည်:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ အချက်အလက်ပြင်မယ်", callback_data="edit_profile")],
            [InlineKeyboardButton("🔐 လျှို့ဝှက်နံပါတ်ပြောင်းမယ်", callback_data="change_password")],
            [InlineKeyboardButton("📱 ဖုန်းနံပါတ်ပြောင်းမယ်", callback_data="change_phone")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """နောက်သို့ပြန်ခြင်း"""
    await update.message.reply_text(
        "🏠 *ပင်မမီနူးသို့ ပြန်လာပြီ*\n\n"
        "အောက်ပါခလုတ်များမှ ရွေးချယ်နိုင်ပါသည်:",
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_main_menu(query, context):
    """ပင်မမီနူးသို့ပြန်ခြင်း"""
    await query.edit_message_text(
        "🏠 *ပင်မမီနူးသို့ ပြန်လာပြီ*\n\n"
        "အောက်ပါခလုတ်များမှ ရွေးချယ်နိုင်ပါသည်:",
        reply_markup=get_main_inline_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# OTHER HANDLERS (Placeholders)
# ==============================
async def handle_view_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 ရလဒ်များကြည့်ရှုခြင်း...")

async def handle_prizes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 ဆုကြေးများကြည့်ရှုခြင်း...")

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 အကူအညီ...")

async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ ဆက်တင်...")

async def handle_help_inline(query, context):
    await query.edit_message_text("ℹ️ အကူအညီ...")

# ==============================
# MAIN APPLICATION
# ==============================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    
    # Reply keyboard handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_buttons))
    
    # Inline button handlers
    app.add_handler(CallbackQueryHandler(handle_inline_buttons))
    
    print("🎰 LUCKY DRAW MYANMAR Bot is running with proper UI/UX...")
    app.run_polling()

if __name__ == "__main__":
    main()

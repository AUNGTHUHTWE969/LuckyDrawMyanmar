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
# REPLY KEYBOARD (ပုံထဲက အတိုင်း)
# ==============================
def get_main_reply_keyboard():
    """ပုံထဲက ဒက်စ်ဘုတ် ခလုတ်များ"""
    return ReplyKeyboardMarkup([
        ["🎰 ကံစမ်းမဲထုတ်မယ်", "📊 ရလဒ်ကြည့်မယ်"],
        ["👤 ကျွန်တော့်ပရိုဖိုင်", "🏆 ဆုကြေးများ"],
        ["📺 ချန်နယ်နှင့်အုပ်စု", "👨‍💼 Admin"],
        ["🤝 Referral", "❓ FAQ"],
        ["ℹ️ About Us"]
    ], resize_keyboard=True, persistent=True)

# ==============================
# BOT HANDLERS
# ==============================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အစပြုခြင်း"""
    user = update.effective_user
    
    welcome_text = f"""
MAM MERU

LUCKY DRAW MYANMAR DEVELOPER AUNG THU HTWE

**upload ({user.first_name}):**

[checkd@egepadis.com](https://www.egepadis.com)
[checkd@engodai](https://www.engodai.com)
[My Profile](https://www.engodai.com)

---

### 8 Pages qookpq

| **4分钟-9:00分** | **Channel & Group** |
|---|---|
| Admin    | Referral    | FAQ    |
| About Us    |    |

---

**Main Menu / My Profile**  
/media adapter / Retention / HTTP socket / Channel & Group / Admin / Referral / FAQ / About Us  
"""
    
    # Welcome message with inline buttons
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start", callback_data="start")],
            [InlineKeyboardButton("📱 Contact", url="https://t.me/aungthuhtwe")],
            [InlineKeyboardButton("🌐 My Profile", url="https://www.engodai.com")]
        ]),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )
    
    # Deskboard buttons
    await update.message.reply_text(
        "👇 **Select from menu below:**",
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==============================
# REPLY BUTTON HANDLERS
# ==============================
async def handle_reply_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply keyboard buttons များကိုကိုင်တွယ်ခြင်း"""
    text = update.message.text
    
    if text == "🎰 ကံစမ်းမဲထုတ်မယ်":
        await update.message.reply_text("🎰 **ကံစမ်းမဲထုတ်ယူခြင်း**\n\nကံစမ်းမဲထုတ်ယူတော့မည်...")
    
    elif text == "📊 ရလဒ်ကြည့်မယ်":
        await update.message.reply_text("📊 **ရလဒ်များကြည့်ရှုခြင်း**\n\nသင့်ရလဒ်များကိုကြည့်ရှုတော့မည်...")
    
    elif text == "👤 ကျွန်တော့်ပရိုဖိုင်":
        await update.message.reply_text(
            "👤 **ကျွန်တော့်ပရိုဖိုင်**\n\n"
            "အမည်: Aung Thu Htwe\n"
            "အီးမေးလ်: checkd@engodai.com\n"
            "ကံစမ်းမဲအရေအတွက်: 15\n"
            "ဆုရရှိမှု: 3",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
                [InlineKeyboardButton("📊 View Stats", callback_data="view_stats")]
            ])
        )
    
    elif text == "🏆 ဆုကြေးများ":
        await update.message.reply_text("🏆 **ဆုကြေးများ**\n\n1st Prize: 10,000,000 Ks\n2nd Prize: 1,000,000 Ks\n3rd Prize: 100,000 Ks")
    
    elif text == "📺 ချန်နယ်နှင့်အုပ်စု":
        await update.message.reply_text(
            "📺 **Channel & Group**\n\n"
            "Join our channels and groups for updates:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Main Channel", url="https://t.me/luckydrawmyanmar")],
                [InlineKeyboardButton("💬 Discussion Group", url="https://t.me/luckydrawmyanmar_group")]
            ])
        )
    
    elif text == "👨‍💼 Admin":
        await update.message.reply_text("👨‍💼 **Admin**\n\nAdmin contact: @aungthuhtwe")
    
    elif text == "🤝 Referral":
        await update.message.reply_text(
            "🤝 **Referral System**\n\n"
            "Refer your friends and earn rewards!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Referral", callback_data="share_referral")],
                [InlineKeyboardButton("👥 My Referrals", callback_data="my_referrals")]
            ])
        )
    
    elif text == "❓ FAQ":
        await update.message.reply_text(
            "❓ **Frequently Asked Questions**\n\n"
            "Q: How to play?\nA: Click lottery draw button\n\n"
            "Q: How to claim prize?\nA: Contact admin",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 More FAQ", callback_data="more_faq")]
            ])
        )
    
    elif text == "ℹ️ About Us":
        await update.message.reply_text(
            "ℹ️ **About Us**\n\n"
            "LUCKY DRAW MYANMAR\n"
            "Developer: Aung Thu Htwe\n"
            "Contact: @aungthuhtwe\n"
            "Website: www.engodai.com"
        )

# ==============================
# INLINE BUTTON HANDLERS
# ==============================
async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline buttons များကိုကိုင်တွယ်ခြင်း"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "start":
        await query.edit_message_text("🚀 **Getting Started...**\n\nWelcome to Lucky Draw Myanmar!")
    
    elif data == "edit_profile":
        await query.edit_message_text("✏️ **Edit Profile**\n\nProfile editing feature coming soon...")
    
    elif data == "view_stats":
        await query.edit_message_text("📊 **View Stats**\n\nYour statistics: 15 draws, 3 wins")
    
    elif data == "share_referral":
        await query.edit_message_text("📤 **Share Referral**\n\nYour referral link: https://t.me/luckydrawmyanmar?start=ref123")
    
    elif data == "my_referrals":
        await query.edit_message_text("👥 **My Referrals**\n\nTotal referrals: 5\nEarned: 25,000 Ks")
    
    elif data == "more_faq":
        await query.edit_message_text("📖 **More FAQ**\n\nAdditional frequently asked questions...")

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
    
    print("🎰 LUCKY DRAW MYANMAR Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

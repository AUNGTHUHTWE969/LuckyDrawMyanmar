import os
import telebot
from telebot.types import ReplyKeyboardMarkup

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')
bot = telebot.TeleBot(BOT_TOKEN)

users = {}

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("👤 My Profile", "🎫 ကံစမ်းမဲ ဝယ်ယူရန်")
    keyboard.row("💰 ငွေသွင်း", "📤 ငွေထုတ်")
    keyboard.row("📊 မှတ်တမ်းကြည့်ရန်", "❓ FAQ")
    keyboard.row("🏠 ပင်မမီနူး")
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        f"👋 မင်္ဂလာပါ {message.from_user.first_name}!\n\n"
        "Telegram Lottery Bot မှ ကြိုဆိုပါတယ်! 🎉\n\n"
        "ကျေးဇူးပြု၍ အောက်ပါ menu မှ ရွေးချယ်မှုများကို အသုံးပြုပါ။",
        reply_markup=main_menu_keyboard()
    )

@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.from_user.id
    if user_id in users:
        bot.reply_to(message, "✅ သင်မှတ်ပုံတင်ပြီးသားဖြစ်ပါသည်!", reply_markup=main_menu_keyboard())
        return
    
    users[user_id] = {
        'name': message.from_user.first_name,
        'balance': 10000,
        'referral_code': f"REF{user_id}"
    }
    
    bot.reply_to(message,
        f"✅ မှတ်ပုံတင်ပြီးပါပြီ {message.from_user.first_name}!\n\n"
        f"💰 လက်ကျန်ငွေ: 10,000 Ks\n"
        f"🔗 Referral Code: REF{user_id}\n\n"
        "🎉 ယခု ကံစမ်းမဲများ ဝယ်ယူနိုင်ပါပြီ!",
        reply_markup=main_menu_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    
    if text == "👤 My Profile":
        user_id = message.from_user.id
        if user_id in users:
            user_data = users[user_id]
            bot.reply_to(message,
                f"👤 **My Profile**\n\n"
                f"**NAME**\n{user_data['name']}\n\n"
                f"**Balance**\n{user_data['balance']:,} Ks\n\n"
                f"**Referral Code**\n{user_data['referral_code']}",
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        else:
            bot.reply_to(message, "❌ ကျေးဇူးပြု၍ မှတ်ပုံတင်ပါ", reply_markup=main_menu_keyboard())
    
    elif text == "💰 ငွေသွင်း":
        bot.reply_to(message,
            "💰 **ငွေသွင်းရန်**\n\n"
            "KPay: 09789999368\n"
            "WavePay: 09789999368\n\n"
            "ငွေသွင်းပြီးပါက Screenshot ပို့ပါ။",
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    
    elif text == "🏠 ပင်မမီနူး":
        start(message)
    
    else:
        bot.reply_to(message, "ℹ️ ကျေးဇူးပြု၍ menu မှ ရွေးချယ်မှုများကို အသုံးပြုပါ။", reply_markup=main_menu_keyboard())

if __name__ == '__main__':
    print("🚀 Starting bot...")
    bot.infinity_polling()
    print("🤖 Bot is running!")

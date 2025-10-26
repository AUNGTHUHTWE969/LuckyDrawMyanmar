import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler
)
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# .env file မှ environment variables များကို load လုပ်ရန် (Local Development အတွက်)
load_dotenv() 

# --- 1. Configuration & Global State ---

# 🚨 Hardcoded အချက်အလက်များကို အသုံးပြုခြင်း 🚨
BOT_TOKEN = "8444084929:AAFnXo4U8U3gZAh2C2zeAks0hk3qGstLcNM"
ADMIN_ID = 8070878424
WEBHOOK_URL = "https://lucky-draw-myanmar.onrender.com" # <--- သတ်မှတ်ထားသော URL

raffle_state = {
    "is_active": False,
    "prize": None,
    "participants": set() 
}

# --- 2. Database Setup ---

# DATABASE_URL ကို Render Environment Variable မှ ဆက်လက်ယူသုံးပါမည်။
DB_URL = os.environ.get("DATABASE_URL")
if DB_URL:
    # Render DB URL ကို SQLAlchemy အတွက် မှန်ကန်သော ပုံစံသို့ ပြောင်းလဲခြင်း
    DATABASE_URL = DB_URL.replace("postgres://", "postgresql://", 1) 
    engine = create_engine(DATABASE_URL)
else:
    # DATABASE_URL မရှိပါက local sqlite ကို သုံးခြင်း
    engine = create_engine("sqlite:///raffle_data.db")

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True) 
    username = Column(String, nullable=True)
    full_name = Column(String)
    
Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. Helper Functions & UI Components ---

def is_admin(user_id: int) -> bool:
    """Admin စစ်ဆေးခြင်း"""
    return user_id == ADMIN_ID

def get_main_keyboard(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    """အမြဲသုံးရမည့် Command များကို Reply Keyboard (Dashboard) အဖြစ် ထုတ်ပေးခြင်း"""
    
    keyboard = [
        [KeyboardButton("/register"), KeyboardButton("/current_raffle")],
    ]
    
    if is_admin_user:
        # Admin အတွက် Dashboard Button ကို ထည့်သွင်းခြင်း
        keyboard.append([KeyboardButton("/admin_menu")])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_join_inline_keyboard() -> InlineKeyboardMarkup:
    """ကံစမ်းမဲ ဝင်ရန် Inline Keyboard ကို ထုတ်ပေးခြင်း"""
    buttons = [
        [InlineKeyboardButton("Join Raffle 🎉", callback_data='join_raffle')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- 4. Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start command: Dashboard Keyboard ကို ပြသခြင်း"""
    user_id = update.effective_user.id
    is_admin_user = is_admin(user_id)
    
    reply_markup = get_main_keyboard(is_admin_user)
    
    message = (
        "👋 **Lucky Draw Myanmar Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        "အောက်က ခလုတ်တွေကို နှိပ်ပြီး လုပ်ဆောင်ချက်တွေ စတင်နိုင်ပါတယ်။"
    )
    
    await update.message.reply_text(
        message, 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

async def current_raffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/current_raffle command: လက်ရှိ ကံစမ်းမဲ အခြေအနေ ပြသခြင်း"""
    if not raffle_state["is_active"]:
        await update.message.reply_text("❌ လက်ရှိ လည်ပတ်နေသော ကံစမ်းမဲ မရှိပါ။")
        return
    
    message = (
        f"⏳ **လက်ရှိ ကံစမ်းမဲ အခြေအနေ** ⏳\n\n"
        f"🎁 **ဆု:** {raffle_state['prize']}\n"
        f"👥 **ပါဝင်သူ စုစုပေါင်း:** {len(raffle_state['participants'])} ဦး"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/register command: User ကို Database တွင် မှတ်ပုံတင်ခြင်း"""
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    full_name = update.effective_user.full_name
    
    with get_db() as db:
        try:
            new_user = User(id=user_id, username=username, full_name=full_name)
            db.add(new_user)
            db.commit()
            await update.message.reply_text(f"🎉 **{full_name}** မှတ်ပုံတင်ခြင်း အောင်မြင်ပါသည်။")
        except IntegrityError:
            db.rollback() 
            await update.message.reply_text("✅ သင်သည် မှတ်ပုံတင်ပြီးသား ဖြစ်ပါသည်။")

# --- 5. Admin Command Handlers ---

async def admin_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_menu command: Admin Dashboard ကို Inline Keyboard ဖြင့် ပြသခြင်း"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 သင့်တွင် Admin အသုံးပြုခွင့်မရှိပါ။")
        return
    
    message = "👑 **Admin လုပ်ဆောင်ချက်များ:**"
    
    # 💡 Admin အတွက် Inline Keyboard ကို သုံးခြင်း
    buttons = [
        [InlineKeyboardButton("🎁 ကံစမ်းမဲ အသစ် စတင်ရန်", callback_data='admin_create_raffle_prompt')],
        [InlineKeyboardButton("🗳️ ကံထူးရှင် ရွေးရန်", callback_data='admin_pick_winner')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def create_raffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/create_raffle command ကိုင်တွယ်ခြင်း"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 သင့်တွင် Admin အသုံးပြုခွင့်မရှိပါ။")
        return
    
    if raffle_state["is_active"]:
        await update.message.reply_text("⚠️ ကံစမ်းမဲတစ်ခု လည်ပတ်နေဆဲဖြစ်ပါသည်။")
        return

    try:
        prize = " ".join(context.args)
        if not prize:
             await update.message.reply_text("❌ ကျေးဇူးပြု၍ ဆုကို ထည့်ပါ။ ဥပမာ: `/create_raffle iPhone 16 Pro`")
             return
    except IndexError:
        return

    raffle_state["is_active"] = True
    raffle_state["prize"] = prize
    raffle_state["participants"].clear()

    # 💡 UI: Join Button ပါသော ကြေညာစာသားကို Inline Keyboard ဖြင့် ပို့ပေးခြင်း
    message = (
        f"🎉 **ကံစမ်းမဲ စတင်ပါပြီ!** 🎉\n\n"
        f"🎁 **ဆု:** {prize}\n"
        f"👥 **လက်ရှိ ပါဝင်သူ:** {len(raffle_state['participants'])} ဦး\n\n"
        "ပါဝင်ဖို့အတွက် အောက်ပါခလုတ်ကို နှိပ်ပါ။"
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=message, 
        reply_markup=get_join_inline_keyboard(), 
        parse_mode="Markdown"
    )

# --- 6. Callback Query Handlers (Inline Button Actions) ---

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin Menu ကနေ Action တွေကို စီမံခန့်ခွဲခြင်း"""
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    data = query.data
    
    if data == 'admin_create_raffle_prompt':
        await query.edit_message_text(
            "📝 **ဆုကို ရိုက်ထည့်ပါ:**\n\n"
            "ကျေးဇူးပြု၍ **`/create_raffle [ဆုအမည်]`** ပုံစံဖြင့် ရိုက်ထည့်ပေးပါ။"
        )
    elif data == 'admin_pick_winner':
        await query.edit_message_text("စနစ်မှ ကံထူးရှင် ရွေးချယ်နေပါသည်။...")
        await pick_winner_handler(update, context, is_callback=True)

async def handle_join_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Join Raffle Button ကို နှိပ်တဲ့အခါ ကိုင်တွယ်ခြင်း"""
    query = update.callback_query
    await query.answer()

    if not raffle_state["is_active"]:
        await query.edit_message_text("❌ လက်ရှိ လည်ပတ်နေသော ကံစမ်းမဲ မရှိတော့ပါ။")
        return
    
    user_id = query.from_user.id
    
    with get_db() as db:
        if not db.query(User).filter(User.id == user_id).first():
            await query.answer("🛑 ကံစမ်းမဲမပါဝင်မီ /register ဖြင့် မှတ်ပုံတင်ရန် လိုအပ်ပါသည်။", show_alert=True)
            return

    if user_id in raffle_state["participants"]:
        await query.answer("✅ သင် ပါဝင်ပြီးသား ဖြစ်ပါသည်။", show_alert=True)
    else:
        raffle_state["participants"].add(user_id)
        
        # 💡 Message ကို update လုပ်ပြီး ပါဝင်သူအရေအတွက်ကို ပြောင်းလဲပြခြင်း
        new_text = (
            f"🎉 **ကံစမ်းမဲ စတင်ပါပြီ!** 🎉\n\n"
            f"🎁 **ဆု:** {raffle_state['prize']}\n"
            f"👥 **လက်ရှိ ပါဝင်သူ:** {len(raffle_state['participants'])} ဦး\n\n"
            "ပါဝင်ဖို့အတွက် အောက်ပါခလုတ်ကို နှိပ်ပါ။"
        )
        
        await query.edit_message_text(
            new_text, 
            reply_markup=get_join_inline_keyboard(), 
            parse_mode="Markdown"
        )
        await query.answer("✨ ပါဝင်ခြင်း အောင်မြင်ပါသည်။ ကံကောင်းပါစေ!", show_alert=True)


async def pick_winner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False) -> None:
    """ကံထူးရှင် ရွေးချယ်ခြင်း"""
    
    user_id = update.effective_user.id if not is_callback else update.callback_query.from_user.id

    if not is_admin(user_id):
        # Admin မဟုတ်ရင် ပြန်ထွက်
        return

    if not raffle_state["is_active"]:
        message = "❌ ကံစမ်းမဲ မစတင်ရသေးပါ။"
    
        if is_callback:
             await update.callback_query.edit_message_text(message)
        else:
             await update.message.reply_text(message)
        return

    participants = list(raffle_state["participants"])

    if len(participants) == 0:
        message = "😢 ပါဝင်သူ မရှိ၍ ကံထူးရှင် ရွေးချယ်နိုင်ခြင်း မရှိပါ။"
    else:
        winner_id = random.choice(participants)
        
        with get_db() as db:
            winner_user = db.query(User).filter(User.id == winner_id).first()
            # Winner ကို Mention လုပ်နိုင်ရန်
            winner_mention = f"[{winner_user.full_name}](tg://user?id={winner_id})" if winner_user else f"User ID: {winner_id}"
        
        message = (
            f"👑 **ကံထူးရှင် ရွေးချယ်ခြင်း ပြီးဆုံးပါပြီ!** 👑\n\n"
            f"🎉 **ကံထူးရှင်:** {winner_mention}\n"
            f"🎁 **ဆု:** {raffle_state['prize']}"
        )

    # ကံစမ်းမဲကို ပြန်ပိတ်ပြီး state ရှင်းခြင်း
    raffle_state["is_active"] = False
    raffle_state["prize"] = None
    raffle_state["participants"].clear()

    if is_callback:
        await update.callback_query.edit_message_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, parse_mode="Markdown")


# --- 7. Application Setup & Webhook ---

# Hardcoded BOT_TOKEN ကို သုံးခြင်း
application = Application.builder().token(BOT_TOKEN).build()

# Command Handlers (Dashboard Command များ)
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("register", register_command))
application.add_handler(CommandHandler("current_raffle", current_raffle_command))
application.add_handler(CommandHandler("admin_menu", admin_menu_command))
application.add_handler(CommandHandler("create_raffle", create_raffle_command))
application.add_handler(CommandHandler("pick_winner", pick_winner_handler))


# Callback Query Handlers (Inline Button Actions)
application.add_handler(CallbackQueryHandler(handle_join_raffle, pattern='^join_raffle$'))
application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern='^admin_create_raffle_prompt$|^admin_pick_winner$'))


# Flask Web Server & Webhook 
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!", 200

# BOT_TOKEN ကို Hardcode လုပ်ထားခြင်းကြောင့် URL လည်း မှန်ကန်စွာ ရရှိမည်
@flask_app.route(f'/{BOT_TOKEN}', methods=['POST']) 
async def webhook_handler(): 
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        # Flask[async] ကို ထည့်သွင်းပြီးပြီဖြစ်၍ async ကို သုံးနိုင်သည်။
        asyncio.create_task(application.process_update(update)) 
    return jsonify({'status': 'ok'})

# Webhook URL ကို API တွင် မှန်ကန်စွာ set လုပ်ခြင်း
async def set_webhook_on_start():
    if BOT_TOKEN and WEBHOOK_URL:
        # URL နဲ့ Token ကို မှန်ကန်စွာ ပေါင်းစပ်ပေးခြင်း
        await application.bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/{BOT_TOKEN}") 

if BOT_TOKEN and WEBHOOK_URL:
    try:
        asyncio.run(set_webhook_on_start())
    except Exception as e:
        # Webhook set လုပ်ရာတွင် ပြဿနာတက်သော်လည်း Deploy သည် ဆက်လက်သွားမည်။
        print(f"Error setting webhook: {e}") 

if __name__ == '__main__':
    # Render မှာ gunicorn ကို Start Command မှာ သုံးထားသည်။
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

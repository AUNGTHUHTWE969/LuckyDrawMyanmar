import os
import random
import asyncio
import logging
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

# .env file မှ environment variables များကို load လုပ်ရန်
load_dotenv() 

# --- Configuration & Global State ---
# 🚨 Bot Token နှင့် Admin ID ကို Environment Variables မှ ရယူပါ
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8444084929:AAFnXo4U8U3gZAh2C2zeAks0hk3qGstLcNM")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8070878424")) # Admin ID ကို ဂဏန်းဖြင့်သာ သတ်မှတ်ရန်
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://lucky-draw-myanmar.onrender.com") 

raffle_state = {
    "is_active": False,
    "prize": None,
    "participants": set() 
}

# --- Database Setup ---
DB_URL = os.environ.get("DATABASE_URL")

if DB_URL:
    # Render PostgreSQL URL ကို SQLAlchemy အတွက် ပုံစံပြောင်းပါ
    DATABASE_URL = DB_URL.replace("postgres://", "postgresql://", 1) 
    
    # 🚨 FINAL FIX: SSL MODE ကို ထည့်သွင်းခြင်း (Render Postgres အတွက် မဖြစ်မနေ လိုအပ်သည်)
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "sslmode": "require"  # SSL ကို မဖြစ်မနေ သုံးရန် သတ်မှတ်ခြင်း
        }
    )
else:
    engine = create_engine("sqlite:///raffle_data.db") # Local Test အတွက်သာ
    
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

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_admin_user = user_id == ADMIN_ID
    reply_markup = get_main_keyboard(is_admin_user)
    
    message = (
        "👋 **Lucky Draw Myanmar Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        "အောက်က ခလုတ်တွေကို နှိပ်ပြီး လုပ်ဆောင်ချက်တွေ စတင်နိုင်ပါတယ်။"
    )
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    full_name = update.effective_user.full_name
    
    # 🚨 DB Error များကို ဖမ်းယူရန် Outer Try/Except ကို အသုံးပြုခြင်း
    try:
        with get_db() as db:
            try:
                new_user = User(id=user_id, username=username, full_name=full_name)
                db.add(new_user)
                db.commit()
                await update.message.reply_text(f"🎉 **{full_name}** မှတ်ပုံတင်ခြင်း အောင်မြင်ပါသည်။")
            except IntegrityError:
                db.rollback() 
                await update.message.reply_text("✅ သင်သည် မှတ်ပုံတင်ပြီးသား ဖြစ်ပါသည်။")
            # 🚨 Note: အခြားသော DB Error များဖြစ်ပေါ်ပါက အောက်က Except တွင် ဖမ်းမိပါမည်
    except Exception as e:
        print(f"CRITICAL DB ERROR in register_command: {e}") 
        # User ကို Reply ပို့ပြီး Log တွင် Error အပြည့်အစုံကို ထုတ်ပြပါ
        try:
            await update.message.reply_text(f"❌ မှတ်ပုံတင်ခြင်း မအောင်မြင်ပါ။ စနစ်ချို့ယွင်းမှု (DB Error) ဖြစ်ပေါ်နေပါသည်။ Admin: {str(e)[:50]}...")
        except Exception:
            # Reply မရရင်တောင် Log ထဲမှာ Error မြင်ရပါပြီ
            pass
            
# --- (Other Handlers: current_raffle_command, admin_menu_command, create_raffle_command, handle_admin_actions, handle_join_raffle, pick_winner_handler) ---
# ... (ဤနေရာတွင် အခြား Handlers များအားလုံးကို ယခင် Code အတိုင်း ထားရှိပါ) ...
# (Placeholders for other handlers to complete the file)
async def current_raffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Add your logic here
    await update.message.reply_text("လက်ရှိ မဲပေါက်ပစ္စည်း မရှိသေးပါ။")

async def admin_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Add your logic here
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Admin Menu ဖွင့်ပါပြီ။")
    else:
        await update.message.reply_text("သင်သည် Admin မဟုတ်ပါ။")
        
async def create_raffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Add your logic here
    pass
async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Add your logic here
    pass
async def handle_join_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Add your logic here
    pass
async def pick_winner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False) -> None:
    # Add your logic here
    pass
# ... (End of other handlers) ...

# --- Helper Functions & UI Components ---
def get_main_keyboard(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    # ... (Keyboard logic)
    keyboard = [
        [KeyboardButton("/register"), KeyboardButton("/current_raffle")],
    ]
    if is_admin_user:
        keyboard.append([KeyboardButton("/admin_menu")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_join_inline_keyboard() -> InlineKeyboardMarkup:
    # ... (Inline Keyboard logic)
    buttons = [[InlineKeyboardButton("Join Raffle 🎉", callback_data='join_raffle')]]
    return InlineKeyboardMarkup(buttons)


# --- Application Setup & Webhook (Gunicorn Stable Fix) ---

application = None # Global Application object
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!", 200

@flask_app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook_handler():
    """Final Webhook handler with proper loop management for Gunicorn."""
    global application 
    
    # 🚨 FIX: Event Loop ကို ကိုယ်တိုင် ထိန်းချုပ်ခြင်း (RuntimeError: Event loop is closed ကို ဖြေရှင်း) 🚨
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if request.method == "POST":
        try:
            json_data = request.get_json(force=True)
            
            # Initialization Check & Setup:
            if application is None:
                application = Application.builder().token(BOT_TOKEN).build()
                
                # Handlers တွေကို ထပ်ထည့်ပါ (Handlers အားလုံး ဒီမှာ ပါရမည်)
                application.add_handler(CommandHandler("start", start))
                application.add_handler(CommandHandler("register", register_command))
                application.add_handler(CommandHandler("current_raffle", current_raffle_command))
                application.add_handler(CommandHandler("admin_menu", admin_menu_command))
                application.add_handler(CommandHandler("create_raffle", create_raffle_command))
                application.add_handler(CommandHandler("pick_winner", pick_winner_handler))
                application.add_handler(CallbackQueryHandler(handle_join_raffle, pattern='^join_raffle$'))
                application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern='^admin_create_raffle_prompt$|^admin_pick_winner$'))
                
                # Initialization ကို Loop တွင် ပြီးအောင် လုပ်ခြင်း
                async def worker_initialize():
                    await application.initialize()
                    # Webhook URL ကို set လုပ်ပါ
                    await application.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}") 
                    print(f"INFO: Worker Application Initialized! Webhook set to {WEBHOOK_URL}/{BOT_TOKEN}")
                
                try:
                    loop.run_until_complete(worker_initialize())
                except Exception as init_e:
                    # Invalid Webhook URL error ကို ဒီမှာ ဖမ်းမိပါမည်
                    print(f"CRITICAL ERROR during Worker Initialization: {init_e}")
                    pass 

            # Update ကို Process လုပ်ရန်
            async def process_update_async():
                update = Update.de_json(json_data, application.bot)
                await application.process_update(update)

            # Update Process ကို Loop တွင် ပြီးအောင် လုပ်ခြင်း
            loop.run_until_complete(process_update_async())
            
        except Exception as e:
            # Update processing error 
            print(f"CRITICAL ERROR in Flask Handler: {e}")
            return jsonify({'status': 'CRITICAL ERROR', 'message': str(e)}), 200 
            
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, debug=False)

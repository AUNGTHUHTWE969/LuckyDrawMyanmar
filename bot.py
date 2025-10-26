import os
import random
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# .env file မှ environment variables များကို load လုပ်ရန် (Local Development အတွက်)
# Render တွင် run လျှင် ၎င်းကို ကျော်သွားမည်။
load_dotenv() 

# --- 1. Configuration & Global State ---

# Environment Variables မှ Bot Token နှင့် Admin ID များကို ယူခြင်း
BOT_TOKEN = os.environ.get("8444084929:AAFnXo4U8U3gZAh2C2zeAks0hk3qGstLcNM")
WEBHOOK_URL = os.environ.get("https://lucky-draw-myanmar.onrender.com")
# Admin ID ကို String အနေနဲ့ ယူပြီး Integer အဖြစ် ပြောင်းပါမည်။ မရှိရင် 0 ကို သုံးပါမည်။
try:
    ADMIN_ID = int(os.environ.get("8070878424", 0))
except ValueError:
    ADMIN_ID = 0

# Raffle State (DB ထဲမှာ မသိမ်းဘဲ ယာယီသိမ်းထားသော ပါဝင်သူစာရင်း)
raffle_state = {
    "is_active": False,
    "prize": None,
    "participants": set() # Telegram User IDs
}

# --- 2. Database Setup (Render Postgres အတွက်) ---

# Render Database URL ကို ယူပြီး SQLAlchemy format သို့ ပြောင်းခြင်း
DB_URL = os.environ.get("DATABASE_URL")
if DB_URL:
    DATABASE_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # DB URL မရှိရင် SQLite ယာယီ database သုံးပါမည်။ (Local Test အတွက်)
    engine = create_engine("sqlite:///raffle_data.db")
    print("WARNING: Using SQLite database. Connect Render Postgres for production.")


Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database Model: User Table
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True) 
    username = Column(String, nullable=True)
    full_name = Column(String)
    
# Database Table များ မရှိသေးရင် ဖန်တီးခြင်း
Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    """Database Session Helper"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. Helper Function (Admin Check) ---

def is_admin(user_id: int) -> bool:
    """လက်ရှိ user သည် admin ဟုတ်/မဟုတ် စစ်ဆေးခြင်း"""
    return user_id == ADMIN_ID

# --- 4. Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 ကံစမ်းမဲ Bot မှ ကြိုဆိုပါသည်။ ကံစမ်းမဲများ ပါဝင်ဖို့ /register နှင့် /join_raffle ကို နှိပ်ပါ။")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User ကို Database တွင် မှတ်ပုံတင်ခြင်း"""
    
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

async def create_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(ADMIN ONLY) ကံစမ်းမဲ အသစ်တစ်ခု စတင်ခြင်း။"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 သင့်တွင် Admin အသုံးပြုခွင့်မရှိပါ။")
        return
    
    if raffle_state["is_active"]:
        await update.message.reply_text("⚠️ ကံစမ်းမဲတစ်ခု လည်ပတ်နေဆဲဖြစ်ပါသည်။")
        return

    try:
        prize = " ".join(context.args)
        if not prize:
             raise IndexError
    except IndexError:
        await update.message.reply_text("❌ ဆုကို ထည့်ပါ။ ဥပမာ: /create_raffle ဆိုင်ကယ်")
        return

    raffle_state["is_active"] = True
    raffle_state["prize"] = prize
    raffle_state["participants"].clear()

    message = (
        f"🎉 **ကံစမ်းမဲ စတင်ပါပြီ!** 🎉\n\n"
        f"🎁 **ဆု:** {prize}\n"
        f"ပါဝင်လိုပါက /join_raffle ကို နှိပ်ပါ။ (မှတ်ချက်: Bot Restart လုပ်ပါက ပါဝင်သူစာရင်း ပျက်နိုင်ပါသည်။)"
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def join_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ကံစမ်းမဲသို့ ပါဝင်ခြင်း။"""
    if not raffle_state["is_active"]:
        await update.message.reply_text("❌ လက်ရှိ လည်ပတ်နေသော ကံစမ်းမဲ မရှိပါ။")
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.full_name

    # DB မှာ Register လုပ်ပြီးသားလား အရင်စစ်ဆေးပါ
    with get_db() as db:
        if not db.query(User).filter(User.id == user_id).first():
            await update.message.reply_text("🛑 ကံစမ်းမဲမပါဝင်မီ /register ဖြင့် မှတ်ပုံတင်ရန် လိုအပ်ပါသည်။")
            return

    if user_id in raffle_state["participants"]:
        await update.message.reply_text("✅ သင် ပါဝင်ပြီးသား ဖြစ်ပါသည်။")
    else:
        raffle_state["participants"].add(user_id)
        await update.message.reply_text(f"✨ **{username}** ပါဝင်လိုက်ပါပြီ! စုစုပေါင်း: {len(raffle_state['participants'])} ဦး")


async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(ADMIN ONLY) ကံထူးရှင် ရွေးချယ်ခြင်း။"""
    
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 သင့်တွင် Admin အသုံးပြုခွင့်မရှိပါ။")
        return

    if not raffle_state["is_active"]:
        await update.message.reply_text("❌ ကံစမ်းမဲ မစတင်ရသေးပါ။")
        return

    participants = list(raffle_state["participants"])

    if len(participants) == 0:
        await update.message.reply_text("😢 ပါဝင်သူ မရှိပါ။")
    else:
        winner_id = random.choice(participants)
        
        # Database မှ ကံထူးရှင် အချက်အလက် ရယူခြင်း
        with get_db() as db:
            winner_user = db.query(User).filter(User.id == winner_id).first()
            winner_name = winner_user.full_name if winner_user else f"User ID: {winner_id}"
        
        message = (
            f"👑 **ကံထူးရှင် ရွေးချယ်ခြင်း ပြီးဆုံးပါပြီ!** 👑\n\n"
            f"🎉 **ကံထူးရှင်:** {winner_name}\n"
            f"🎁 **ဆု:** {raffle_state['prize']}"
        )
        await update.message.reply_text(message, parse_mode="Markdown")

    # ကံစမ်းမဲ အခြေအနေကို ပြန်လည် စတင်ပါ။
    raffle_state["is_active"] = False
    raffle_state["prize"] = None
    raffle_state["participants"].clear()

# --- 5. Application Setup & Webhook ---

# Telegram Application ကို စတင်ခြင်း
application = Application.builder().token(BOT_TOKEN).build()

# Command Handler များကို ထည့်သွင်းခြင်း
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("register", register))
application.add_handler(CommandHandler("create_raffle", create_raffle))
application.add_handler(CommandHandler("join_raffle", join_raffle))
application.add_handler(CommandHandler("pick_winner", pick_winner))

# Flask Web Server
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    """Uptime Robot အတွက် Health Check Endpoint"""
    return "Bot is running!", 200

@flask_app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook_handler():
    """Telegram Webhook Endpoint"""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        # Application Update ကို သီးခြား thread ဖြင့် run ရန်
        asyncio.create_task(application.process_update(update))
    return jsonify({'status': 'ok'})

# Webhook ကို Telegram မှာ တစ်ခါတည်း သတ်မှတ်ဖို့
async def set_webhook_on_start():
    if BOT_TOKEN and WEBHOOK_URL:
        # Webhook URL: https://your-app-name.onrender.com/BOT_TOKEN
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}{BOT_TOKEN}")
        print(f"Webhook set to: {WEBHOOK_URL}{BOT_TOKEN}")

if BOT_TOKEN and WEBHOOK_URL:
    try:
        asyncio.run(set_webhook_on_start())
    except Exception as e:
        print(f"Error setting webhook: {e}")

# Gunicorn/Render မှ စတင်သောအခါ Flask App ကို run ရန်။
if __name__ == '__main__':
    # Local Development အတွက်သာ
    print("Running Flask app locally...")
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

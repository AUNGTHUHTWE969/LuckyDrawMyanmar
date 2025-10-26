import os
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError # DB Error ကို စစ်ရန်

# --- 1. Configuration & Global State ---

# Bot Token နှင့် Admin ID ကို Environment Variables မှ ယူခြင်း
BOT_TOKEN = os.environ.get("8444084929:AAFnXo4U8U3gZAh2C2zeAks0hk3qGstLcNM")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
# Admin ID ကို String အနေနဲ့ ယူပြီး Integer အဖြစ် ပြောင်းပါမည်
ADMIN_ID = int(os.environ.get("8070878424", 0)) 

# Raffle State (Temporary - DB ဖြင့် အစားထိုးနိုင်သည်)
raffle_state = {
    "is_active": False,
    "prize": None,
    "participants": set()
}

# --- 2. Database Setup (Populated with prior code) ---

DATABASE_URL = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://", 1)

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True) 
    username = Column(String, index=True)
    full_name = Column(String)
    
Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. Helper Function (Admin Check) ---

def is_admin(user_id: int) -> bool:
    """လက်ရှိ user သည် admin ဟုတ်/မဟုတ် စစ်ဆေးခြင်း"""
    return user_id == ADMIN_ID

# --- 4. Command Handlers (Modified) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start command ကို ဖြေကြားခြင်း။"""
    await update.message.reply_text("👋 ကံစမ်းမဲ Bot မှ ကြိုဆိုပါသည်။ ပါဝင်ရန် /register နှင့် /join_raffle ကို နှိပ်ပါ။")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/register command ဖြင့် User ကို Database တွင် မှတ်ပုံတင်ခြင်း"""
    
    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    full_name = update.effective_user.full_name
    
    with get_db() as db:
        try:
            new_user = User(id=user_id, username=username, full_name=full_name)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            await update.message.reply_text(f"🎉 **{full_name}** မှတ်ပုံတင်ခြင်း အောင်မြင်ပါသည်။")
        except IntegrityError:
            # Primary Key Error (User ID) ကြောင့် Register ထပ်လုပ်လို့မရရင်
            db.rollback() 
            await update.message.reply_text("✅ သင်သည် မှတ်ပုံတင်ပြီးသား ဖြစ်ပါသည်။")

async def create_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(ADMIN ONLY) ကံစမ်းမဲ အသစ်တစ်ခု စတင်ခြင်း။"""
    
    # --- ADMIN CHECK ---
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 သင့်တွင် အသုံးပြုခွင့်မရှိပါ။")
        return
    # -------------------
    
    if raffle_state["is_active"]:
        await update.message.reply_text("⚠️ ကံစမ်းမဲတစ်ခု လည်ပတ်နေဆဲဖြစ်ပါသည်။ /pick_winner ဖြင့် အရင်ပိတ်ပါ။")
        return

    try:
        prize = " ".join(context.args) # Command နောက်က စာအားလုံးကို ဆုအဖြစ်ယူမည်
        if not prize:
             raise IndexError
    except IndexError:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ ဆုကို ထည့်သွင်းပါ။ ဥပမာ: /create_raffle ဆိုင်ကယ်")
        return

    raffle_state["is_active"] = True
    raffle_state["prize"] = prize
    raffle_state["participants"].clear()

    message = (
        f"🎉 **ကံစမ်းမဲ စတင်ပါပြီ!** 🎉\n\n"
        f"🎁 **ဆု:** {prize}\n"
        f"ပါဝင်လိုပါက /join_raffle ကို နှိပ်ပါ။"
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def join_raffle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ကံစမ်းမဲသို့ ပါဝင်ခြင်း။"""
    if not raffle_state["is_active"]:
        await update.message.reply_text("❌ လက်ရှိ လည်ပတ်နေသော ကံစမ်းမဲ မရှိပါ။")
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.full_name

    # DB မှာ Register လုပ်ပြီးသားလား အရင်စစ်ဆေးသင့်ပါသည်။
    with get_db() as db:
        if not db.query(User).filter(User.id == user_id).first():
            await update.message.reply_text("🛑 ကံစမ်းမဲမပါဝင်မီ /register ဖြင့် မှတ်ပုံတင်ရန် လိုအပ်ပါသည်။")
            return

    if user_id in raffle_state["participants"]:
        await update.message.reply_text("✅ သင် ပါဝင်ပြီးသား ဖြစ်ပါသည်။")
    else:
        raffle_state["participants"].add(user_id)
        await update.message.reply_text(f"✨ **{username}** ကံစမ်းမဲတွင် ပါဝင်လိုက်ပါပြီ! စုစုပေါင်း: {len(raffle_state['participants'])} ဦး")


async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(ADMIN ONLY) ကံထူးရှင် ရွေးချယ်ခြင်း။"""
    
    # --- ADMIN CHECK ---
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 သင့်တွင် အသုံးပြုခွင့်မရှိပါ။")
        return
    # -------------------

    if not raffle_state["is_active"]:
        await update.message.reply_text("❌ ကံစမ်းမဲ မစတင်ရသေးပါ။")
        return

    participants = list(raffle_state["participants"])

    if len(participants) == 0:
        await update.message.reply_text("😢 ပါဝင်သူ မရှိ၍ ကံထူးရှင် ရွေးချယ်နိုင်ခြင်း မရှိပါ။")
    else:
        winner_id = random.choice(participants)
        
        # Database မှ ကံထူးရှင် အချက်အလက် ရယူခြင်း
        with get_db() as db:
            winner_user = db.query(User).filter(User.id == winner_id).first()
            winner_name = winner_user.full_name if winner_user else "တစ်စုံတစ်ယောက် (အမည် မသိ)"
        
        message = (
            f"👑 **ကံထူးရှင် ရွေးချယ်ခြင်း ပြီးဆုံးပါပြီ!** 👑\n\n"
            f"🎉 **ကံထူးရှင်:** {winner_name} (ID: {winner_id})\n"
            f"🎁 **ဆု:** {raffle_state['prize']}"
        )
        await update.message.reply_text(message, parse_mode="Markdown")

    # ကံစမ်းမဲ အခြေအနေကို ပြန်လည် စတင်ပါ။
    raffle_state["is_active"] = False
    raffle_state["prize"] = None
    raffle_state["participants"].clear()


# --- 5. Application Setup & Webhook (unchanged) ---

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
        await application.process_update(update)
    return jsonify({'status': 'ok'})

import asyncio
async def set_webhook():
    """Bot စတင်စဉ်တွင် Webhook ကို Telegram တွင် သတ်မှတ်ခြင်း။"""
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}{BOT_TOKEN}")

if BOT_TOKEN and WEBHOOK_URL:
    asyncio.run(set_webhook())


# Gunicorn/Render မှ စတင်သောအခါ Flask App ကို run ရန်။
if __name__ == '__main__':
    # ဒါက Local မှာ စမ်းသပ်ဖို့သာ ဖြစ်ပါတယ်။
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

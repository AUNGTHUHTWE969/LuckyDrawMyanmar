import os
import logging
import sqlite3
import random
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration - Render.com environment variables ကနေဖတ်မယ်
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Database ကိုစတင်မယ်"""
    conn = sqlite3.connect('lucky_draw.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone_number TEXT UNIQUE,
            username TEXT,
            first_name TEXT,
            is_verified INTEGER DEFAULT 0,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            join_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# App start မှာ database initialize လုပ်မယ်
init_db()

def send_telegram_message(chat_id, text):
    """Telegram ကို message ပို့မယ်"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Message sent to {chat_id}")
            return True
        else:
            logger.error(f"Telegram API error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook handler - Telegram ကနေ message ရောက်ရင် ဒီ function ကိုခေါ်မယ်"""
    try:
        data = request.get_json()
        
        if 'message' not in data:
            return jsonify({'status': 'ok'})
        
        message = data['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '').strip()
        first_name = message['from'].get('first_name', 'User')
        
        logger.info(f"Message from {user_id}: {text}")
        
        # Command handlers
        if text == '/start':
            response_text = f"""
🎉 <b>LUCKY DRAW MYANMAR BOT</b>

Welcome <b>{first_name}</b>!

🤖 <b>Bot Status:</b> 🟢 ACTIVE
🌐 <b>Server:</b> Render.com

<b>Commands:</b>
/register - အကောင့်အသစ်ဖွင့်မယ်
/join - Lucky Draw ဝင်မယ်  
/profile - ကိုယ့်အကောင့်ကြည့်မယ်
/stats - စာရင်းဇယားကြည့်မယ်

<b>မှတ်ချက်:</b> ဖုန်းနံပါတ်နဲ့ မှတ်ပုံတင်ရပါမယ်
"""
            send_telegram_message(chat_id, response_text)
        
        elif text == '/register':
            # Phone registration စမယ်
            send_telegram_message(chat_id, """
📱 <b>REGISTRATION</b>

ကျေးဇူးပြုပြီး သင့်ဖုန်းနံပါတ်ထည့်ပါ:

<b>Format:</b> 
09XXXXXXXX or +959XXXXXXXX

ဥပမာ: 
<code>09123456789</code>
<code>+959123456789</code>
""")
        
        elif text == '/join':
            handle_join(chat_id, user_id, first_name)
        
        elif text == '/profile':
            handle_profile(chat_id, user_id, first_name)
        
        elif text == '/stats':
            handle_stats(chat_id)
        
        elif text == '/test':
            send_telegram_message(chat_id, "✅ <b>Bot is working perfectly!</b>")
        
        else:
            # Phone number ဖြစ်မဖြစ်စစ်မယ်
            if is_phone_number(text):
                handle_phone_registration(chat_id, user_id, text, first_name)
            else:
                send_telegram_message(chat_id, "❌ <b>Unknown command</b>\n\nUse /start to see available commands")
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error'})

def is_phone_number(text):
    """Phone number ဟုတ်မဟုတ်စစ်မယ်"""
    import re
    clean_text = re.sub(r'[\s\-\(\)]', '', text)
    patterns = [r'^09\d{9}$', r'^\+959\d{9}$']
    return any(re.match(pattern, clean_text) for pattern in patterns)

def handle_phone_registration(chat_id, user_id, phone, first_name):
    """Phone number ကို database ထဲသိမ်းမယ်"""
    conn = sqlite3.connect('lucky_draw.db')
    cursor = conn.cursor()
    
    try:
        clean_phone = phone.replace(' ', '').replace('-', '')
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, phone_number, first_name, is_verified) VALUES (?, ?, ?, 1)",
            (user_id, clean_phone, first_name)
        )
        conn.commit()
        
        send_telegram_message(chat_id, f"""
✅ <b>REGISTRATION SUCCESSFUL!</b>

<b>Phone Number:</b> {clean_phone}
<b>Name:</b> {first_name}
<b>Status:</b> Verified

ကျေးဇူးတင်ပါတယ်! ယခုအခါ 
/join - Lucky Draw ဝင်နိုင်ပါပြီ
""")
    except Exception as e:
        logger.error(f"Registration error: {e}")
        send_telegram_message(chat_id, "❌ <b>Registration failed. Please try again.</b>")
    finally:
        conn.close()

def handle_join(chat_id, user_id, first_name):
    """Lucky Draw ဝင်မယ်"""
    conn = sqlite3.connect('lucky_draw.db')
    cursor = conn.cursor()
    
    # User မှတ်ပုံတင်ထားရဲ့လားစစ်မယ်
    cursor.execute("SELECT is_verified FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user or not user[0]:
        send_telegram_message(chat_id, "❌ <b>Please register first!</b>\n\nUse /register to register with your phone number")
        conn.close()
        return
    
    # ယခင်က join ပြီးသားလားစစ်မယ်
    cursor.execute("SELECT 1 FROM participants WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        send_telegram_message(chat_id, "❌ <b>You have already joined the draw!</b>")
    else:
        cursor.execute("INSERT INTO participants (user_id) VALUES (?)", (user_id,))
        conn.commit()
        
        # စုစုပေါင်းဝင်ရောက်သူအရေအတွက်ရမယ်
        cursor.execute("SELECT COUNT(*) FROM participants")
        count = cursor.fetchone()[0]
        
        send_telegram_message(chat_id, f"""
✅ <b>JOINED SUCCESSFULLY!</b>

🎊 <b>Thank you {first_name}!</b>
📊 <b>Total Participants:</b> {count}

🍀 <b>Good Luck!</b>
""")
    conn.close()

def handle_profile(chat_id, user_id, first_name):
    """User profile ကြည့်မယ်"""
    conn = sqlite3.connect('lucky_draw.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.phone_number, u.username, u.created_date,
               (SELECT COUNT(*) FROM participants p WHERE p.user_id = u.user_id) as draw_count
        FROM users u WHERE u.user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:  # Phone number ရှိရင်
        phone, username, join_date, draw_count = result
        profile_text = f"""
👤 <b>USER PROFILE</b>

<b>Name:</b> {first_name}
<b>Phone:</b> {phone}
<b>Username:</b> @{username if username else 'N/A'}
<b>Joined:</b> {join_date[:10]}
<b>Draws Joined:</b> {draw_count}

<b>Status:</b> ✅ Registered
"""
    else:
        profile_text = """
❌ <b>Not Registered</b>

Please register with your phone number first using /register

ကျေးဇူးပြုပြီး ဖုန်းနံပါတ်နဲ့ မှတ်ပုံတင်ပါ
"""
    
    send_telegram_message(chat_id, profile_text)

def handle_stats(chat_id):
    """Bot statistics ကြည့်မယ်"""
    conn = sqlite3.connect('lucky_draw.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM participants")
    participant_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
    user_count = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

<b>Registered Users:</b> {user_count}
<b>Draw Participants:</b> {participant_count}
<b>Bot Status:</b> 🟢 Online
<b>Server:</b> Render.com
<b>Python:</b> 3.13 Compatible
"""
    send_telegram_message(chat_id, stats_text)

@app.route('/')
def home():
    """Home page - Web browser ကနေဝင်ကြည့်ရင် ဒါပြမယ်"""
    conn = sqlite3.connect('lucky_draw.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM participants")
    participant_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
    user_count = cursor.fetchone()[0]
    conn.close()
    
    return f

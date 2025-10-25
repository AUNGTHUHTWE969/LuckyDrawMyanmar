import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class LuckyDrawBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_url = os.getenv('WEBHOOK_URL')
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect('luckydraw.db')
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Draw events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS draw_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                prize TEXT,
                winner_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                draw_date DATETIME
            )
        ''')
        
        # Participants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draw_id INTEGER,
                user_id INTEGER,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (draw_id) REFERENCES draw_events (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Winners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draw_id INTEGER,
                user_id INTEGER,
                won_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (draw_id) REFERENCES draw_events (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")
    
    def setup_handlers(self):
        """Setup bot command handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("register", self.register))
        self.application.add_handler(CommandHandler("create_draw", self.create_draw))
        self.application.add_handler(CommandHandler("list_draws", self.list_draws))
        self.application.add_handler(CommandHandler("join_draw", self.join_draw))
        self.application.add_handler(CommandHandler("draw_winner", self.draw_winner))
        self.application.add_handler(CommandHandler("my_tickets", self.my_tickets))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        welcome_text = f"""
🧧 ကြိုဆိုပါတယ် {user.mention_html()}!

Lucky Draw Myanmar Bot မှ နေပြီး ဆုကြေးပွဲများ ဝင်ရောက်ယူနိုင်ပါတယ်။

အသုံးပြုနည်းများ:
/register - စာရင်းသွင်းရန်
/create_draw - ဆွဲကံပွဲအသစ်ဖန်တီးရန်
/list_draws - ဆွဲကံပွဲများ ကြည့်ရန်
/join_draw - ဆွဲကံပွဲတွင်ပါဝင်ရန်
/my_tickets - ကိုယ့်တီကတ်များ ကြည့်ရန်
/draw_winner - ဆုရှင်ဆွဲရန် (Admin)
        """
        await update.message.reply_html(welcome_text)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 အကူအညီများ:

1. ပထမဆုံး /register ဖြင့် စာရင်းသွင်းပါ
2. /list_draws ဖြင့် ရှိပြီးသား ပွဲများကို ကြည့်ပါ
3. /join_draw <ပွဲနံပါတ်> ဖြင့် ဝင်ရောက်ယူပါ
4. Admin များအနေဖြင့် /create_draw ဖြင့် ပွဲအသစ်ဖန်တီးနိုင်ပါတယ်

ဥပမာ:
/join_draw 1
        """
        await update.message.reply_text(help_text)
    
    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        conn = sqlite3.connect('luckydraw.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)',
                (user.id, user.username, user.full_name)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                await update.message.reply_text("✅ စာရင်းသွင်းမှု အောင်မြင်ပါသည်!")
            else:
                await update.message.reply_text("ℹ️  သင့်အား စာရင်းသွင်းပြီးသားဖြစ်ပါသည်။")
                
        except Exception as e:
            logging.error(f"Registration error: {e}")
            await update.message.reply_text("❌ စာရင်းသွင်းရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        
        finally:
            conn.close()
    
    async def create_draw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check if user is admin
        user = update.effective_user
        if str(user.id) not in os.getenv('ADMIN_IDS', '').split(','):
            await update.message.reply_text("❌ ဤအမိန့်ကို အသုံးပြုခွင့် မရှိပါ။")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text("""
📝 ပွဲဖန်တီးရန် format:
/create_draw <ပွဲအမည်> <ဆုကြေး> <ဆုရှင်အရေအတွက်>

ဥပမာ:
/create_draw "နှစ်သစ်ဆုကြေးပွဲ" "ငွေကျပ် ၁၀၀၀၀၀" 3
            """)
            return
        
        draw_name = context.args[0]
        prize = context.args[1]
        winner_count = int(context.args[2])
        
        conn = sqlite3.connect('luckydraw.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO draw_events (name, prize, winner_count, created_by) VALUES (?, ?, ?, ?)',
                (draw_name, prize, winner_count, user.id)
            )
            conn.commit()
            draw_id = cursor.lastrowid
            
            await update.message.reply_text(f"""
✅ ဆွဲကံပွဲအသစ် ဖန်တီးပြီးပါပြီ!

ပွဲအမည်: {draw_name}
ဆုကြေး: {prize}
ဆုရှင်အရေ: {winner_count} ဦး
ပွဲအမှတ်: {draw_id}

အခြားသူများ ဝင်ရောက်ရန်:
/join_draw {draw_id}
            """)
            
        except Exception as e:
            logging.error(f"Create draw error: {e}")
            await update.message.reply_text("❌ ပွဲဖန်တီးရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        
        finally:
            conn.close()
    
    async def list_draws(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        conn = sqlite3.connect('luckydraw.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, name, prize, winner_count, status 
                FROM draw_events 
                WHERE status = 'active'
                ORDER BY created_at DESC
            ''')
            draws = cursor.fetchall()
            
            if not draws:
                await update.message.reply_text("ℹ️  လက်ရှိတွင် ဆွဲကံပွဲမရှိပါ။")
                return
            
            draws_text = "🎯 လက်ရှိဆွဲကံပွဲများ:\n\n"
            for draw in draws:
                draw_id, name, prize, winner_count, status = draw
                draws_text += f"""
#{draw_id} - {name}
ဆုကြေး: {prize}
ဆုရှင်: {winner_count} ဦး
ဝင်ရောက်ရန်: /join_draw {draw_id}
────────────────────
                """
            
            await update.message.reply_text(draws_text)
            
        except Exception as e:
            logging.error(f"List draws error: {e}")
            await update.message.reply_text("❌ ပွဲစာရင်းရယူရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        
        finally:
            conn.close()
    
    async def join_draw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("""
🎫 ပွဲဝင်ရန်:
/join_draw <ပွဲအမှတ်>

ဥပမာ:
/join_draw 1
            """)
            return
        
        try:
            draw_id = int(context.args[0])
            user = update.effective_user
            
            conn = sqlite3.connect('luckydraw.db')
            cursor = conn.cursor()
            
            # Check if user is registered
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (user.id,))
            user_record = cursor.fetchone()
            
            if not user_record:
                await update.message.reply_text("❌ ကျေးဇူးပြု၍ ပထမဆုံး /register ဖြင့် စာရင်းသွင်းပါ။")
                return
            
            user_id = user_record[0]
            
            # Check if draw exists and is active
            cursor.execute('SELECT name, status FROM draw_events WHERE id = ?', (draw_id,))
            draw = cursor.fetchone()
            
            if not draw:
                await update.message.reply_text("❌ ပွဲအမှတ် မှားယွင်းနေပါသည်။")
                return
            
            draw_name, status = draw
            if status != 'active':
                await update.message.reply_text("❌ ဤဆွဲကံပွဲ ပြီးဆုံးသွားပါပြီ။")
                return
            
            # Check if already joined
            cursor.execute(
                'SELECT id FROM participants WHERE draw_id = ? AND user_id = ?',
                (draw_id, user_id)
            )
            if cursor.fetchone():
                await update.message.reply_text("ℹ️  သင် ဤပွဲသို့ ဝင်ရောက်ပြီးသားဖြစ်ပါသည်။")
                return
            
            # Join the draw
            cursor.execute(
                'INSERT INTO participants (draw_id, user_id) VALUES (?, ?)',
                (draw_id, user_id)
            )
            conn.commit()
            
            await update.message.reply_text(f"""
✅ ဆွဲကံပွဲသို့ အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ!

ပွဲအမည်: {draw_name}
ပွဲအမှတ်: {draw_id}

ကံကောင်းနိုင်စရာများ ကျေးဇူးတင်ပါတယ်! 🍀
            """)
            
        except ValueError:
            await update.message.reply_text("❌ ပွဲအမှတ်သည် နံပါတ်တစ်ခုဖြစ်ရပါမည်။")
        except Exception as e:
            logging.error(f"Join draw error: {e}")
            await update.message.reply_text("❌ ပွဲဝင်ရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        finally:
            conn.close()
    
    async def draw_winner(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if str(user.id) not in os.getenv('ADMIN_IDS', '').split(','):
            await update.message.reply_text("❌ ဤအမိန့်ကို အသုံးပြုခွင့် မရှိပါ။")
            return
        
        if not context.args:
            await update.message.reply_text("""
🏆 ဆုရှင်ဆွဲရန်:
/draw_winner <ပွဲအမှတ်>

ဥပမာ:
/draw_winner 1
            """)
            return
        
        try:
            draw_id = int(context.args[0])
            conn = sqlite3.connect('luckydraw.db')
            cursor = conn.cursor()
            
            # Get draw info
            cursor.execute('SELECT name, prize, winner_count FROM draw_events WHERE id = ?', (draw_id,))
            draw = cursor.fetchone()
            
            if not draw:
                await update.message.reply_text("❌ ပွဲအမှတ် မှားယွင်းနေပါသည်။")
                return
            
            draw_name, prize, winner_count = draw
            
            # Get participants
            cursor.execute('''
                SELECT u.telegram_id, u.full_name, u.username 
                FROM participants p 
                JOIN users u ON p.user_id = u.id 
                WHERE p.draw_id = ?
            ''', (draw_id,))
            participants = cursor.fetchall()
            
            if len(participants) < winner_count:
                await update.message.reply_text(f"❌ ဝင်ရောက်သူ {len(participants)} ဦးသာရှိပြီး ဆုရှင် {winner_count} ဦး ဆွဲရန် မလုံလောက်ပါ။")
                return
            
            # Draw winners randomly
            import random
            winners = random.sample(participants, winner_count)
            
            # Save winners
            for winner in winners:
                telegram_id, full_name, username = winner
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
                user_id = cursor.fetchone()[0]
                cursor.execute(
                    'INSERT INTO winners (draw_id, user_id) VALUES (?, ?)',
                    (draw_id, user_id)
                )
            
            # Update draw status
            cursor.execute('UPDATE draw_events SET status = "completed" WHERE id = ?', (draw_id,))
            conn.commit()
            
            # Announce winners
            winners_text = f"""
🎉 CONGRATULATIONS! 🎉

ပွဲအမည်: {draw_name}
ဆုကြေး: {prize}

ဆုရှင်များ:
"""
            for i, winner in enumerate(winners, 1):
                telegram_id, full_name, username = winner
                mention = f"@{username}" if username else full_name
                winners_text += f"{i}. {mention}\n"
            
            winners_text += f"\nဆုရှင်အားလုံးကို ဂုဏ်ပြုအပ်ပါသည်! 🥳"
            
            await update.message.reply_text(winners_text)
            
            # Notify winners individually
            for winner in winners:
                telegram_id, full_name, username = winner
                try:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=f"""
🎊 ဂုဏ်ပြုပါတယ်!

သင် {draw_name} ဆွဲကံပွဲတွင် ဆုရှင်အဖြစ် ရွေးချယ်ခြင်းခံရပါသည်!

ဆုကြေး: {prize}

ကျေးဇူးတင်ပါတယ်! 🎁
                        """
                    )
                except Exception as e:
                    logging.error(f"Could not notify winner: {e}")
            
        except Exception as e:
            logging.error(f"Draw winner error: {e}")
            await update.message.reply_text("❌ ဆုရှင်ဆွဲရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        finally:
            conn.close()
    
    async def my_tickets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        conn = sqlite3.connect('luckydraw.db')
        cursor = conn.cursor()
        
        try:
            # Get user's participations
            cursor.execute('''
                SELECT de.id, de.name, de.prize, de.status, p.joined_at
                FROM participants p
                JOIN draw_events de ON p.draw_id = de.id
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = ?
                ORDER BY p.joined_at DESC
            ''', (user.id,))
            tickets = cursor.fetchall()
            
            if not tickets:
                await update.message.reply_text("ℹ️  သင် ယခုအချိန်ထိ ဆွဲကံပွဲများတွင် မပါဝင်ရသေးပါ။\n\n/list_draws ဖြင့် ပွဲများကြည့်ပြီး ဝင်ရောက်နိုင်ပါတယ်။")
                return
            
            tickets_text = "🎫 သင့်တီကတ်များ:\n\n"
            for ticket in tickets:
                draw_id, name, prize, status, joined_at = ticket
                status_emoji = "✅" if status == 'completed' else "⏳"
                tickets_text += f"""
{status_emoji} {name}
ဆုကြေး: {prize}
အခြေအနေ: {status}
ဝင်ရောက်သည့်နေ့: {joined_at[:10]}
────────────────────
                """
            
            await update.message.reply_text(tickets_text)
            
        except Exception as e:
            logging.error(f"My tickets error: {e}")
            await update.message.reply_text("❌ တီကတ်များရယူရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။")
        finally:
            conn.close()

# Initialize bot
bot = LuckyDrawBot()

@app.route('/')
def home():
    return "Lucky Draw Myanmar Bot is Running! 🎯"

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook endpoint for Telegram"""
    update = Update.de_json(request.get_json(), bot.application.bot)
    await bot.application.process_update(update)
    return 'OK'

def set_webhook():
    """Set webhook on startup"""
    if os.getenv('WEBHOOK_URL'):
        webhook_url = f"{os.getenv('WEBHOOK_URL')}/webhook"
        bot.application.bot.set_webhook(webhook_url)
        logging.info(f"Webhook set to: {webhook_url}")

if __name__ == '__main__':
    set_webhook()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Import your modules
from database_manager import DatabaseManager
from auth_system import AuthSystem
from payment_system import PaymentSystem
from lottery_system import LotterySystem
from advertising_system import AdvertisingSystem
import config

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class LuckyDrawMyanmarBot:
    def __init__(self):
        # Use environment variable for bot token
        self.bot_token = config.BOT_TOKEN
        if self.bot_token == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ BOT_TOKEN environment variable not set!")
            raise ValueError("Please set BOT_TOKEN environment variable")
        
        self.db = DatabaseManager(config.DATABASE_NAME)
        self.updater = Updater(self.bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Initialize systems
        self.payment_system = PaymentSystem(self.db)
        self.lottery_system = LotterySystem(self.db, self.updater.bot)
        self.advertising_system = AdvertisingSystem(self.db, self.updater.bot)
        self.auth_system = AuthSystem(self.db)
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all message handlers"""
        # Start command
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        
        # Auth commands
        self.dispatcher.add_handler(CommandHandler("register", self.auth_system.start_registration))
        self.dispatcher.add_handler(CommandHandler("login", self.auth_system.start_login))
        self.dispatcher.add_handler(CommandHandler("forgotpw", self.auth_system.start_password_reset))
        
        # Payment commands
        self.dispatcher.add_handler(CommandHandler("deposit", self.payment_system.deposit_menu))
        self.dispatcher.add_handler(CommandHandler("withdraw", self.payment_system.withdraw_menu))
        self.dispatcher.add_handler(CommandHandler("paymentinfo", self.payment_system.show_payment_info))
        
        # Lottery commands
        self.dispatcher.add_handler(CommandHandler("buyticket", self.buy_ticket))
        self.dispatcher.add_handler(CommandHandler("mytickets", self.my_tickets))
        
        # Advertising commands
        self.dispatcher.add_handler(CommandHandler("addad", self.advertising_system.start_ad_creation))
        
        # Admin commands
        self.dispatcher.add_handler(CommandHandler("admin", self.admin_panel))
        
        # Message handlers
        self.dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r'^🏠 ပင်မမီနူး$'), self.show_main_menu))
        self.dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r'^💰 ငွေသွင်း$'), self.payment_system.deposit_menu))
        self.dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r'^📱 KPay$|^📱 WavePay$'), self.handle_payment_method))
        
        # Text message handler
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_text_messages))
        
        # Photo message handler (for deposit screenshots)
        self.dispatcher.add_handler(MessageHandler(Filters.photo, self.handle_photo_messages))
    
    def start(self, update: Update, context: CallbackContext):
        """Start command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name)
        
        welcome_text = (
            f"🎉 **LUCKY DRAW MYANMAR မှ ကြိုဆိုပါတယ်!** 🎉\n\n"
            f"👋 မင်္ဂလာပါ {user.first_name}!\n\n"
            f"**LUCKY DRAW MYANMAR** သည် နေ့စဉ်ကံစမ်းမဲနှင့် ကြော်ငြာဝန်ဆောင်မှုများ ပေးပါသည်။\n\n"
            f"🎯 **ဝန်ဆောင်မှုများ:**\n"
            f"• 🎰 နေ့စဉ်ကံစမ်းမဲ\n" 
            f"• 📢 ကြော်ငြာအပ်နှံမှု\n"
            f"• 💰 ငွေသွင်း/ထုတ်ဝန်ဆောင်မှု\n\n"
            f"ကျေးဇူးပြု၍ အောက်ပါမီနူးမှ ရွေးချယ်ပါ:"
        )
        
        update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=self.create_main_menu()
        )
    
    def create_main_menu(self):
        """Create main menu"""
        menu = [
            [KeyboardButton("💰 ငွေသွင်း"), KeyboardButton("💸 ငွေထုတ်")],
            [KeyboardButton("📊 လက်ကျန်ငွေ"), KeyboardButton("🏦 ငွေလွှဲအချက်အလက်")],
            [KeyboardButton("🎰 ကံစမ်းမဲဝယ်ရန်"), KeyboardButton("📢 ကြော်ငြာအပ်ရန်")],
            [KeyboardButton("📋 စည်းမျဉ်းများ"), KeyboardButton("🆘 အကူအညီ")]
        ]
        return ReplyKeyboardMarkup(menu, resize_keyboard=True)
    
    def show_main_menu(self, update: Update, context: CallbackContext):
        """Show main menu"""
        update.message.reply_text(
            "🏠 **ပင်မမီနူး**\n\nကျေးဇူးပြု၍ ရွေးချယ်ပါ...",
            reply_markup=self.create_main_menu(),
            parse_mode='Markdown'
        )
    
    def handle_payment_method(self, update: Update, context: CallbackContext):
        """Handle payment method selection"""
        method = update.message.text.replace('📱 ', '')
        self.payment_system.handle_deposit_method(update, context, method)
    
    def handle_text_messages(self, update: Update, context: CallbackContext):
        """Handle text messages"""
        text = update.message.text
        
        # Handle registration steps
        if 'registration' in context.user_data:
            step = context.user_data['registration'].get('step')
            if step == 'phone':
                self.auth_system.handle_registration_phone(update, context)
            elif step == 'email_optional':
                self.auth_system.handle_registration_email_optional(update, context)
            elif step == 'register_name':
                self.auth_system.handle_registration_name(update, context)
            elif step == 'password':
                self.auth_system.handle_registration_password(update, context)
            elif step == 'confirm' and text == '✅ အတည်ပြုသည်':
                self.auth_system.complete_registration(update, context)
        
        # Handle login steps
        elif context.user_data.get('login_step') == 'phone':
            self.auth_system.handle_login_phone(update, context)
        elif context.user_data.get('login_step') == 'password':
            self.auth_system.handle_login_password(update, context)
        
        # Handle password reset steps
        elif context.user_data.get('reset_step') == 'phone':
            self.auth_system.handle_password_reset_phone(update, context)
        elif context.user_data.get('reset_step') == 'code':
            self.auth_system.handle_password_reset_code(update, context)
        elif context.user_data.get('reset_step') == 'new_password':
            self.auth_system.handle_new_password(update, context)
        
        # Handle deposit amount
        elif context.user_data.get('waiting_deposit_amount'):
            self.payment_system.process_deposit_amount(update, context, text)
        
        # Handle withdraw amount
        elif context.user_data.get('waiting_withdraw_amount'):
            self.payment_system.process_withdraw_amount(update, context)
        elif context.user_data.get('waiting_withdraw_confirm'):
            self.payment_system.confirm_withdraw(update, context, text)
    
    def handle_photo_messages(self, update: Update, context: CallbackContext):
        """Handle photo messages (for deposit screenshots)"""
        if context.user_data.get('waiting_deposit_screenshot'):
            self.process_deposit_screenshot(update, context)
    
    def process_deposit_screenshot(self, update: Update, context: CallbackContext):
        """Process deposit screenshot"""
        photo_file = update.message.photo[-1].file_id
        user_id = update.effective_user.id
        amount = context.user_data.get('deposit_amount')
        method = context.user_data.get('deposit_method')
        
        # Create transaction record
        trans_id = self.db.create_transaction(
            user_id=user_id,
            trans_type='deposit',
            amount=amount,
            payment_method=method,
            screenshot_id=photo_file
        )
        
        # Notify admins
        self.notify_admins_deposit_request(trans_id, user_id, amount, method)
        
        # Clear user data
        context.user_data.clear()
        
        update.message.reply_text(
            f"✅ **ငွေသွင်းအချက်အလက်များလက်ခံရရှိပါသည်!**\n\n"
            f"💰 ပမာဏ: {amount:,} ကျပ်\n"
            f"📱 နည်းလမ်း: {method}\n"
            f"📋 အိုင်ဒီ: #{trans_id}\n\n"
            "Admin မှခွင့်ပြုသည်အထိ စောင့်ဆိုင်းပေးပါ\n"
            "⏰ 5-15 မိနစ်ခန့်ကြာမြင့်နိုင်သည်",
            parse_mode='Markdown',
            reply_markup=self.create_main_menu()
        )
    
    def notify_admins_deposit_request(self, trans_id, user_id, amount, method):
        """Notify admins about deposit request"""
        user = self.db.get_user_by_id(user_id)
        user_info = f"{user[6]} (@{user[1]})" if user else "User"
        
        message = (
            f"🟡 **ငွေသွင်းခွင့်ပြုရန်**\n\n"
            f"📋 အိုင်ဒီ: #{trans_id}\n"
            f"👤 အသုံးပြုသူ: {user_info}\n"
            f"💰 ပမာဏ: {amount:,} MMK\n"
            f"📱 နည်းလမ်း: {method}\n\n"
            f"✅ ခွင့်ပြုရန်: /approve_{trans_id}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                self.updater.bot.send_message(admin_id, message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    def buy_ticket(self, update: Update, context: CallbackContext):
        """Buy lottery ticket"""
        user_id = update.effective_user.id
        user = self.db.get_user_by_id(user_id)
        
        if not user:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ အကောင့်ဝင်ပါ: /login")
            return
        
        balance = user[7]
        ticket_price = config.TICKET_PRICE
        
        if balance < ticket_price:
            update.message.reply_text(
                f"❌ **လက်ကျန်ငွေမလုံလောက်ပါ**\n\n"
                f"💰 လက်ကျန်ငွေ: {balance:,} ကျပ်\n"
                f"🎫 မဲဈေး: {ticket_price:,} ကျပ်\n\n"
                f"💵 ငွေသွင်းရန်: /deposit"
            )
            return
        
        # Buy ticket
        today = datetime.now().strftime('%Y-%m-%d')
        success, ticket_number = self.db.buy_ticket(user_id, ticket_price, today)
        
        if success:
            update.message.reply_text(
                f"✅ **မဲဝယ်ယူအောင်မြင်ပါသည်!**\n\n"
                f"🎫 **မဲနံပါတ်:** {ticket_number}\n"
                f"💰 **ဈေးနှုန်း:** {ticket_price:,} ကျပ်\n"
                f"📅 **ထိုးမည့်ရက်:** {today}\n"
                f"⏰ **ဆုချီးမြှင့်ချိန်:** {config.DAILY_DRAW_TIME}\n\n"
                f"🍀 **ကံကောင်းပါစေ!**"
            )
        else:
            update.message.reply_text("❌ မဲဝယ်ယူရာတွင် အမှားတစ်ခုဖြစ်နေသည်")
    
    def my_tickets(self, update: Update, context: CallbackContext):
        """Show user's tickets"""
        user_id = update.effective_user.id
        tickets = self.db.get_user_tickets(user_id)
        
        if not tickets:
            update.message.reply_text("❌ သင့်မှာ မဲမရှိသေးပါ\n\n🎫 မဲဝယ်ရန်: /buyticket")
            return
        
        ticket_text = f"🎫 **သင့်ရဲ့မဲများ** ({len(tickets)} ခု)\n\n"
        
        for i, ticket in enumerate(tickets, 1):
            ticket_text += (
                f"{i}. **မဲနံပါတ်:** {ticket[2]}\n"
                f"   **ရက်စွဲ:** {ticket[5]}\n"
                f"   **အခြေအနေ:** {ticket[6]}\n\n"
            )
        
        update.message.reply_text(ticket_text, parse_mode='Markdown')
    
    def admin_panel(self, update: Update, context: CallbackContext):
        """Admin panel"""
        if update.effective_user.id not in config.ADMIN_IDS:
            update.message.reply_text("❌ Admin only!")
            return
        
        admin_text = (
            "🏛️ **Admin Panel**\n\n"
            "**စီမံခန့်ခွဲမှုများ:**\n"
            "• 👥 အသုံးပြုသူများ\n"
            "• 💰 ငွေသွင်းခွင့်ပြုရန်\n"
            "• 💸 ငွေထုတ်ခွင့်ပြုရန်\n"
            "• 📢 ကြော်ငြာခွင့်ပြုရန်\n"
            "• 📊 စာရင်းဇယားများ\n\n"
            "**Commands:**\n"
            "/users - အသုံးပြုသူစာရင်း\n"
            "/pending - စောင့်ဆိုင်းအီးများ\n"
            "/stats - စာရင်းဇယား"
        )
        
        update.message.reply_text(admin_text, parse_mode='Markdown')
    
    def run(self):
        """Run the bot"""
        logger.info("🤖 Starting Lucky Draw Myanmar Bot...")
        self.updater.start_polling()
        logger.info("✅ Bot is running successfully!")
        self.updater.idle()

if __name__ == '__main__':
    bot = LuckyDrawMyanmarBot()
    bot.run()

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from database_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)

class PaymentSystem:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def show_payment_info(self, update: Update, context: CallbackContext):
        """Show payment information"""
        payment_text = (
            "🏦 **ငွေလွှဲအချက်အလက်**\n\n"
            "📱 **ငွေလွှဲနည်းလမ်းများ:**\n\n"
        )
        
        for method, details in config.PAYMENT_METHODS.items():
            payment_text += (
                f"💳 **{method}:**\n"
                f"👤 အမည်: {details['name']}\n"
                f"📞 ဖုန်းနံပါတ်: {details['phone']}\n\n"
            )
        
        payment_text += (
            "⚠️ **သတိပြုရန်:** အထက်ပါအကောင့်များသို့သာ ငွေလွှဲပါ\n"
            "💰 ငွေသွင်းရန်: /deposit\n"
            "💸 ငွေထုတ်ရန်: /withdraw"
        )
        
        update.message.reply_text(payment_text, parse_mode='Markdown')
    
    def deposit_menu(self, update: Update, context: CallbackContext):
        """Deposit menu"""
        deposit_text = (
            "💰 **ငွေသွင်းရန်**\n\n"
            "ကျေးဇူးပြု၍ ငွေလွှဲနည်းလမ်းရွေးပါ\n\n"
            f"🏦 **အကောင့်အချက်အလက်:**\n"
            f"👤 {config.PAYMENT_METHODS['KPay']['name']}\n"
            f"📞 {config.PAYMENT_METHODS['KPay']['phone']}"
        )
        
        keyboard = [
            [KeyboardButton("📱 KPay"), KeyboardButton("📱 WavePay")],
            [KeyboardButton("🏠 ပင်မမီနူး")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        update.message.reply_text(deposit_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        context.user_data['waiting_deposit_method'] = True
    
    def handle_deposit_method(self, update: Update, context: CallbackContext, method):
        """Handle deposit method selection"""
        context.user_data['deposit_method'] = method
        context.user_data['waiting_deposit_method'] = False
        context.user_data['waiting_deposit_amount'] = True
        
        method_info = config.PAYMENT_METHODS.get(method, {})
        
        instructions = (
            f"📱 **{method} ဖြင့်ငွေသွင်းရန်**\n\n"
            f"💳 **အကောင့်အချက်အလက်:**\n"
            f"👤 အမည်: {method_info.get('name', '')}\n"
            f"📞 ဖုန်းနံပါတ်: {method_info.get('phone', '')}\n\n"
            f"ကျေးဇူးပြု၍ ငွေပမာဏရိုက်ထည့်ပါ:\n"
            f"Example: 10000"
        )
        
        update.message.reply_text(instructions, parse_mode='Markdown')
    
    def process_deposit_amount(self, update: Update, context: CallbackContext, amount):
        """Process deposit amount"""
        try:
            amount = int(amount)
            if amount < 1000:
                update.message.reply_text("❌ အနည်းဆုံးငွေပမာဏ 1,000 ကျပ် ဖြစ်ပါသည်")
                return
            
            context.user_data['deposit_amount'] = amount
            context.user_data['waiting_deposit_amount'] = False
            context.user_data['waiting_deposit_screenshot'] = True
            
            confirm_text = (
                f"✅ **ငွေပမာဏ: {amount:,} ကျပ်**\n"
                f"📱 **ငွေလွှဲနည်း: {context.user_data['deposit_method']}**\n\n"
                "ကျေးဇူးပြု၍ ငွေလွှဲအောင်မြင်သည့် screenshot ပုံကို ပို့ပေးပါ"
            )
            
            update.message.reply_text(confirm_text, parse_mode='Markdown')
            
        except ValueError:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းအမှန်ရိုက်ထည့်ပါ")
    
    def withdraw_menu(self, update: Update, context: CallbackContext):
        """Withdraw menu"""
        user_id = update.effective_user.id
        balance = self.db.get_user_balance(user_id)
        
        if balance < 1000:
            update.message.reply_text(
                "❌ **လက်ကျန်ငွေမလုံလောက်ပါ**\n\n"
                "ငွေထုတ်ရန် အနည်းဆုံး 1,000 ကျပ် လိုအပ်ပါသည်\n"
                "💰 ငွေသွင်းရန်: /deposit"
            )
            return
        
        context.user_data['waiting_withdraw_amount'] = True
        
        withdraw_text = (
            f"💸 **ငွေထုတ်ရန်**\n\n"
            f"💰 **လက်ကျန်ငွေ: {balance:,} ကျပ်**\n"
            f"📱 **ငွေလက်ခံမည့်ဖုန်းနံပါတ်ရိုက်ထည့်ပါ:**\n"
            f"Example: 09759998877"
        )
        
        update.message.reply_text(withdraw_text, parse_mode='Markdown')
    
    def process_withdraw_amount(self, update: Update, context: CallbackContext):
        """Process withdraw amount"""
        try:
            phone_number = update.message.text
            user_id = update.effective_user.id
            balance = self.db.get_user_balance(user_id)
            
            # Validate phone number
            if not phone_number.startswith('09') or len(phone_number) != 11:
                update.message.reply_text("❌ မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ")
                return
            
            context.user_data['withdraw_phone'] = phone_number
            context.user_data['waiting_withdraw_amount'] = False
            context.user_data['waiting_withdraw_confirm'] = True
            
            confirm_text = (
                f"✅ **ငွေလက်ခံမည့်ဖုန်း: {phone_number}**\n"
                f"💰 **လက်ကျန်ငွေ: {balance:,} ကျပ်**\n\n"
                f"ကျေးဇူးပြု၍ ထုတ်ယူမည့်ငွေပမာဏရိုက်ထည့်ပါ:\n"
                f"Example: 5000"
            )
            
            update.message.reply_text(confirm_text, parse_mode='Markdown')
            
        except Exception as e:
            update.message.reply_text("❌ အမှားတစ်ခုဖြစ်နေသည်")
    
    def confirm_withdraw(self, update: Update, context: CallbackContext, amount):
        """Confirm withdraw request"""
        try:
            amount = int(amount)
            user_id = update.effective_user.id
            balance = self.db.get_user_balance(user_id)
            phone_number = context.user_data.get('withdraw_phone')
            
            if amount < 1000:
                update.message.reply_text("❌ အနည်းဆုံးငွေပမာဏ 1,000 ကျပ် ဖြစ်ပါသည်")
                return
            
            if amount > balance:
                update.message.reply_text("❌ လက်ကျန်ငွေမလုံလောက်ပါ")
                return
            
            # Create withdraw transaction
            trans_id = self.db.create_transaction(
                user_id=user_id,
                trans_type='withdraw',
                amount=amount,
                phone_number=phone_number
            )
            
            # Notify admins
            self.notify_admins_withdraw_request(trans_id, user_id, amount, phone_number)
            
            # Clear user data
            context.user_data.clear()
            
            update.message.reply_text(
                f"✅ **ငွေထုတ်အချက်အလက်များလက်ခံရရှိပါသည်!**\n\n"
                f"💰 ပမာဏ: {amount:,} ကျပ်\n"
                f"📱 ဖုန်းနံပါတ်: {phone_number}\n"
                f"📋 အိုင်ဒီ: #{trans_id}\n\n"
                "Admin မှခွင့်ပြုသည်အထိ စောင့်ဆိုင်းပေးပါ\n"
                "⏰ 5-15 မိနစ်ခန့်ကြာမြင့်နိုင်သည်",
                parse_mode='Markdown'
            )
            
        except ValueError:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းအမှန်ရိုက်ထည့်ပါ")
    
    def notify_admins_withdraw_request(self, trans_id, user_id, amount, phone_number):
        """Notify admins about withdraw request"""
        user = self.db.get_user_by_id(user_id)
        user_info = f"{user[6]} (@{user[1]})" if user else "User"
        
        message = (
            f"🟡 **ငွေထုတ်ခွင့်ပြုရန်**\n\n"
            f"📋 အိုင်ဒီ: #{trans_id}\n"
            f"👤 အသုံးပြုသူ: {user_info}\n"
            f"💰 ပမာဏ: {amount:,} MMK\n"
            f"📱 ဖုန်းနံပါတ်: {phone_number}\n\n"
            f"✅ ခွင့်ပြုရန်: /approve_{trans_id}\n"
            f"❌ ပယ်ဖျက်ရန်: /reject_{trans_id}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                from main_bot import LuckyDrawMyanmarBot
                bot = LuckyDrawMyanmarBot()
                bot.updater.bot.send_message(admin_id, message, parse_mode='Markdown')
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")

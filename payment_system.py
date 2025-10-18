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
        
        context.user_data['waiting_withdraw_name'] = True
        
        withdraw_text = (
            f"💸 **ငွေထုတ်ရန်**\n\n"
            f"💰 **လက်ကျန်ငွေ: {balance:,} ကျပ်**\n"
            f"👤 **ကျေးဇူးပြု၍ သင့်အမည်အပြည့်အစုံရိုက်ထည့်ပါ:**\n"
            f"Example: ကိုအောင်မျိုးမင်း"
        )
        
        update.message.reply_text(withdraw_text, parse_mode='Markdown')
    
    def process_withdraw_name(self, update: Update, context: CallbackContext):
        """Process withdraw name input"""
        withdrawer_name = update.message.text
        
        if len(withdrawer_name) < 2:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ မှန်ကန်သောအမည်ရိုက်ထည့်ပါ")
            return
        
        context.user_data['withdrawer_name'] = withdrawer_name
        context.user_data['waiting_withdraw_name'] = False
        context.user_data['waiting_withdraw_phone'] = True
        
        update.message.reply_text(
            f"✅ **အမည်လက်ခံရရှိပါသည်: {withdrawer_name}**\n\n"
            f"📱 **ကျေးဇူးပြု၍ ငွေလက်ခံမည့်ဖုန်းနံပါတ်ရိုက်ထည့်ပါ:**\n"
            f"Example: 09759998877",
            parse_mode='Markdown'
        )
    
    def process_withdraw_phone(self, update: Update, context: CallbackContext):
        """Process withdraw phone number input"""
        try:
            phone_number = update.message.text
            user_id = update.effective_user.id
            balance = self.db.get_user_balance(user_id)
            withdrawer_name = context.user_data.get('withdrawer_name')
            
            # Validate phone number
            if not phone_number.startswith('09') or len(phone_number) != 11:
                update.message.reply_text("❌ မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ")
                return
            
            context.user_data['withdraw_phone'] = phone_number
            context.user_data['waiting_withdraw_phone'] = False
            context.user_data['waiting_withdraw_amount'] = True
            
            confirm_text = (
                f"✅ **ငွေထုတ်သူအမည်: {withdrawer_name}**\n"
                f"✅ **ငွေလက်ခံမည့်ဖုန်း: {phone_number}**\n"
                f"💰 **လက်ကျန်ငွေ: {balance:,} ကျပ်**\n\n"
                f"ကျေးဇူးပြု၍ ထုတ်ယူမည့်ငွေပမာဏရိုက်ထည့်ပါ:\n"
                f"Example: 5000"
            )
            
            update.message.reply_text(confirm_text, parse_mode='Markdown')
            
        except Exception as e:
            update.message.reply_text("❌ အမှားတစ်ခုဖြစ်နေသည်")
    
    def process_withdraw_amount(self, update: Update, context: CallbackContext, amount):
        """Process withdraw amount"""
        try:
            amount = int(amount)
            user_id = update.effective_user.id
            balance = self.db.get_user_balance(user_id)
            phone_number = context.user_data.get('withdraw_phone')
            withdrawer_name = context.user_data.get('withdrawer_name')
            
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
            
            # Notify admins with complete information
            self.notify_admins_withdraw_request(trans_id, user_id, amount, phone_number, withdrawer_name)
            
            # Clear user data
            context.user_data.clear()
            
            update.message.reply_text(
                f"✅ **ငွေထုတ်အချက်အလက်များလက်ခံရရှိပါသည်!**\n\n"
                f"👤 **ငွေထုတ်သူအမည်:** {withdrawer_name}\n"
                f"💰 **ပမာဏ:** {amount:,} ကျပ်\n"
                f"📱 **ဖုန်းနံပါတ်:** {phone_number}\n"
                f"📋 **အိုင်ဒီ:** #{trans_id}\n\n"
                "Admin မှခွင့်ပြုသည်အထိ စောင့်ဆိုင်းပေးပါ\n"
                "⏰ 5-15 မိနစ်ခန့်ကြာမြင့်နိုင်သည်",
                parse_mode='Markdown'
            )
            
        except ValueError:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ ဂဏန်းအမှန်ရိုက်ထည့်ပါ")
    
    def notify_admins_withdraw_request(self, trans_id, user_id, amount, phone_number, withdrawer_name):
        """Notify admins about withdraw request"""
        user = self.db.get_user_by_id(user_id)
        
        if user:
            # User information from database
            username = user[1] or "No Username"
            first_name = user[2] or "No First Name"
            register_name = user[6] or "No Registered Name"
            user_phone = user[3] or "No Phone"
            
            user_info = (
                f"👤 **အကောင့်အမည်:** {register_name}\n"
                f"📞 **အကောင့်ဖုန်း:** {user_phone}\n"
                f"👨‍💼 **Username:** @{username}\n"
                f"👋 **First Name:** {first_name}"
            )
        else:
            user_info = "❌ User information not found"
        
        message = (
            f"🟡 **ငွေထုတ်ခွင့်ပြုရန်**\n\n"
            f"📋 **လွှဲပြောင်းအိုင်ဒီ:** #{trans_id}\n"
            f"💰 **ငွေပမာဏ:** {amount:,} ကျပ်\n\n"
            f"**ငွေထုတ်သူအချက်အလက်:**\n"
            f"👤 **အမည်:** {withdrawer_name}\n"
            f"📞 **ဖုန်းနံပါတ်:** {phone_number}\n\n"
            f"**အကောင့်အချက်အလက်:**\n"
            f"{user_info}\n\n"
            f"⏰ **အချိန်:** {self.get_current_time()}\n\n"
            f"✅ **ခွင့်ပြုရန်:** /approve_{trans_id}\n"
            f"❌ **ပယ်ဖျက်ရန်:** /reject_{trans_id}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                from main_bot import bot_instance
                if bot_instance:
                    bot_instance.updater.bot.send_message(admin_id, message, parse_mode='Markdown')
                else:
                    print(f"Bot instance not available for admin notification")
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")
    
    def get_current_time(self):
        """Get current formatted time"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def show_withdrawal_history(self, update: Update, context: CallbackContext, status_filter=None):
        """Show withdrawal history for admin"""
        if update.effective_user.id not in config.ADMIN_IDS:
            update.message.reply_text("❌ Admin only!")
            return
        
        withdrawals = self.db.get_all_withdrawals(status_filter)
        
        if not withdrawals:
            status_text = "စောင့်ဆိုင်းနေသော" if status_filter == 'pending' else ""
            update.message.reply_text(f"📭 {status_text}ငွေထုတ်မှုမှတ်တမ်းမရှိပါ")
            return
        
        status_text = "စောင့်ဆိုင်းနေသော" if status_filter == 'pending' else ""
        history_text = f"📊 **{status_text}ငွေထုတ်မှုမှတ်တမ်း** ({len(withdrawals)} ခု)\n\n"
        
        for i, withdraw in enumerate(withdrawals, 1):
            trans_id, user_id, trans_type, amount, status, payment_method, phone_number, screenshot_id, created_at, processed_at, processed_by, username, first_name, register_name, user_phone = withdraw
            
            history_text += (
                f"**#{i}** | **ID:** #{trans_id}\n"
                f"👤 **အသုံးပြုသူ:** {register_name} (@{username})\n"
                f"📞 **ဖုန်း:** {user_phone}\n"
                f"💰 **ပမာဏ:** {amount:,} ကျပ်\n"
                f"📱 **လက်ခံဖုန်း:** {phone_number}\n"
                f"📊 **အခြေအနေ:** {self.get_status_text(status)}\n"
                f"⏰ **တောင်းဆိုချိန်:** {created_at[:16]}\n"
            )
            
            if processed_at:
                history_text += f"✅ **ခွင့်ပြုချိန်:** {processed_at[:16]}\n"
            
            history_text += "─" * 30 + "\n\n"
        
        update.message.reply_text(history_text, parse_mode='Markdown')
    
    def get_status_text(self, status):
        """Convert status to Myanmar text"""
        status_map = {
            'pending': '⏳ စောင့်ဆိုင်းနေသည်',
            'approved': '✅ အောင်မြင်ပါသည်', 
            'rejected': '❌ ပယ်ဖျက်သည်'
        }
        return status_map.get(status, status)

import re
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from database_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)

class AuthSystem:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def validate_phone_number(self, phone_number):
        """Validate all Myanmar phone number formats"""
        # Remove any spaces, dashes, or plus signs
        cleaned_phone = re.sub(r'[\s+\-]', '', phone_number)
        
        # Myanmar phone number patterns for all operators
        patterns = [
            r'^09\d{8,9}$',           # Standard 09 numbers
            r'^9\d{8,9}$',            # Without leading 0
            r'^959\d{8,9}$',          # International format without +
            r'^\+959\d{8,9}$',        # International format with +
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned_phone):
                return True
        return False
    
    def format_phone_number(self, phone_number):
        """Format phone number to standard 09XXXXXXXXX format"""
        # Remove any spaces, dashes, or plus signs
        cleaned_phone = re.sub(r'[\s+\-]', '', phone_number)
        
        # Convert to standard 09 format
        if cleaned_phone.startswith('959'):
            return '09' + cleaned_phone[3:]
        elif cleaned_phone.startswith('+959'):
            return '09' + cleaned_phone[4:]
        elif cleaned_phone.startswith('9') and len(cleaned_phone) in [9, 10]:
            return '09' + cleaned_phone[1:]
        elif cleaned_phone.startswith('09'):
            return cleaned_phone
        else:
            return None
    
    def validate_password(self, password):
        """Validate password strength"""
        if len(password) < config.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long"
        
        # Check for at least one number and one letter
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_letter and has_digit):
            return False, "Password must contain both letters and numbers"
        
        return True, "Password is valid"
    
    def start_registration(self, update: Update, context: CallbackContext):
        """Start user registration process"""
        user = update.effective_user
        
        context.user_data['registration'] = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'step': 'phone'
        }
        
        update.message.reply_text(
            "📝 **အကောင့်မှတ်ပုံတင်ခြင်း**\n\n"
            "ကျေးဇူးပြု၍ သင့်ဖုန်းနံပါတ်ရိုက်ထည့်ပါ:\n"
            "ဖုန်းနံပါတ်ပုံစံများ:\n"
            "• 09759998877\n"
            "• 959775999887\n" 
            "• +959775999887\n"
            "• 97759998877\n\n"
            "မည်သည့် SIM ကဒ်မဆိုအသုံးပြုနိုင်ပါသည်",
            parse_mode='Markdown'
        )
    
    def handle_registration_phone(self, update: Update, context: CallbackContext):
        """Handle phone number input during registration"""
        phone_number = update.message.text
        
        if not self.validate_phone_number(phone_number):
            update.message.reply_text(
                "❌ **ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ**\n\n"
                "**လက်ခံသောဖုန်းနံပါတ်ပုံစံများ:**\n"
                "• 09XXXXXXXXX (MPT, Ooredoo, Telenor, Mytel, MEC)\n"
                "• 959XXXXXXXXX\n"
                "• +959XXXXXXXXX\n"
                "• 9XXXXXXXXX\n\n"
                "**Example:**\n"
                "09759998877, 959775999887, +959775999887",
                parse_mode='Markdown'
            )
            return
        
        # Format phone number to standard format
        formatted_phone = self.format_phone_number(phone_number)
        if not formatted_phone:
            update.message.reply_text("❌ **ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ**")
            return
        
        # Check if phone number already exists
        existing_user = self.db.get_user_by_phone(formatted_phone)
        if existing_user:
            update.message.reply_text(
                "❌ **ဤဖုန်းနံပါတ်ဖြင့် အကောင့်ရှိပြီးသားဖြစ်ပါသည်**\n\n"
                "ကျေးဇူးပြု၍ အကောင့်ဝင်ရန် /login ကိုသုံးပါ သို့မဟုတ် အခြားဖုန်းနံပါတ်ဖြင့်ကြိုးစားပါ"
            )
            return
        
        context.user_data['registration']['phone_number'] = formatted_phone
        context.user_data['registration']['original_phone'] = phone_number
        context.user_data['registration']['step'] = 'email_optional'
        
        update.message.reply_text(
            "✅ **ဖုန်းနံပါတ်လက်ခံရရှိပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ သင့်အီးမေးလ်လိပ်စာရိုက်ထည့်ပါ (မရှိပါက 'skip' ဟုရိုက်ထည့်ပါ):\n"
            "Example: myemail@gmail.com\n"
            "သို့မဟုတ် 'skip' ဟုရိုက်ပါ",
            parse_mode='Markdown'
        )
    
    def handle_registration_email_optional(self, update: Update, context: CallbackContext):
        """Handle optional email input"""
        email_input = update.message.text.lower()
        
        if email_input == 'skip':
            context.user_data['registration']['email'] = None
            context.user_data['registration']['step'] = 'register_name'
            
            update.message.reply_text(
                "⏭️ **အီးမေးလ်ကိုကျော်သွားပါသည်...**\n\n"
                "ကျေးဇူးပြု၍ သင့်အမည်အပြည့်အစုံရိုက်ထည့်ပါ:\n"
                "Example: ကိုအောင်မျိုးမင်း",
                parse_mode='Markdown'
            )
            return
        
        # Validate email if provided
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email_input):
            update.message.reply_text(
                "❌ **ကျေးဇူးပြု၍ မှန်ကန်သောအီးမေးလ်လိပ်စာရိုက်ထည့်ပါ သို့မဟုတ် 'skip' ဟုရိုက်ပါ**\n\n"
                "Example: myemail@gmail.com\n"
                "သို့မဟုတ် 'skip'"
            )
            return
        
        context.user_data['registration']['email'] = email_input
        context.user_data['registration']['step'] = 'register_name'
        
        update.message.reply_text(
            "✅ **အီးမေးလ်လိပ်စာလက်ခံရရှိပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ သင့်အမည်အပြည့်အစုံရိုက်ထည့်ပါ:\n"
            "Example: ကိုအောင်မျိုးမင်း",
            parse_mode='Markdown'
        )
    
    def handle_registration_name(self, update: Update, context: CallbackContext):
        """Handle register name input"""
        register_name = update.message.text
        
        if len(register_name) < 2:
            update.message.reply_text("❌ **ကျေးဇူးပြု၍ မှန်ကန်သောအမည်ရိုက်ထည့်ပါ**")
            return
        
        context.user_data['registration']['register_name'] = register_name
        context.user_data['registration']['step'] = 'password'
        
        update.message.reply_text(
            "✅ **အမည်လက်ခံရရှိပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ သင့်စကားဝှက်ရိုက်ထည့်ပါ:\n"
            f"• အနည်းဆုံး {config.PASSWORD_MIN_LENGTH} လုံး\n"
            "• စာလုံးနှင့် ဂဏန်းပါဝင်ရမည်\n"
            "Example: MyPass123",
            parse_mode='Markdown'
        )
    
    def handle_registration_password(self, update: Update, context: CallbackContext):
        """Handle password input during registration"""
        password = update.message.text
        
        is_valid, message = self.validate_password(password)
        if not is_valid:
            update.message.reply_text(f"❌ **{message}**")
            return
        
        context.user_data['registration']['password'] = password
        context.user_data['registration']['step'] = 'confirm'
        
        # Show registration summary
        reg_data = context.user_data['registration']
        
        summary = (
            "📋 **အကောင့်အချက်အလက်အတည်ပြုခြင်း**\n\n"
            f"📞 **ဖုန်းနံပါတ်:** {reg_data['phone_number']}\n"
            f"📧 **အီးမေးလ်:** {reg_data['email'] if reg_data['email'] else 'မရှိပါ'}\n"
            f"👤 **အမည်:** {reg_data['register_name']}\n\n"
            "ဤအချက်အလက်များမှန်ကန်ပါက '✅ အတည်ပြုသည်' ကိုနှိပ်ပါ"
        )
        
        keyboard = [
            [KeyboardButton("✅ အတည်ပြုသည်"), KeyboardButton("🔄 ပြန်စရန်")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    
    def complete_registration(self, update: Update, context: CallbackContext):
        """Complete user registration"""
        reg_data = context.user_data['registration']
        
        success, message = self.db.create_user(
            user_id=reg_data['user_id'],
            username=reg_data['username'],
            first_name=reg_data['first_name'],
            phone_number=reg_data['phone_number'],
            password=reg_data['password'],
            register_name=reg_data['register_name'],
            email=reg_data.get('email')
        )
        
        if success:
            # Clear registration data
            context.user_data.clear()
            
            success_message = (
                "🎉 **အကောင့်မှတ်ပုံတင်အောင်မြင်ပါသည်!**\n\n"
                f"👤 **အမည်:** {reg_data['register_name']}\n"
                f"📞 **ဖုန်း:** {reg_data['phone_number']}\n"
                f"📧 **အီးမေးလ်:** {reg_data['email'] if reg_data['email'] else 'မရှိပါ'}\n\n"
                "🔐 **အကောင့်ဝင်ရန်:** /login\n"
                "🏠 **ပင်မမီနူး:** /start"
            )
            
            update.message.reply_text(success_message, parse_mode='Markdown')
        else:
            update.message.reply_text(f"❌ **{message}**")
    
    def start_login(self, update: Update, context: CallbackContext):
        """Start login process"""
        context.user_data['login_step'] = 'phone'
        
        update.message.reply_text(
            "🔐 **အကောင့်ဝင်ရန်**\n\n"
            "ကျေးဇူးပြု၍ သင့်ဖုန်းနံပါတ်ရိုက်ထည့်ပါ:\n"
            "ဖုန်းနံပါတ်ပုံစံများ:\n"
            "• 09759998877\n"
            "• 959775999887\n"
            "• +959775999887\n"
            "• 97759998877\n\n"
            "မည်သည့် SIM ကဒ်မဆိုအသုံးပြုနိုင်ပါသည်",
            parse_mode='Markdown'
        )
    
    def handle_login_phone(self, update: Update, context: CallbackContext):
        """Handle phone number input during login"""
        phone_number = update.message.text
        
        if not self.validate_phone_number(phone_number):
            update.message.reply_text(
                "❌ **မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ**\n\n"
                "**လက်ခံသောဖုန်းနံပါတ်ပုံစံများ:**\n"
                "• 09XXXXXXXXX\n"
                "• 959XXXXXXXXX\n"
                "• +959XXXXXXXXX\n"
                "• 9XXXXXXXXX"
            )
            return
        
        # Format phone number to standard format
        formatted_phone = self.format_phone_number(phone_number)
        if not formatted_phone:
            update.message.reply_text("❌ **မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ**")
            return
        
        context.user_data['login_phone'] = formatted_phone
        context.user_data['login_original_phone'] = phone_number
        context.user_data['login_step'] = 'password'
        
        update.message.reply_text(
            f"✅ **ဖုန်းနံပါတ်လက်ခံရရှိပါသည်!**\n"
            f"📱 **ဖုန်းနံပါတ်:** {formatted_phone}\n\n"
            "ကျေးဇူးပြု၍ သင့်စကားဝှက်ရိုက်ထည့်ပါ:",
            parse_mode='Markdown'
        )
    
    def handle_login_password(self, update: Update, context: CallbackContext):
        """Handle password input during login"""
        password = update.message.text
        phone_number = context.user_data['login_phone']
        
        success, result = self.db.authenticate_user(phone_number, password)
        
        if success:
            user_id = result
            user = self.db.get_user_by_id(user_id)
            
            # Clear login data
            context.user_data.pop('login_phone', None)
            context.user_data.pop('login_step', None)
            
            welcome_message = (
                f"🎉 **အကောင့်သို့ဝင်ရောက်အောင်မြင်ပါသည်!**\n\n"
                f"👋 မင်္ဂလာပါ {user[6]}!\n\n"
                f"💰 **လက်ကျန်ငွေ:** {user[7]:,} ကျပ်\n"
                f"📅 **အကောင့်ဖွင့်သည့်ရက်:** {user[11][:10]}\n\n"
                "ကျေးဇူးပြု၍ အောက်ပါမီနူးမှ ရွေးချယ်ပါ:"
            )
            
            from main_bot import LuckyDrawMyanmarBot
            bot = LuckyDrawMyanmarBot()
            update.message.reply_text(
                welcome_message,
                reply_markup=bot.create_main_menu(),
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text(f"❌ **{result}**")
    
    def start_password_reset(self, update: Update, context: CallbackContext):
        """Start password reset process using phone number"""
        context.user_data['reset_step'] = 'phone'
        
        update.message.reply_text(
            "🔐 **စကားဝှက်ပြန်လည်သတ်မှတ်ရန်**\n\n"
            "ကျေးဇူးပြု၍ သင့်ဖုန်းနံပါတ်ရိုက်ထည့်ပါ:\n"
            "ဖုန်းနံပါတ်ပုံစံများ:\n"
            "• 09759998877\n"
            "• 959775999887\n"
            "• +959775999887\n"
            "• 97759998877\n\n"
            "မည်သည့် SIM ကဒ်မဆိုအသုံးပြုနိုင်ပါသည်",
            parse_mode='Markdown'
        )
    
    def handle_password_reset_phone(self, update: Update, context: CallbackContext):
        """Handle phone number input for password reset"""
        phone_number = update.message.text
        
        if not self.validate_phone_number(phone_number):
            update.message.reply_text(
                "❌ **မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ**\n\n"
                "**လက်ခံသောဖုန်းနံပါတ်ပုံစံများ:**\n"
                "• 09XXXXXXXXX\n"
                "• 959XXXXXXXXX\n"
                "• +959XXXXXXXXX\n"
                "• 9XXXXXXXXX"
            )
            return
        
        # Format phone number to standard format
        formatted_phone = self.format_phone_number(phone_number)
        if not formatted_phone:
            update.message.reply_text("❌ **မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ**")
            return
        
        # Check if user exists
        user = self.db.get_user_by_phone(formatted_phone)
        if not user:
            update.message.reply_text(
                "❌ **ဤဖုန်းနံပါတ်ဖြင့် အကောင့်မရှိပါ**\n\n"
                "ကျေးဇူးပြု၍ မှန်ကန်သောဖုန်းနံပါတ်ရိုက်ထည့်ပါ"
            )
            return
        
        # Generate and send reset code
        reset_code = self.db.create_phone_reset_token(formatted_phone)
        
        if reset_code:
            context.user_data['reset_phone'] = formatted_phone
            context.user_data['reset_original_phone'] = phone_number
            context.user_data['reset_step'] = 'code'
            
            update.message.reply_text(
                f"✅ **ပြန်လည်သတ်မှတ်ရန်ကုဒ်ပေးပို့ပြီးပါပြီ!**\n\n"
                f"📱 **သင့်ဖုန်းသို့ပို့ထားသောကုဒ်:** ||{reset_code}||\n\n"
                f"ကျေးဇူးပြု၍ ကုဒ်ရိုက်ထည့်ပါ:\n"
                f"Example: {reset_code}",
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text("❌ **အမှားတစ်ခုဖြစ်နေသည်**")
    
    def handle_password_reset_code(self, update: Update, context: CallbackContext):
        """Handle reset code input"""
        code = update.message.text.upper()
        phone_number = context.user_data['reset_phone']
        
        user_id = self.db.verify_phone_reset_token(phone_number, code)
        
        if not user_id:
            update.message.reply_text("❌ **မှားယွင်းသော သို့မဟုတ် သက်တမ်းကုန်သွားသော ကုဒ်**")
            return
        
        context.user_data['reset_user_id'] = user_id
        context.user_data['reset_code'] = code
        context.user_data['reset_step'] = 'new_password'
        
        update.message.reply_text(
            "✅ **ကုဒ်မှန်ကန်ပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ စကားဝှက်အသစ်ရိုက်ထည့်ပါ:\n"
            f"• အနည်းဆုံး {config.PASSWORD_MIN_LENGTH} လုံး\n"
            "• စာလုံးနှင့် ဂဏန်းပါဝင်ရမည်",
            parse_mode='Markdown'
        )
    
    def handle_new_password(self, update: Update, context: CallbackContext):
        """Handle new password input for reset"""
        new_password = update.message.text
        
        is_valid, message = self.validate_password(new_password)
        if not is_valid:
            update.message.reply_text(f"❌ **{message}**")
            return
        
        phone_number = context.user_data['reset_phone']
        code = context.user_data.get('reset_code')
        user_id = context.user_data['reset_user_id']
        
        if user_id:
            # Change password
            self.db.change_password(user_id, new_password)
            self.db.use_phone_reset_token(phone_number, code)
            
            # Clear reset data
            context.user_data.clear()
            
            update.message.reply_text(
                "✅ **စကားဝှက်ပြောင်းလဲမှုအောင်မြင်ပါသည်!**\n\n"
                "ကျေးဇူးပြု၍ အကောင့်အသစ်ဖြင့်ဝင်ရောက်ပါ\n"
                "/login - အကောင့်ဝင်ရန်",
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text("❌ **အမှားတစ်ခုဖြစ်နေသည်**")

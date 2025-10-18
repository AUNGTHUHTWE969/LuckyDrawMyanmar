import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from database_manager import DatabaseManager
import config

logger = logging.getLogger(__name__)

class AdvertisingSystem:
    def __init__(self, db_manager, bot):
        self.db = db_manager
        self.bot = bot
    
    def start_ad_creation(self, update: Update, context: CallbackContext):
        """Start advertisement creation by client"""
        user_id = update.effective_user.id
        
        context.user_data['ad_creation_step'] = 'advertiser_name'
        context.user_data['created_by'] = user_id
        
        update.message.reply_text(
            "📢 **LUCKY DRAW MYANMAR - ကြော်ငြာအပ်နှံရန်**\n\n"
            "ကျေးဇူးပြု၍ သင့်ကုမ္ပဏီ/ဆိုင်အမည်ရိုက်ထည့်ပါ:\n"
            "Example: ကုမ္ပဏီလီမိတက်",
            parse_mode='Markdown'
        )
    
    def handle_ad_creation_input(self, update: Update, context: CallbackContext, text):
        """Handle ad creation step inputs"""
        step = context.user_data.get('ad_creation_step')
        
        if step == 'advertiser_name':
            self.handle_advertiser_name(update, context, text)
        elif step == 'ad_title':
            self.handle_ad_title(update, context, text)
        elif step == 'ad_content':
            self.handle_ad_content(update, context, text)
        elif step == 'ad_type':
            self.handle_ad_type(update, context, text)
    
    def handle_advertiser_name(self, update: Update, context: CallbackContext, advertiser_name):
        """Handle advertiser name input"""
        if len(advertiser_name) < 2:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ မှန်ကန်သောအမည်ရိုက်ထည့်ပါ")
            return
        
        context.user_data['advertiser_name'] = advertiser_name
        context.user_data['ad_creation_step'] = 'ad_title'
        
        update.message.reply_text(
            "✅ **ကုမ္ပဏီအမည်လက်ခံရရှိပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ ကြော်ငြာခေါင်းစဉ်ရိုက်ထည့်ပါ:\n"
            "Example: နှစ်သစ်ဈေးလျှော့ချပွဲ",
            parse_mode='Markdown'
        )
    
    def handle_ad_title(self, update: Update, context: CallbackContext, ad_title):
        """Handle ad title input"""
        if len(ad_title) < 5:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ ကြော်ငြာခေါင်းစဉ်အပြည့်အစုံရိုက်ထည့်ပါ")
            return
        
        context.user_data['ad_title'] = ad_title
        context.user_data['ad_creation_step'] = 'ad_content'
        
        update.message.reply_text(
            "✅ **ကြော်ငြာခေါင်းစဉ်လက်ခံရရှိပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ ကြော်ငြာအကြောင်းအရာအပြည့်အစုံရိုက်ထည့်ပါ:\n"
            "Example: နှစ်သစ်မှာချစ်သူများအတွက် အထူးလက်ဆောင်များ 50% လျှော့ဈေး...",
            parse_mode='Markdown'
        )
    
    def handle_ad_content(self, update: Update, context: CallbackContext, ad_content):
        """Handle ad content input"""
        if len(ad_content) < 10:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ ကြော်ငြာအကြောင်းအရာအပြည့်အစုံရိုက်ထည့်ပါ")
            return
        
        context.user_data['ad_content'] = ad_content
        context.user_data['ad_creation_step'] = 'ad_type'
        
        ad_types_text = (
            "✅ **ကြော်ငြာအကြောင်းအရာလက်ခံရရှိပါသည်!**\n\n"
            "ကျေးဇူးပြု၍ ကြော်ငြာအမျိုးအစားရွေးချယ်ပါ:\n\n"
            "📝 **စာသားကြော်ငြာ** - စာသားသက်သက်\n"
            "🖼️ **ပုံကြော်ငြာ** - ပုံနှင့်တကွ\n"
            "🌟 **စပွန်ဆာကြော်ငြာ** - အထူးကြော်ငြာ"
        )
        
        keyboard = [
            [KeyboardButton("📝 စာသားကြော်ငြာ"), KeyboardButton("🖼️ ပုံကြော်ငြာ")],
            [KeyboardButton("🌟 စပွန်ဆာကြော်ငြာ"), KeyboardButton("🏠 ပင်မမီနူး")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        update.message.reply_text(ad_types_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def handle_ad_type(self, update: Update, context: CallbackContext, ad_type):
        """Handle ad type selection"""
        ad_type_map = {
            "📝 စာသားကြော်ငြာ": "text",
            "🖼️ ပုံကြော်ငြာ": "banner", 
            "🌟 စပွန်ဆာကြော်ငြာ": "sponsored"
        }
        
        selected_type = ad_type_map.get(ad_type)
        if not selected_type:
            update.message.reply_text("❌ ကျေးဇူးပြု၍ ကြော်ငြာအမျိုးအစားမှန်ကန်စွာရွေးချယ်ပါ")
            return
        
        context.user_data['ad_type'] = selected_type
        
        # Calculate cost and show summary
        self.show_ad_summary(update, context)
    
    def show_ad_summary(self, update: Update, context: CallbackContext):
        """Show advertisement summary and confirm"""
        ad_data = context.user_data
        
        # Calculate estimated cost (basic calculation)
        base_cost = 5000
        if ad_data['ad_type'] == 'banner':
            base_cost = 7500
        elif ad_data['ad_type'] == 'sponsored':
            base_cost = 10000
        
        summary = (
            "📋 **ကြော်ငြာအချက်အလက်အတည်ပြုခြင်း**\n\n"
            f"🏢 **ကုမ္ပဏီအမည်:** {ad_data['advertiser_name']}\n"
            f"📝 **ကြော်ငြာခေါင်းစဉ်:** {ad_data['ad_title']}\n"
            f"📄 **ကြော်ငြာအမျိုးအစား:** {ad_data['ad_type']}\n"
            f"💰 **ခန့်မှန်းကုန်ကျစရိတ်:** {base_cost:,} ကျပ်\n\n"
            "ဤကြော်ငြာအချက်အလက်များမှန်ကန်ပါက Admin ဆီသို့တင်သွင်းရန် '✅ တင်သွင်းမည်' ကိုနှိပ်ပါ"
        )
        
        keyboard = [
            [KeyboardButton("✅ တင်သွင်းမည်"), KeyboardButton("🔄 ပြန်စရန်")],
            [KeyboardButton("🏠 ပင်မမီနူး")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
        
        context.user_data['ad_creation_step'] = 'confirm'
        context.user_data['estimated_cost'] = base_cost
    
    def submit_advertisement(self, update: Update, context: CallbackContext):
        """Submit advertisement to database"""
        try:
            ad_data = context.user_data
            user_id = ad_data['created_by']
            
            cursor = self.db.conn.cursor()
            
            cursor.execute('''
                INSERT INTO advertisements 
                (advertiser_name, ad_title, ad_content, ad_type, total_cost, created_by, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            ''', (
                ad_data['advertiser_name'],
                ad_data['ad_title'], 
                ad_data['ad_content'],
                ad_data['ad_type'],
                ad_data['estimated_cost'],
                user_id
            ))
            
            ad_id = cursor.lastrowid
            self.db.conn.commit()
            
            # Notify admins
            self.notify_admins_new_ad(ad_id, ad_data)
            
            # Clear user data
            context.user_data.clear()
            
            update.message.reply_text(
                f"✅ **ကြော်ငြာအပ်နှံမှုအောင်မြင်ပါသည်!**\n\n"
                f"📋 **ကြော်ငြာအမှတ်:** #{ad_id}\n"
                f"💰 **ခန့်မှန်းကုန်ကျစရိတ်:** {ad_data['estimated_cost']:,} ကျပ်\n\n"
                "Admin မှခွင့်ပြုသည်အထိ စောင့်ဆိုင်းပေးပါ\n"
                "⏰ 24 နာရီအတွင်းပြန်လည်ဆက်သွယ်ပေးပါမည်",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            update.message.reply_text(f"❌ ကြော်ငြာအပ်နှံရာတွင်အမှားဖြစ်နေသည်: {str(e)}")
    
    def notify_admins_new_ad(self, ad_id, ad_data):
        """Notify admins about new ad submission"""
        user = self.db.get_user_by_id(ad_data['created_by'])
        user_info = f"{user[6]} (@{user[1]})" if user else "User"
        
        message = (
            f"🆕 **ကြော်ငြာအသစ်တင်သွင်းခြင်း**\n\n"
            f"📋 **ကြော်ငြာအမှတ်:** #{ad_id}\n"
            f"🏢 **ကြော်ငြာပေးသူ:** {ad_data['advertiser_name']}\n"
            f"📝 **ကြော်ငြာခေါင်းစဉ်:** {ad_data['ad_title']}\n"
            f"💰 **တောင်းခံငွေ:** {ad_data['estimated_cost']:,} ကျပ်\n"
            f"👤 **တင်သွင်းသူ:** {user_info}\n\n"
            f"🔍 **ကြည့်ရန်:** /viewad_{ad_id}\n"
            f"✅ **ခွင့်ပြုရန်:** /approvead_{ad_id}\n"
            f"❌ **ပယ်ဖျက်ရန်:** /rejectad_{ad_id}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                self.bot.send_message(admin_id, message, parse_mode='Markdown')
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")

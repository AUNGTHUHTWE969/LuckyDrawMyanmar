import random
import schedule
import time
import threading
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
from database_manager import DatabaseManager
import config

class LotterySystem:
    def __init__(self, db_manager, bot):
        self.db = db_manager
        self.bot = bot
        self.setup_daily_draw()
    
    def setup_daily_draw(self):
        """နေ့စဉ်ကံစမ်းမဲအစီအစဉ် စီစဉ်ခြင်း"""
        schedule.every().day.at(config.DAILY_DRAW_TIME).do(self.run_daily_draw)
        
        # နောက်ခံတွင် scheduler စတင်ရန်
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)
        
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    
    def run_daily_draw(self):
        """နေ့စဉ်ကံစမ်းမဲ လုပ်ဆောင်ခြင်း"""
        try:
            # ယနေ့အတွက် ကံစမ်းမဲဝယ်ယူသူအားလုံးရယူရန်
            today = datetime.now().strftime('%Y-%m-%d')
            ticket_buyers = self.db.get_today_ticket_buyers(today)
            
            if not ticket_buyers:
                self.notify_admins("❌ ယနေ့ ကံစမ်းမဲဝယ်ယူသူ မရှိပါ")
                return
            
            # ဆုကြေးအောင်းငွေတွက်ချက်ပြီး ဆုရှင်များရွေးချယ်ရန်
            total_sales = self.db.get_daily_ticket_sales(today)
            admin_commission = total_sales * 0.20
            donation_amount = admin_commission * 0.05
            prize_pool = total_sales - admin_commission
            
            # ဆုရှင်များရွေးချယ်ရန် (ဝယ်ယူသူ၏ 10%, အနည်းဆုံး 1 ဦး၊ အများဆုံး 10 ဦး)
            winner_count = max(1, min(10, len(ticket_buyers) // 10))
            winners = random.sample(ticket_buyers, winner_count)
            
            # ဆုကြေးခွဲဝေရန်
            prize_per_winner = prize_pool / winner_count
            
            for winner in winners:
                self.db.update_balance(winner[0], prize_per_winner)
                self.db.record_winner(winner[0], prize_per_winner, today, f"TICKET_{winner[0]}")
            
            # ဆုရှင်များကြေညာရန်
            self.announce_winners(winners, prize_per_winner, today)
            
            # စီမံခန့်ခွဲသူများအား အကြောင်းကြားရန်
            self.notify_admins(
                f"🎉 နေ့စဉ်ကံစမ်းမဲ ပြီးဆုံးပါပြီ!\n"
                f"🎯 ကံစမ်းမဲပေါက်သူ: {winner_count} ဦး\n"
                f"💰 စုစုပေါင်းဆုကြေးငွေ: {prize_pool:,.0f} ကျပ်"
            )
            
        except Exception as e:
            self.notify_admins(f"❌ ကံစမ်းမဲလုပ်ဆောင်ရာတွင် အမှားတစ်ခုဖြစ်နေသည်: {str(e)}")
    
    def announce_winners(self, winners, prize_amount, date):
        """Channel သို့ ဆုရှင်များကြေညာခြင်း"""
        announcement = (
            f"🎉 **LUCKY DRAW MYANMAR - နေ့စဉ်ဆုကြေးရလာဒ်** 🎉\n\n"
            f"🏆 **တရားဝင်ကြေညာချက်**\n"
            f"📅 ရက်စွဲ: {date}\n"
            f"⏰ အချိန်: {config.DAILY_DRAW_TIME}\n"
            f"🎯 စုစုပေါင်းကံစမ်းမဲပေါက်သူ: {len(winners)} ဦး\n"
            f"💰 ဆုကြေးပမာဏ: {prize_amount:,.0f} ကျပ်\n\n"
            f"🎊 **ဆုရရှိသူများ:**\n"
        )
        
        for i, winner in enumerate(winners, 1):
            username = f"@{winner[1]}" if winner[1] else winner[2]
            announcement += f"{i}. {username}\n"
        
        announcement += (
            f"\n💝 **လှူဒါန်းငွေ:** {(prize_amount * len(winners) * 0.05):,.0f} ကျပ်\n"
            f"🎗️ **ကျေးဇူးတင်ရှိပါသည်!**\n\n"
            f"#DailyLuckyDraw #LuckyDrawMyanmar #Winners"
        )
        
        try:
            self.bot.send_message(
                chat_id=config.ANNOUNCEMENT_CHANNEL,
                text=announcement,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"ဆုရှင်များကြေညာရာတွင် မအောင်မြင်ပါ: {e}")
    
    def notify_admins(self, message):
        """စီမံခန့်ခွဲသူများအား အကြောင်းကြားခြင်း"""
        for admin_id in config.ADMIN_IDS:
            try:
                self.bot.send_message(admin_id, message)
            except Exception as e:
                print(f"စီမံခန့်ခွဲသူ {admin_id} အား အကြောင်းကြားရာတွင် မအောင်မြင်ပါ: {e}")

import os

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Admin Configuration
ADMIN_IDS = [123456789, 987654321]

# Channel & Group Configuration
ANNOUNCEMENT_CHANNEL = "@luckydrawmyanmarofficial"

# Payment Configuration - Same name and phone for both methods
PAYMENT_METHODS = {
    'KPay': {
        'name': 'AUNG THU HTWE',
        'phone': '09789999368'
    },
    'WavePay': {
        'name': 'AUNG THU HTWE', 
        'phone': '09789999368'
    }
}

# Lottery Configuration
DAILY_DRAW_TIME = "21:00"
TICKET_PRICE = 100

# Security Configuration
PASSWORD_MIN_LENGTH = 6
MAX_LOGIN_ATTEMPTS = 5

# Database Configuration
DATABASE_NAME = "luckydraw_myanmar.db"

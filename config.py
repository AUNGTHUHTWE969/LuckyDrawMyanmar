import os

# Bot Configuration - Render environment variable ကနေယူမယ်
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Admin Configuration - comma separated IDs
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '123456789,987654321').split(',')]

# Channel & Group Configuration
ANNOUNCEMENT_CHANNEL = os.getenv('ANNOUNCEMENT_CHANNEL', '@luckydrawmyanmarofficial')

# Payment Configuration
PAYMENT_METHODS = {
    'KPay': {
        'name': os.getenv('KPAY_NAME', 'AUNG THU HTWE'),
        'phone': os.getenv('KPAY_PHONE', '09789999368')
    },
    'WavePay': {
        'name': os.getenv('WAVEPAY_NAME', 'AUNG THU HTWE'), 
        'phone': os.getenv('WAVEPAY_PHONE', '09789999368')
    }
}

# Lottery Configuration
DAILY_DRAW_TIME = os.getenv('DAILY_DRAW_TIME', '21:00')
TICKET_PRICE = int(os.getenv('TICKET_PRICE', '100'))

# Security Configuration
PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '6'))
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))

# Email Configuration (Optional)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'your_email@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your_email_password')

# Database Configuration
DATABASE_NAME = os.getenv('DATABASE_NAME', 'luckydraw_myanmar.db')

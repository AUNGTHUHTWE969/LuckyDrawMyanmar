# Lucky Draw Myanmar Bot

A Telegram lottery bot deployed on Render with full payment integration.

## Features

- 🎫 Ticket purchasing with confirmation system
- 💰 KPay and WavePay integration  
- 👑 Admin panel for management
- ⏰ Configurable draw times
- 📊 Real-time transaction tracking
- 🏆 Automatic winner selection

## Deployment on Render

1. Fork this repository to your GitHub account
2. Go to [Render.com](https://render.com) and create account
3. Click "New +" and select "Web Service"
4. Connect your GitHub repository
5. Use these settings:
   - **Name**: `lucky-draw-bot`
   - **Environment**: `Python`
   - **Region**: `Singapore` (or your preferred region)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

6. Add environment variables:
   - `BOT_TOKEN`: Your Telegram bot token from BotFather

7. Click "Create Web Service"

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export BOT_TOKEN=your_bot_token_here

# Run locally
python bot.py

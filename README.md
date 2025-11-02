# Telegram Lottery Bot

A feature-rich Telegram lottery bot built with python-telegram-bot, deployed on Render.

## Features

- User registration and profile management
- Lottery ticket purchasing
- Deposit and withdrawal system
- Admin panel
- Referral system
- Multi-language support (Burmese)

## Deployment on Render

### Method 1: Direct Deploy from GitHub

1. Fork this repository to your GitHub account
2. Go to [Render.com](https://render.com)
3. Click "New +" and select "Web Service"
4. Connect your GitHub account and select this repository
5. Use the following settings:
   - **Name**: `telegram-lottery-bot`
   - **Environment**: `Python`
   - **Region**: Choose your preferred region
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
6. Add environment variable:
   - **Key**: `BOT_TOKEN`
   - **Value**: Your bot token from BotFather
7. Click "Create Web Service"

### Method 2: Deploy using Render.yaml

1. Fork this repository
2. Go to Render Dashboard
3. Click "New +" and select "Blueprints"
4. Connect your GitHub and select this repository
5. Render will automatically detect `render.yaml` and deploy

## Environment Variables

- `BOT_TOKEN`: Your Telegram bot token from BotFather
- `PORT`: Web server port (automatically set by Render)
- `ENVIRONMENT`: Set to 'production' or 'development'

## Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/telegram-lottery-bot.git
cd telegram-lottery-bot

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export BOT_TOKEN="your_bot_token_here"

# Run locally
python app.py

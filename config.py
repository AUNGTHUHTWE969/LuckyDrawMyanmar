import os

# Bot Configuration
class Config:
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '8444084929:AAEIkrCAeuNjSHVUCYE9AEpg6IFqE52rNxc')
    
    # Web server configuration
    PORT = int(os.environ.get('PORT', 8080))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # Admin IDs
    ADMIN_IDS = [8070878424]
    
    # Database configuration (for future use with PostgreSQL)
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Development configuration
class DevelopmentConfig(Config):
    LOG_LEVEL = 'DEBUG'

# Production configuration  
class ProductionConfig(Config):
    LOG_LEVEL = 'INFO'

# Choose configuration based on environment
if os.environ.get('ENVIRONMENT') == 'development':
    config = DevelopmentConfig()
else:
    config = ProductionConfig()

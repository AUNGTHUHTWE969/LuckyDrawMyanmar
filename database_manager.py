import sqlite3
import logging
import hashlib
import secrets
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_name="luckydraw_myanmar.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables including user authentication"""
        cursor = self.conn.cursor()
        
        # Users table with authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                phone_number TEXT UNIQUE,
                email TEXT,
                password_hash TEXT,
                register_name TEXT,
                balance REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                login_attempts INTEGER DEFAULT 0,
                last_login DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Phone reset tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token TEXT UNIQUE,
                phone_number TEXT,
                expires_at DATETIME,
                used BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                status TEXT,
                payment_method TEXT,
                phone_number TEXT,
                screenshot_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                processed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Lottery tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ticket_number TEXT UNIQUE,
                ticket_price REAL,
                purchase_date DATE,
                draw_date DATE,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Daily winners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                prize_amount REAL,
                draw_date DATE,
                announced BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Advertisements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS advertisements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                advertiser_name TEXT,
                ad_title TEXT,
                ad_content TEXT,
                ad_image TEXT,
                ad_link TEXT,
                ad_type TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 1,
                start_date DATE,
                end_date DATE,
                total_cost REAL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                created_by INTEGER,
                approved_by INTEGER,
                approved_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
        logger.info("All database tables created successfully")
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, password_hash):
        """Verify password against hash"""
        return self.hash_password(password) == password_hash
    
    def create_user(self, user_id, username, first_name, phone_number, password, register_name, email=None):
        """Create new user with authentication"""
        cursor = self.conn.cursor()
        
        password_hash = self.hash_password(password)
        
        try:
            cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, phone_number, email, password_hash, register_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, phone_number, email, password_hash, register_name))
            
            self.conn.commit()
            return True, "User created successfully"
            
        except sqlite3.IntegrityError as e:
            if "phone_number" in str(e):
                return False, "Phone number already registered"
            elif "email" in str(e):
                return False, "Email already registered"
            else:
                return False, "User already exists"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def authenticate_user(self, phone_number, password):
        """Authenticate user with phone number and password"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT user_id, password_hash, login_attempts, status 
            FROM users 
            WHERE phone_number = ?
        ''', (phone_number,))
        
        user = cursor.fetchone()
        
        if not user:
            return False, "User not found"
        
        user_id, password_hash, login_attempts, status = user
        
        if status != 'active':
            return False, "Account is suspended"
        
        if login_attempts >= 5:
            return False, "Too many failed login attempts. Please reset your password."
        
        if self.verify_password(password, password_hash):
            # Reset login attempts on successful login
            cursor.execute('''
                UPDATE users 
                SET login_attempts = 0, last_login = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            return True, user_id
        else:
            # Increment login attempts
            cursor.execute('''
                UPDATE users 
                SET login_attempts = login_attempts + 1
                WHERE user_id = ?
            ''', (user_id,))
            self.conn.commit()
            return False, "Invalid password"
    
    def get_user_by_phone(self, phone_number):
        """Get user by phone number"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone_number = ?', (phone_number,))
        return cursor.fetchone()
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def add_user(self, user_id, username, first_name):
        """Add or update user (for start command)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name) 
            VALUES (?, ?, ?)
        ''', (user_id, username, first_name))
        self.conn.commit()
    
    def create_phone_reset_token(self, phone_number):
        """Create password reset token using phone number"""
        cursor = self.conn.cursor()
        
        # Get user by phone number
        cursor.execute('SELECT user_id FROM users WHERE phone_number = ?', (phone_number,))
        user = cursor.fetchone()
        
        if not user:
            return None
        
        user_id = user[0]
        token = secrets.token_urlsafe(6).upper()  # 6-character code
        expires_at = datetime.now() + timedelta(minutes=10)  # 10 minutes expiry
        
        # Invalidate any existing tokens
        cursor.execute('''
            UPDATE phone_reset_tokens 
            SET used = TRUE 
            WHERE user_id = ? AND used = FALSE
        ''', (user_id,))
        
        # Create new token
        cursor.execute('''
            INSERT INTO phone_reset_tokens (user_id, token, phone_number, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, token, phone_number, expires_at))
        
        self.conn.commit()
        return token
    
    def verify_phone_reset_token(self, phone_number, token):
        """Verify phone reset token"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT user_id 
            FROM phone_reset_tokens 
            WHERE phone_number = ? AND token = ? AND used = FALSE AND expires_at > CURRENT_TIMESTAMP
        ''', (phone_number, token))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def use_phone_reset_token(self, phone_number, token):
        """Mark phone reset token as used"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE phone_reset_tokens 
            SET used = TRUE 
            WHERE phone_number = ? AND token = ?
        ''', (phone_number, token))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def change_password(self, user_id, new_password):
        """Change user password"""
        cursor = self.conn.cursor()
        
        password_hash = self.hash_password(new_password)
        
        cursor.execute('''
            UPDATE users 
            SET password_hash = ?, login_attempts = 0, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (password_hash, user_id))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_user_balance(self, user_id):
        """Get user balance"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def update_balance(self, user_id, amount):
        """Update user balance"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def create_transaction(self, user_id, trans_type, amount, payment_method=None, phone_number=None, screenshot_id=None):
        """Create transaction record"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, status, payment_method, phone_number, screenshot_id)
            VALUES (?, ?, ?, 'pending', ?, ?, ?)
        ''', (user_id, trans_type, amount, payment_method, phone_number, screenshot_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_transactions(self, trans_type):
        """Get pending transactions"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.*, u.username, u.first_name, u.register_name, u.phone_number as user_phone
            FROM transactions t 
            JOIN users u ON t.user_id = u.user_id 
            WHERE t.type = ? AND t.status = 'pending'
        ''', (trans_type,))
        return cursor.fetchall()
    
    def update_transaction_status(self, trans_id, status, processed_by=None):
        """Update transaction status"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE transactions 
            SET status = ?, processed_at = CURRENT_TIMESTAMP, processed_by = ?
            WHERE id = ?
        ''', (status, processed_by, trans_id))
        self.conn.commit()
    
    def buy_ticket(self, user_id, ticket_price, draw_date):
        """Buy lottery ticket"""
        cursor = self.conn.cursor()
        
        # Check balance
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if not user or user[0] < ticket_price:
            return False, "Insufficient balance"
        
        # Generate ticket number
        ticket_number = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
        
        # Deduct balance and create ticket
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (ticket_price, user_id))
        cursor.execute('''
            INSERT INTO lottery_tickets (user_id, ticket_number, ticket_price, purchase_date, draw_date)
            VALUES (?, ?, ?, DATE('now'), ?)
        ''', (user_id, ticket_number, ticket_price, draw_date))
        
        # Record transaction
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, status)
            VALUES (?, 'ticket_purchase', ?, 'completed')
        ''', (user_id, ticket_price))
        
        self.conn.commit()
        return True, ticket_number
    
    def get_today_ticket_buyers(self, date):
        """Get today's ticket buyers"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name 
            FROM lottery_tickets lt 
            JOIN users u ON lt.user_id = u.user_id 
            WHERE lt.draw_date = ? AND lt.status = 'active'
        ''', (date,))
        return cursor.fetchall()
    
    def get_daily_ticket_sales(self, date):
        """Get daily ticket sales total"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT SUM(ticket_price) FROM lottery_tickets WHERE draw_date = ?', (date,))
        result = cursor.fetchone()
        return result[0] if result[0] else 0
    
    def record_winner(self, user_id, prize_amount, date, ticket_number):
        """Record winner in database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO daily_winners (user_id, prize_amount, draw_date, ticket_number)
            VALUES (?, ?, ?, ?)
        ''', (user_id, prize_amount, date, ticket_number))
        self.conn.commit()
    
    def get_user_tickets(self, user_id):
        """Get user's tickets"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM lottery_tickets 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_all_withdrawals(self, status=None, limit=50):
        """Get all withdrawal records"""
        cursor = self.conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT t.*, u.username, u.first_name, u.register_name, u.phone_number as user_phone
                FROM transactions t 
                JOIN users u ON t.user_id = u.user_id 
                WHERE t.type = 'withdraw' AND t.status = ?
                ORDER BY t.created_at DESC
                LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT t.*, u.username, u.first_name, u.register_name, u.phone_number as user_phone
                FROM transactions t 
                JOIN users u ON t.user_id = u.user_id 
                WHERE t.type = 'withdraw'
                ORDER BY t.created_at DESC
                LIMIT ?
            ''', (limit,))
        
        return cursor.fetchall()
    
    def get_user_transactions(self, user_id, limit=20):
        """Get user's transaction history"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()

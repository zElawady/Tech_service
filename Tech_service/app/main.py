import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import re
import time
import uuid
import random
import logging
import altair as alt
from datetime import datetime, timedelta
from functools import wraps
from textwrap import dedent

# ==================== LOGGING SETUP ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="Service Connect Platform",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CHATBOT CLASS ====================
class Chatbot:
    def __init__(self, services):
        self.services = services or []
        self.context = {}

    def update_context(self, user_role, current_page):
        self.context['role'] = user_role
        self.context['page'] = current_page

    def get_response(self, user_input):
        user_input = user_input.lower().strip()
        role = self.context.get('role', 'Guest')
        page = self.context.get('page', 'Unknown')

        # Greetings
        if any(word in user_input for word in ['hello', 'hi', 'hey', 'start', 'greetings', 'welcome']):
            greetings = [
                f"Hello! 👋 I'm the Service Connect Assistant. You are currently on the **{page}** page. How can I help?",
                f"Hi there! Need help finding a service? I see you're browsing as **{role}**.",
                "Welcome back! I'm here to assist with booking, services, or account questions."
            ]
            return random.choice(greetings)

        # Services & Pricing
        if any(word in user_input for word in ['service', 'price', 'cost', 'how much', 'list', 'offer', 'cleaning', 'plumbing', 'tech']):
            if self.services:
                services_list = "\n".join([f"📍 **{s['name']}** - ${s['price']}" for s in self.services[:3]])
                responses = [
                     f"📋 **Here are some popular services:**\n{services_list}\n\nCheck the 'Services' page for more!",
                     f"We offer great services like **{self.services[0]['name']}** and **{self.services[1]['name']}**. Visit 'Services' to see them all.",
                     "💰 Our prices are competitive! For example, **" + self.services[0]['name'] + "** starts at $" + str(self.services[0]['price']) + "."
                ]
                return random.choice(responses)
            else:
                return "We have many services available. Please check the Services page!"

        # Booking / How to Order
        if any(word in user_input for word in ['book', 'order', 'reserve', 'buy', 'schedule', 'how to']):
            if role == 'user':
                return random.choice([
                    "📝 **Booking is easy:**\n1. Go to 'Services'\n2. Pick a service\n3. Fill the form!",
                    "To book, just navigate to the **Services** page and click 'Select' on the service you need.",
                    "Ready to order? Head over to the **Services** tab to get started."
                ])
            elif role == 'technical':
                return "⚠️ Technicians cannot book services. Please check your **Pending Orders** for assigned work."
            else:
                return "🔐 You need to **Login** or **Register** as a User to book a service."

        # Technical / Orders
        if any(word in user_input for word in ['pending', 'job', 'work', 'task', 'status', 'check']):
            if role == 'technical':
                return "🛠️ Check **Pending Orders** to see your assigned tasks. Don't forget to mark them as done!"
            elif role == 'user':
                return "📦 You can track your service status in the **My Orders** page."
            else:
                return "🔐 Please login to view order status."

        # Chat with technician
        if any(word in user_input for word in ['chat', 'message', 'talk', 'contact', 'technician', 'provider']):
             if role == 'user':
                return "💬 Go to **My Orders**, select your order, and click 'Contact Technician' to chat."
             elif role == 'technical':
                return "💬 Go to **Pending Orders**, select the job, and click 'Contact Customer' to chat."
             else:
                return "🔐 Please login to communicate with service providers."

        # Account
        if any(word in user_input for word in ['login', 'sign in', 'register', 'sign up', 'account', 'profile']):
            return "👤 You can **Login** or **Register** from the Home page options."

        # About
        if any(word in user_input for word in ['about', 'who', 'company', 'mission']):
            return "🏢 We are **Service Connect**, your trusted platform for local home and tech services."

        # Contact
        if any(word in user_input for word in ['help', 'support', 'phone', 'email', 'call']):
            return "📞 Reach us at support@serviceconnect.com or call +1-234-567-8900."

        # Default Fallback
        fallbacks = [
            f"❓ I'm not sure I understand. I can help with **Services**, **Booking**, and **Account** info.",
            f"Could you rephrase that? I'm currently tuned to help you with Service Connect tasks on the **{page}** page.",
            "I'm a simple bot 🤖. Ask me about 'prices', 'how to book', or 'my orders'!",
            f"I see you are on the **{page}** page. Do you need help with that?"
        ]
        return random.choice(fallbacks)

# ==================== DATABASE MANAGER ====================
class DatabaseManager:
    def __init__(self, db_path="service_connect.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
        self._seed_initial_data()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info("Database connection established")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            st.error("Failed to connect to database")

    def _create_tables(self):
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'technical', 'admin')),
                status TEXT DEFAULT 'Active',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                phone TEXT,
                bio TEXT
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                icon TEXT,
                rating REAL DEFAULT 4.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                payment_method TEXT,
                notes TEXT,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            # New table for chat messages
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                sender_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
            ''')
            # New table for order technicians assignment
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_technicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                technician_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (technician_id) REFERENCES users(id)
            )
            ''')
            self.conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")

    def _seed_initial_data(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            if cursor.fetchone()[0] == 0:
                admin_hash = self._hash_password("admin123")
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, bio)
                VALUES (?, ?, ?, ?, ?)
                ''', ('admin@serviceconnect.com', admin_hash, 'Admin', 'admin', 'System Administrator'))
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, bio)
                VALUES (?, ?, ?, ?, ?)
                ''', ('user@example.com', self._hash_password('user'), 'Demo User', 'user', 'Regular user account for testing'))
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, bio)
                VALUES (?, ?, ?, ?, ?)
                ''', ('tech@example.com', self._hash_password('tech'), 'Demo Tech', 'technical', 'Professional service provider'))
                # Add more technicians
                technicians = [
                    ('ahmed@example.com', 'tech123', 'Ahmed Hassan', 'Professional plumber with 10 years experience', '+201234567890'),
                    ('mohamed@example.com', 'tech123', 'Mohamed Ali', 'Electrical engineer specialist', '+201234567891'),
                    ('sara@example.com', 'tech123', 'Sara Mahmoud', 'Cleaning service expert', '+201234567892'),
                ]
                for email, password, name, bio, phone in technicians:
                    cursor.execute('''
                    INSERT INTO users (email, password_hash, name, role, bio, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (email, self._hash_password(password), name, 'technical', bio, phone))
            cursor.execute("SELECT COUNT(*) FROM services")
            if cursor.fetchone()[0] == 0:
                services = [
                    ('House Cleaning', 'Home', 50, 'Deep cleaning service for your entire home', '🧹', 4.7),
                    ('Plumbing Repair', 'Maintenance', 80, 'Fix leaks and drainage issues', '🔧', 4.8),
                    ('Tech Support', 'Tech', 60, 'Computer troubleshooting and setup', '💻', 4.9),
                    ('Mobile Mechanic', 'Auto', 90, 'Car repair at your location', '🚗', 4.6),
                    ('Locksmith', 'Maintenance', 60, 'Lock replacement and key making', '🔑', 4.8),
                    ('Lighting Install', 'Maintenance', 80, 'Professional light fixture installation', '💡', 4.7),
                    ('Air Conditioning', 'Home', 120, 'AC installation and repair', '❄️', 4.9),
                    ('Electrical Wiring', 'Maintenance', 100, 'Safe electrical wiring solutions', '⚡', 4.8),
                    ('Carpet Cleaning', 'Home', 70, 'Deep carpet cleaning and stain removal', '🧽', 4.6),
                    ('Painting Service', 'Home', 200, 'Interior and exterior painting', '🎨', 4.7),
                ]
                cursor.executemany('''
                INSERT INTO services (name, category, price, description, icon, rating)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', services)
            self.conn.commit()
            logger.info("Initial data seeded")
        except sqlite3.Error as e:
            logger.error(f"Error seeding data: {e}")

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, email, password):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id, email, name, role, password_hash
            FROM users WHERE email = ? AND is_active = 1
            ''', (email,))
            user = cursor.fetchone()
            if not user:
                return False, "Invalid credentials"
            user_id, db_email, name, role, db_hash = user
            if self._hash_password(password) == db_hash:
                cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
                self.conn.commit()
                return True, {"id": user_id, "email": db_email, "name": name, "role": role}
            return False, "Invalid credentials"
        except sqlite3.Error as e:
            logger.error(f"Auth error: {e}")
            return False, "System error"

    def register_user(self, email, password, name, role, phone=None, bio=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
            if cursor.fetchone()[0] > 0:
                return False, "Email already exists"
            password_hash = self._hash_password(password)
            cursor.execute('''
            INSERT INTO users (email, password_hash, name, role, phone, bio)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, password_hash, name, role, phone, bio))
            self.conn.commit()
            return True, "Registration successful"
        except sqlite3.Error as e:
            logger.error(f"Registration error: {e}")
            return False, "System error"

    def get_services(self, category=None):
        try:
            cursor = self.conn.cursor()
            if category and category != "All":
                cursor.execute('SELECT * FROM services WHERE category = ?', (category,))
            else:
                cursor.execute('SELECT * FROM services')
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting services: {e}")
            return []

    def create_order(self, user_id, service_id, booking_date, payment_method, notes, price):
        try:
            order_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO orders (id, user_id, service_id, booking_date, payment_method, notes, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, user_id, service_id, booking_date, payment_method, notes, price))
            self.conn.commit()
            return True, order_id
        except sqlite3.Error as e:
            logger.error(f"Error creating order: {e}")
            return False, None

    def get_user_orders(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, s.icon
            FROM orders o
            JOIN services s ON o.service_id = s.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting orders: {e}")
            return []

    def get_pending_orders(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, u.name as user_name,
                   u.email as user_email, u.phone as user_phone,
                   (SELECT COUNT(*) FROM chat_messages WHERE order_id = o.id AND is_read = 0 AND sender_id != ?) as unread_count
            FROM orders o
            JOIN services s ON o.service_id = s.id
            JOIN users u ON o.user_id = u.id
            WHERE o.status = 'Pending'
            ORDER BY o.created_at DESC
            ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending orders: {e}")
            return []

    def update_order_status(self, order_id, status):
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating order: {e}")
            return False

    def get_dashboard_stats(self):
        try:
            cursor = self.conn.cursor()
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
            stats['total_users'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'technical'")
            stats['total_techs'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            stats['total_orders'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
            stats['pending_orders'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Done'")
            stats['completed_orders'] = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(price) FROM orders WHERE status = 'Done'")
            stats['revenue'] = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM services")
            stats['total_services'] = cursor.fetchone()[0]
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def get_all_orders(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, u.name as user_name
            FROM orders o
            JOIN services s ON o.service_id = s.id
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            ''')
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            return []

    def get_user_profile(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT name, email, role, join_date, last_login, phone, bio
            FROM users WHERE id = ?
            ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None

    def update_user_profile(self, user_id, name, phone, bio):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE users SET name = ?, phone = ?, bio = ? WHERE id = ?
            ''', (name, phone, bio, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False

    def save_contact_message(self, name, email, subject, message):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO contact_messages (name, email, subject, message)
            VALUES (?, ?, ?, ?)
            ''', (name, email, subject, message))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving contact: {e}")
            return False

    # ==================== CHAT SYSTEM METHODS ====================
    def save_chat_message(self, order_id, sender_id, message):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO chat_messages (order_id, sender_id, message)
            VALUES (?, ?, ?)
            ''', (order_id, sender_id, message))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving chat message: {e}")
            return False

    def get_chat_messages(self, order_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT cm.*, u.name as sender_name, u.role as sender_role
            FROM chat_messages cm
            JOIN users u ON cm.sender_id = u.id
            WHERE cm.order_id = ?
            ORDER BY cm.created_at ASC
            ''', (order_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting chat messages: {e}")
            return []

    def mark_messages_as_read(self, order_id, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE chat_messages
            SET is_read = 1
            WHERE order_id = ? AND sender_id != ? AND is_read = 0
            ''', (order_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking messages as read: {e}")
            return False

    def get_unread_message_count(self, user_id, role):
        try:
            cursor = self.conn.cursor()
            if role == 'user':
                cursor.execute('''
                SELECT COUNT(*)
                FROM chat_messages cm
                JOIN orders o ON cm.order_id = o.id
                JOIN users u ON cm.sender_id = u.id
                WHERE o.user_id = ? AND cm.is_read = 0 AND u.role = 'technical'
                ''', (user_id,))
            else:
                cursor.execute('''
                SELECT COUNT(*)
                FROM chat_messages cm
                JOIN users u ON cm.sender_id = u.id
                JOIN orders o ON cm.order_id = o.id
                WHERE cm.is_read = 0 AND u.role = 'user' AND o.status = 'Pending'
                ''')
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    def get_user_chats(self, user_id, role):
        try:
            cursor = self.conn.cursor()
            if role == 'user':
                cursor.execute('''
                SELECT DISTINCT o.id as order_id, s.name as service_name,
                       o.status, o.created_at, o.booking_date,
                       (SELECT COUNT(*) FROM chat_messages
                        WHERE order_id = o.id AND is_read = 0 AND sender_id != ?) as unread_count
                FROM orders o
                JOIN services s ON o.service_id = s.id
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
                ''', (user_id, user_id))
            else:  # technician
                cursor.execute('''
                SELECT DISTINCT o.id as order_id, s.name as service_name,
                       u.name as user_name, o.status, o.created_at, o.booking_date,
                       (SELECT COUNT(*) FROM chat_messages
                        WHERE order_id = o.id AND is_read = 0 AND sender_id != ?) as unread_count
                FROM orders o
                JOIN services s ON o.service_id = s.id
                JOIN users u ON o.user_id = u.id
                WHERE o.status = 'Pending'
                ORDER BY o.created_at DESC
                ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting user chats: {e}")
            return []

    def get_order_details(self, order_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, s.icon,
                   u.name as user_name, u.email as user_email, u.phone as user_phone,
                   t.name as technician_name, t.email as technician_email, t.phone as technician_phone
            FROM orders o
            JOIN services s ON o.service_id = s.id
            JOIN users u ON o.user_id = u.id
            LEFT JOIN order_technicians ot ON o.id = ot.order_id
            LEFT JOIN users t ON ot.technician_id = t.id
            WHERE o.id = ?
            ''', (order_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting order details: {e}")
            return None

    def assign_technician_to_order(self, order_id, technician_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM order_technicians WHERE order_id = ?', (order_id,))
            cursor.execute('''
            INSERT INTO order_technicians (order_id, technician_id)
            VALUES (?, ?)
            ''', (order_id, technician_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error assigning technician: {e}")
            return False

    def get_available_technicians(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id, name, email, phone, bio
            FROM users
            WHERE role = 'technical' AND is_active = 1
            ORDER BY name
            ''')
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting technicians: {e}")
            return []

    def close(self):
        if self.conn:
            self.conn.close()

# ==================== UI MANAGER ====================
class UIManager:
    @staticmethod
    def md(html):
        st.markdown(dedent(html).strip(), unsafe_allow_html=True)

    @staticmethod
    def show_notification(message, type='success'):
        if type == 'success':
            st.success(message)
        elif type == 'error':
            st.error(message)
        elif type == 'warning':
            st.warning(message)
        else:
            st.info(message)

    @staticmethod
    def format_datetime(dt_string):
        if not dt_string:
            return "N/A"
        try:
            dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%I:%M %p')
        except:
            return dt_string[:10]

    @staticmethod
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_phone(phone):
        pattern = r'^\+?[1-9]\d{1,14}$'
        return re.match(pattern, phone) is not None if phone else True

    @staticmethod
    def inject_css():
        UIManager.md("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    background-color: #0b0f19;
    color: #ffffff !important;
}
.stApp {
    background: linear-gradient(135deg, #0b0f19 0%, #1a1f35 50%, #251e3e 100%);
    background-attachment: fixed;
}
.block-container {
    padding-top: 2rem;
    padding-right: 2rem;
    padding-left: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
/* Top Navigation Bar */
.nav-container {
    display: flex;
    justify-content: center;
    gap: 20px;
    padding: 15px 30px;
    background: rgba(20, 25, 45, 0.98);
    backdrop-filter: blur(15px);
    border-radius: 15px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.6);
    margin-bottom: 30px;
    position: sticky;
    top: 10px;
    z-index: 1000;
    border: 1px solid rgba(255, 255, 255, 0.2);
}
/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}
@keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}
.animate-enter {
    animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.animate-slide {
    animation: slideIn 0.5s ease-out forwards;
}
.pulse-animation {
    animation: pulse 2s infinite;
}
.bounce-animation {
    animation: bounce 0.5s infinite;
}
/* Chat System Styles */
.chat-container {
    background: rgba(20, 25, 45, 0.95);
    border-radius: 20px;
    padding: 25px;
    box-shadow: 0 15px 50px rgba(0,0,0,0.5);
    border: 1px solid rgba(108, 92, 231, 0.3);
    margin-bottom: 30px;
}
.chat-header {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    margin-bottom: 25px;
    position: relative;
    overflow: hidden;
}
.chat-header::before {
    content: '💬';
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 2rem;
    opacity: 0.3;
}
.chat-header h2 {
    color: white !important;
    margin: 0;
    font-size: 24px;
    font-weight: 700;
}
.chat-header p {
    color: rgba(255,255,255,0.9) !important;
    margin: 8px 0 0 0;
    font-size: 14px;
}
.chat-messages {

    max-height: 500px;
    overflow-y: auto;
    padding: 20px;
    background: rgba(26, 31, 53, 0.8);
    border-radius: 15px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.1);
    scroll-behavior: smooth;
}
.chat-message {
    margin-bottom: 20px;
    padding: 15px;
    border-radius: 15px;
    max-width: 80%;
    position: relative;
    word-wrap: break-word;
}
.chat-message.user {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    margin-left: auto;
    border-bottom-right-radius: 5px;
}
.chat-message.tech {
    background: rgba(255, 255, 255, 0.1);
    margin-right: auto;
    border-bottom-left-radius: 5px;
    border: 1px solid rgba(255,255,255,0.2);
}
.chat-message-content {
    color: white !important;
    font-size: 15px;
    line-height: 1.5;
}
.chat-message-time {
    font-size: 11px;
    color: rgba(255,255,255,0.6) !important;
    text-align: right;
    margin-top: 5px;
}
.chat-message-sender {
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 5px;
    color: rgba(255,255,255,0.9) !important;
}
/* Chat Input */
.chat-input-container {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}
.chat-input-container textarea {
    flex-grow: 1;
    background: rgba(26, 31, 53, 0.9);
    border: 1px solid rgba(108, 92, 231, 0.5);
    border-radius: 12px;
    padding: 15px;
    color: white !important;
    font-size: 15px;
    resize: none;
    height: 70px;
}
.chat-input-container textarea:focus {
    border-color: #6c5ce7;
    box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.2);
    outline: none;
}
/* Order Chat Badge */
.order-chat-badge {
    position: absolute;
    top: -8px;
    right: -8px;
    background: #e74c3c;
    color: white !important;
    font-size: 12px;
    font-weight: bold;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: bounce 1s infinite;
}
/* Chat Notification */
.chat-notification {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    color: white !important;
    padding: 15px 25px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    z-index: 9999;
    animation: slideIn 0.5s ease-out;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    transition: transform 0.3s ease;
}
.chat-notification:hover {
    transform: scale(1.05);
}
.chat-notification-close {
    background: none;
    border: none;
    color: white !important;
    font-size: 20px;
    cursor: pointer;
    padding: 0;
    margin-left: 10px;
}
/* Chat List */
.chat-list-container {
    background: rgba(20, 25, 45, 0.95);
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.1);
}
.chat-list-item {
    background: rgba(30, 35, 60, 0.8);
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid rgba(255,255,255,0.1);
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
}
.chat-list-item:hover {
    background: rgba(108, 92, 231, 0.2);
    border-color: #6c5ce7;
    transform: translateX(5px);
}
.chat-list-item.active {
    background: rgba(108, 92, 231, 0.3);
    border-color: #6c5ce7;
}
.chat-list-item-unread {
    position: absolute;
    top: 15px;
    right: 15px;
    background: #e74c3c;
    color: white !important;
    font-size: 11px;
    font-weight: bold;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.chat-list-info h4 {
    margin: 0 0 5px 0;
    color: #ffffff !important;
}
.chat-list-info p {
    margin: 0;
    color: rgba(255,255,255,0.7) !important;
    font-size: 13px;
}
.chat-list-time {
    font-size: 11px;
    color: rgba(255,255,255,0.5) !important;
    margin-top: 5px;
}
/* Hero Section */
.hero-section {
    text-align: center;
    padding: 80px 50px !important;
    background: rgba(30, 35, 60, 0.5);
    border-radius: 25px !important;
    box-shadow: 0 15px 50px rgba(0,0,0,0.7) !important;
    border: 1px solid #6c5ce7;
    margin-bottom: 50px;
    background-image: radial-gradient(circle at 10% 20%, rgba(108, 92, 231, 0.1) 0%, transparent 50%),
                      radial-gradient(circle at 90% 80%, rgba(142, 68, 173, 0.1) 0%, transparent 50%);
}
.hero-section h1 {
    color: #a29bfe !important;
    font-size: 3.5rem;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 5px 15px rgba(108, 92, 231, 0.3);
}
.hero-section p {
    color: #e0e0e0 !important;
    font-size: 1.2rem;
}
/* Service Cards */
.service-card {
    background: linear-gradient(135deg, #1e233c 0%, #252947 100%);
    border-radius: 18px;
    padding: 28px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    transition: all 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.15);
    height: 320px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.service-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #6c5ce7, #8e44ad);
}
.service-card:hover {
    transform: translateY(-10px) scale(1.02);
    box-shadow: 0 20px 50px rgba(108, 92, 231, 0.4);
    border-color: #6c5ce7;
}
.card-icon {
    font-size: 50px;
    margin-bottom: 10px;
    text-align: center;
    filter: drop-shadow(0 5px 10px rgba(108, 92, 231, 0.5));
}
.card-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #ffffff !important;
    margin-bottom: 5px;
}
.card-category {
    display: inline-block;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    color: #ffffff !important;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 10px;
    width: fit-content;
    box-shadow: 0 4px 10px rgba(108, 92, 231, 0.3);
}
.card-desc {
    color: #e0e0e0 !important;
    flex-grow: 1;
    margin-bottom: 15px;
    font-size: 14px;
    line-height: 1.5;
}
.card-price {
    font-size: 1.8rem;
    font-weight: 700;
    color: #a29bfe !important;
    margin-top: 10px;
    text-shadow: 0 3px 10px rgba(108, 92, 231, 0.5);
}
.card-rating {
    color: #f1c40f !important;
    font-size: 14px;
    margin-top: 5px;
}
/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    color: white !important;
    border: none;
    padding: 14px 28px;
    border-radius: 14px;
    font-weight: 700;
    transition: all 0.3s ease;
    width: 100%;
    box-shadow: 0 6px 20px rgba(108, 92, 231, 0.5);
    font-size: 17px;
    letter-spacing: 0.5px;
    position: relative;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.stButton > button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: 0.5s;
}
.stButton > button:hover {
    transform: scale(1.05);
    background: linear-gradient(135deg, #8e44ad 0%, #6c5ce7 100%) !important;
    color: white !important;
    box-shadow: 0 0 35px rgba(108, 92, 231, 0.9);
}
.stButton > button:hover::before {
    left: 100%;
}
/* Special Button Styles */
.btn-primary {
    background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%) !important;
}
.btn-secondary {
    background: linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%) !important;
}
/* Form Elements */
div[data-testid="stForm"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stDateInput"] label {
    color: #ffffff !important;
    font-weight: 600;
}
input[type="text"],
input[type="password"],
input[type="email"],
textarea {
    background-color: #1a1f35 !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px;
    padding: 12px 16px !important;
    font-size: 16px;
    transition: all 0.3s ease;
}
input[type="text"]:focus,
input[type="password"]:focus,
input[type="email"]:focus,
textarea:focus {
    border-color: #6c5ce7 !important;
    box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.3) !important;
    outline: none;
}
/* Select Box */
div[data-baseweb="select"] > div {
    background-color: #1a1f35 !important;
    color: #ffffff !important;
    border: 1px solid #6c5ce7 !important;
    border-radius: 12px;
    padding: 4px 12px !important;
}
div[data-baseweb="select"] span {
    color: #ffffff !important;
    font-family: inherit;
    font-size: inherit;
    color: #ffffff !important;
}
/* Text Colors */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 700 !important;
}
h1 {
    font-size: 2.8rem !important;
    margin-bottom: 1rem !important;
    background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
h2 {
    font-size: 2.2rem !important;
    margin-bottom: 1rem !important;
}
/* Chatbot Container */
.chatbot-container {
    background: rgba(30, 35, 60, 0.95);
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
}
.chatbot-header {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.chatbot-header::before {
    content: '🤖';
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 2rem;
    opacity: 0.3;
}
.chatbot-header h2 {
    color: white !important;
    margin: 0;
    font-size: 24px;
    font-weight: 700;
}
.chatbot-header p {
    color: rgba(255,255,255,0.9) !important;
    margin: 8px 0 0 0;
    font-size: 14px;
}
.chat-messages-area {
    min-height: 300px;
    max-height: 400px;
    overflow-y: auto;
    padding: 15px;
    background: linear-gradient(135deg, #1a1f35 0%, #252947 100%);
    border-radius: 10px;
    margin-bottom: 15px;
    border: 1px solid rgba(255,255,255,0.1);
    scroll-behavior: smooth;
}
.chat-messages-area * {
    color: #ffffff !important;
}
/* Custom scrollbar */
.chat-messages-area::-webkit-scrollbar {
    width: 6px;
}
.chat-messages-area::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
}
.chat-messages-area::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    border-radius: 3px;
}
/* Status Badges */
.status-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.status-pending {
    background: #f1c40f20;
    color: #f1c40f;
    border: 1px solid #f1c40f;
    box-shadow: 0 3px 10px rgba(241, 196, 15, 0.2);
}
.status-done {
    background: #2ecc7120;
    color: #2ecc71;
    border: 1px solid #2ecc71;
    box-shadow: 0 3px 10px rgba(46, 204, 113, 0.2);
}
.status-cancelled {
    background: #e74c3c20;
    color: #e74c3c;
    border: 1px solid #e74c3c;
    box-shadow: 0 3px 10px rgba(231, 76, 60, 0.2);
}
/* Stats Cards */
.stats-card {
    background: linear-gradient(135deg, #1e233c 0%, #252947 100%);
    border-radius: 15px;
    padding: 25px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
    transition: all 0.3s ease;
}
.stats-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 40px rgba(108, 92, 231, 0.3);
}
.stats-card h3 {
    font-size: 2rem !important;
    margin-bottom: 5px !important;
    color: #a29bfe !important;
}
.stats-card p {
    color: #e0e0e0 !important;
    font-size: 14px;
    margin: 0 !important;
}
/* Notification */
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 25px;
    border-radius: 10px;
    background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
    color: white !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    z-index: 10000;
    animation: slideIn 0.5s ease-out;
    display: flex;
    align-items: center;
    gap: 10px;
}
.notification.error {
    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
}
.notification.warning {
    background: linear-gradient(135deg, #f1c40f 0%, #f39c12 100%);
}
/* Loading Animation */
.loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100px;
}
.loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(108, 92, 231, 0.3);
    border-top: 4px solid #6c5ce7;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
/* Feature Cards */
.feature-card {
    background: rgba(30, 35, 60, 0.8);
    border-radius: 15px;
    padding: 30px;
    text-align: center;
    border: 1px solid rgba(255, 255,255, 0.1);
    transition: all 0.3s ease;
    height: 250px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.feature-card:hover {
    transform: translateY(-10px);
    border-color: #6c5ce7;
    box-shadow: 0 15px 40px rgba(108, 92, 231, 0.3);
}
.feature-icon {
    font-size: 3rem;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
/* Profile Card */
.profile-card {
    background: linear-gradient(135deg, #1e233c 0%, #252947 100%);
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 15px 50px rgba(0,0,0,0.5);
    border: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}
.profile-avatar {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3rem;
    margin: 0 auto 20px;
    box-shadow: 0 10px 30px rgba(108, 92, 231, 0.5);
}
</style>
""")

# ==================== AUTH MANAGER ====================
class AuthManager:
    @staticmethod
    def logout():
        st.session_state['current_user'] = None
        st.session_state['current_page'] = 'Home'
        st.session_state['current_chat_order'] = None
        st.rerun()

# ==================== NAVIGATION MANAGER ====================
class NavigationManager:
    @staticmethod
    def show_navigation(db):
        user = st.session_state['current_user']
        if not user:
            return
        menu_items = {
            'user': ["Home", "Services", "My Orders", "My Chats", "Profile", "About", "Contact Us", "Logout"],
            'technical': ["Home", "Pending Orders", "My Chats", "Profile", "About", "Contact Us", "Logout"],
            'admin': ["Home", "Dashboard", "All Orders", "Analytics", "Profile", "About", "Contact Us", "Logout"]
        }
        menu = menu_items.get(user['role'], [])
        unread_count = db.get_unread_message_count(user['id'], user['role'])
        
        html_nav = '<div class="nav-container">'
        cols = st.columns(len(menu))
        for i, item in enumerate(menu):
            button_text = item
            if item == "My Chats" and unread_count > 0:
                button_text = f"💬 My Chats ({unread_count})"
            with cols[i]:
                if st.button(button_text, key=f"nav_{item}", use_container_width=True):
                    if item == "Logout":
                        AuthManager.logout()
                    else:
                        st.session_state['current_page'] = item
                        st.session_state['selected_service'] = None
                        st.session_state['current_chat_order'] = None
                        st.rerun()
        html_nav += '</div>'
        UIManager.md(html_nav)

    @staticmethod
    def show_guest_navigation():
        html_guest_nav = '<div class="nav-container">'
        cols = st.columns(5)
        menu_items = ["Home", "Login", "Register", "About", "Contact Us"]
        for i, item in enumerate(menu_items):
            with cols[i]:
                if st.button(item, key=f"guest_nav_{item}", use_container_width=True):
                    st.session_state['current_page'] = item
                    st.rerun()
        html_guest_nav += '</div>'
        UIManager.md(html_guest_nav)

# ==================== PAGE LOGIC ====================
class HomePage:
    @staticmethod
    def show(db):
        if st.session_state['current_user']:
            role = st.session_state['current_user']['role']
            if role == 'user':
                st.session_state['current_page'] = 'Services'
            elif role == 'technical':
                st.session_state['current_page'] = 'Pending Orders'
            elif role == 'admin':
                st.session_state['current_page'] = 'Dashboard'
            st.rerun()
            return
        
        UIManager.md("""
        <div class="hero-section animate-enter">
            <h1>⚡ Service Connect Platform</h1>
            <p>Your reliable partner for booking and providing local services</p>
        </div>
        """)
        # Features Section
        UIManager.md("<h2 style='text-align: center; margin: 40px 0 20px;'>🌟 Why Choose Us?</h2>")
        features = st.columns(3)
        with features[0]:
            UIManager.md("""
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <h3>Fast Service</h3>
                <p>Quick response and efficient service delivery</p>
            </div>
            """)
        with features[1]:
            UIManager.md("""
            <div class="feature-card">
                <div class="feature-icon">🛡️</div>
                <h3>Verified Experts</h3>
                <p>All technicians are verified and experienced</p>
            </div>
            """)
        with features[2]:
            UIManager.md("""
            <div class="feature-card">
                <div class="feature-icon">💬</div>
                <h3>Direct Chat</h3>
                <p>Communicate directly with service providers</p>
            </div>
            """)
        # Quick Stats
        stats = db.get_dashboard_stats()
        UIManager.md("<h2 style='text-align: center; margin: 50px 0 20px;'>📊 Quick Stats</h2>")
        stats_cols = st.columns(4)
        with stats_cols[0]:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>{stats.get('total_services', 0)}+</h3>
                <p>Services</p>
            </div>
            """)
        with stats_cols[1]:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>{stats.get('total_orders', 0)}+</h3>
                <p>Orders</p>
            </div>
            """)
        with stats_cols[2]:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>{stats.get('total_techs', 0)}+</h3>
                <p>Experts</p>
            </div>
            """)
        with stats_cols[3]:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>${stats.get('revenue', 0):.0f}+</h3>
                <p>Saved</p>
            </div>
            """)
        # Action Buttons
        UIManager.md("<br>")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("🔐 LOGIN", key="home_login", use_container_width=True):
                st.session_state['current_page'] = "Login"
                st.rerun()
        with col3:
            if st.button("🚀 REGISTER", key="home_register", use_container_width=True):
                st.session_state['current_page'] = "Register"
                st.rerun()

class LoginPage:
    @staticmethod
    def show(db):
        if st.button("← Back to Home"):
            st.session_state['current_page'] = 'Home'
            st.rerun()
        UIManager.md("<h2 style='text-align: center;'>Welcome Back! 👋</h2>")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                success, result = db.authenticate_user(email, password)
                if success:
                    st.session_state['current_user'] = result
                    UIManager.show_notification(f"✅ Welcome {result['name']}!", 'success')
                    time.sleep(0.5)
                    # Redirect based on role
                    if result['role'] == 'user':
                        st.session_state['current_page'] = 'Services'
                    elif result['role'] == 'technical':
                        st.session_state['current_page'] = 'Pending Orders'
                    elif result['role'] == 'admin':
                        st.session_state['current_page'] = 'Dashboard'
                    st.rerun()
                else:
                    UIManager.show_notification(result, 'error')

class RegisterPage:
    @staticmethod
    def show(db):
        if st.button("← Back to Home"):
            st.session_state['current_page'] = 'Home'
            st.rerun()
        UIManager.md("<h2 style='text-align: center;'>Join Service Connect! 🚀</h2>")
        # Role selection with better UX
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Register as User", key="reg_user", use_container_width=True,
                        type="primary" if st.session_state.get('selected_role_reg', 'user') == 'user' else "secondary"):
                st.session_state['selected_role_reg'] = 'user'
                st.rerun()
        with col2:
            if st.button("🔧 Register as Technician", key="reg_tech", use_container_width=True,
                        type="primary" if st.session_state.get('selected_role_reg') == 'technical' else "secondary"):
                st.session_state['selected_role_reg'] = 'technical'
                st.rerun()
        role = st.session_state.get('selected_role_reg', 'user')
        st.info(f"📝 Registering as: **{role.capitalize()}** - {'Book services' if role == 'user' else 'Provide services'}")
        
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number (Optional)")
            password = st.text_input("Password", type="password", help="Minimum 6 characters")
            confirm = st.text_input("Confirm Password", type="password")
            bio = None
            if role == 'technical':
                bio = st.text_area("Professional Bio (Optional)", placeholder="Brief description of your skills and experience...")
            
            if st.form_submit_button("Create Account", use_container_width=True):
                if not name or not email or not password:
                    UIManager.show_notification("All fields are required", 'error')
                elif not UIManager.validate_email(email):
                    UIManager.show_notification("Invalid email format", 'error')
                elif password != confirm:
                    UIManager.show_notification("Passwords don't match", 'error')
                elif len(password) < 6:
                    UIManager.show_notification("Password must be at least 6 characters", 'error')
                elif phone and not UIManager.validate_phone(phone):
                    UIManager.show_notification("Invalid phone number format", 'error')
                else:
                    success, msg = db.register_user(email, password, name, role, phone, bio)
                    if success:
                        UIManager.show_notification("✅ Registration successful! Please login.", 'success')
                        time.sleep(1)
                        st.session_state['current_page'] = "Login"
                        st.rerun()
                    else:
                        UIManager.show_notification(msg, 'error')

class ServicesPage:
    @staticmethod
    def show_service_details(db):
        service = st.session_state['selected_service']
        if st.button("← Back to Services"):
            st.session_state['selected_service'] = None
            st.rerun()
        UIManager.md(f"""
        <div style="background: rgba(30, 35, 60, 0.95); padding: 40px; border-radius: 20px;
        border: 1px solid #6c5ce7; margin: 20px 0; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; font-size: 8rem; opacity: 0.1;">{service['icon']}</div>
        <div style="font-size: 4rem; text-align: center;">{service['icon']}</div>
        <h1 style="text-align: center; color: #a29bfe;">{service['name']}</h1>
        <div style="text-align: center; margin: 20px 0;">
            <span class="card-category">{service['category']}</span>
            <span style="margin-left: 10px; color: #f1c40f;">⭐ {service['rating']}</span>
        </div>
        <p style="text-align: center; font-size: 1.1rem; color: #e0e0e0; max-width: 800px; margin: 0 auto;">{service['description']}</p>
        <h2 style="text-align: center; margin-top: 30px; color: #a29bfe;">Price: ${service['price']}</h2>
        </div>
        """)
        st.subheader("📅 Complete Your Booking")
        with st.form("booking_form"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Service Date", min_value=datetime.today())
            with col2:
                payment = st.selectbox("Payment Method", ["Credit Card", "Cash", "Digital Wallet", "Bank Transfer"])
            notes = st.text_area("Special Instructions (Optional)", placeholder="Any specific requirements or details...")
            if st.form_submit_button("Confirm Booking", use_container_width=True):
                success, order_id = db.create_order(
                    st.session_state['current_user']['id'],
                    service['id'],
                    date.strftime('%Y-%m-%d'),
                    payment,
                    notes,
                    service['price']
                )
                if success:
                    UIManager.show_notification("🎉 Booking Confirmed! You will receive a confirmation email.", 'success')
                    time.sleep(1)
                    st.session_state['selected_service'] = None
                    st.session_state['current_page'] = "My Orders"
                    st.rerun()
                else:
                    UIManager.show_notification("Booking failed. Please try again.", 'error')

    @staticmethod
    def show(db):
        if not st.session_state.get('current_user') or st.session_state['current_user']['role'] != 'user':
            UIManager.show_notification("Access Denied", 'error')
            time.sleep(1)
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        if st.session_state.get('selected_service'):
            ServicesPage.show_service_details(db)
            return
        st.title("🛒 Available Services")
        # Search and filter
        col1, col2 = st.columns([1, 2])
        with col1:
            categories = ["All"] + sorted(list(set([s['category'] for s in db.get_services()])))
            selected_cat = st.selectbox("Filter by Category", categories)
        with col2:
            search = st.text_input("🔍 Search services...")
        services = db.get_services(selected_cat if selected_cat != "All" else None)
        # Filter by search
        if search:
            services = [s for s in services if search.lower() in s['name'].lower() or
                        search.lower() in s['description'].lower()]
        if not services:
            st.info("No services found matching your criteria.")
            return
        # Display services in grid
        cols = st.columns(3)
        for i, service in enumerate(services):
            with cols[i % 3]:
                UIManager.md(f"""
                <div class="service-card animate-enter" style="animation-delay: {i*0.05}s">
                <div class="card-icon">{service['icon']}</div>
                <h3 class="card-title">{service['name']}</h3>
                <div class="card-category">{service['category']}</div>
                <p class="card-desc">{service['description']}</p>
                <div class="card-rating">⭐ {service['rating']}</div>
                <p class="card-price">${service['price']}</p>
                </div>
                """)
                if st.button("✨ Select Service", key=f"select_{service['id']}", use_container_width=True):
                    st.session_state['selected_service'] = service
                    st.rerun()

class MyOrdersPage:
    @staticmethod
    def show(db):
        if not st.session_state.get('current_user'):
            UIManager.show_notification("Please login first", 'error')
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        user = st.session_state['current_user']
        st.title("📋 My Orders")
        orders = db.get_user_orders(user['id'])
        if not orders:
            st.info("No orders yet. Browse services to make your first booking!")
            return
        for order in orders:
            status_color = "#2ecc71" if order['status'] == 'Done' else ("#f1c40f" if order['status'] == 'Pending' else "#3498db")
            status_icon = "✅" if order['status'] == 'Done' else ("⏳" if order['status'] == 'Pending' else "❌")
            # Get unread message count for this order
            unread_count = 0
            try:
                messages = db.get_chat_messages(order['id'])
                unread_count = sum(1 for msg in messages if not msg['is_read'] and msg['sender_id'] != user['id'])
            except:
                pass
            UIManager.md(f"""
            <div style="background: rgba(30, 35, 60, 0.95); border-left: 5px solid {status_color};
            padding: 20px; margin: 15px 0; border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease; position: relative;">
            <div style="display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 1.5rem;">{order['icon']}</div>
            <div style="flex-grow: 1;">
            <h3 style="margin: 0;">{order['service_name']}</h3>
            <p style="margin: 5px 0; color: rgba(255,255,255,0.7); font-size: 0.9rem;">
            Order ID: {order['id'][:8]}...
            </p>
            </div>
            <span style="color: {status_color}; font-weight: bold;">{status_icon} {order['status']}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
            <div>
            <p><strong>📅 Service Date:</strong> {order['booking_date']}</p>
            <p><strong>💰 Price:</strong> ${order['price']}</p>
            </div>
            <div>
            <p><strong>💳 Payment Method:</strong> {order['payment_method']}</p>
            <p><strong>📝 Order Date:</strong> {order['created_at'][:10] if order['created_at'] else 'N/A'}</p>
            </div>
            </div>
            {f"<p><strong>📝 Special Instructions:</strong> {order['notes']}</p>" if order['notes'] else ""}
            </div>
            """)
            # Action buttons
            col1, col2 = st.columns([3, 1])
            with col2:
                chat_button_text = "💬 Chat with Technician"
                if unread_count > 0:
                    chat_button_text = f"💬 Chat ({unread_count})"
                if st.button(chat_button_text, key=f"chat_{order['id']}", use_container_width=True):
                    st.session_state['current_chat_order'] = order['id']
                    st.session_state['current_page'] = 'My Chats'
                    st.rerun()

class PendingOrdersPage:
    @staticmethod
    def show(db):
        if not st.session_state.get('current_user') or st.session_state['current_user']['role'] != 'technical':
            UIManager.show_notification("Access Denied", 'error')
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        user = st.session_state['current_user']
        st.title("🛠️ Pending Service Requests")
        orders = db.get_pending_orders(user['id'])
        if not orders:
            st.success("🎉 No pending orders!")
            return
        for order in orders:
            unread_count = order.get('unread_count', 0)
            UIManager.md(f"""
            <div style="background: rgba(30, 35, 60, 0.95); padding: 20px; margin: 15px 0;
            border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1); border-left: 5px solid #f1c40f;
            position: relative;">
            {f"<span class='order-chat-badge'>{unread_count}</span>" if unread_count > 0 else ""}
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
            <div>
            <h3 style="margin: 0;">{order['service_name']}</h3>
            <p style="color: #e0e0e0; margin: 5px 0;">Order ID: {order['id'][:8]}...</p>
            </div>
            <span style="background: #f1c40f20; color: #f1c40f; padding: 5px 12px; border-radius: 12px; font-weight: bold;">⏳ Pending</span>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h4 style="margin: 0 0 10px 0;">👤 Client Details</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
            <p style="margin: 5px 0;"><strong>Name:</strong> {order['user_name']}</p>
            <p style="margin: 5px 0;"><strong>📧 Email:</strong> {order['user_email']}</p>
            {f"<p style='margin: 5px 0;'><strong>📞 Phone:</strong> {order['user_phone']}</p>" if order['user_phone'] else ""}
            </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            <div>
            <p><strong>📅 Service Date:</strong> {order['booking_date']}</p>
            <p><strong>💰 Price:</strong> ${order['price']}</p>
            </div>
            <div>
            <p><strong>💳 Payment Method:</strong> {order['payment_method']}</p>
            <p><strong>📝 Order Date:</strong> {order['created_at'][:10] if order['created_at'] else 'N/A'}</p>
            </div>
            </div>
            {f"<div style='margin-top: 15px;'><p><strong>📝 Special Instructions:</strong></p><p style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px;'>{order['notes']}</p></div>" if order['notes'] else ""}
            </div>
            """)
            # Action buttons
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                chat_button_text = "💬 Chat with Client"
                if unread_count > 0:
                    chat_button_text = f"💬 Chat ({unread_count})"
                if st.button(chat_button_text, key=f"chat_{order['id']}", use_container_width=True):
                    st.session_state['current_chat_order'] = order['id']
                    st.session_state['current_page'] = 'My Chats'
                    st.rerun()
            with col3:
                if st.button(f"✅ Complete", key=f"complete_{order['id']}", use_container_width=True):
                    if db.update_order_status(order['id'], 'Done'):
                        UIManager.show_notification("✅ Order completed successfully!", 'success')
                        time.sleep(1)
                        st.rerun()

class ChatPage:
    @staticmethod
    def show(db):
        user = st.session_state['current_user']
        if not user:
            UIManager.show_notification("Please login first", 'error')
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        st.title("💬 My Chats")
        chats = db.get_user_chats(user['id'], user['role'])
        if not chats:
            st.info("No chats yet. Start by booking a service or accepting a pending order!")
            return
        # Display chat list
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Conversations")
            for chat in chats:
                is_active = st.session_state.get('current_chat_order') == chat['order_id']
                UIManager.md(f"""
                <div class="chat-list-item {'active' if is_active else ''}"
                     style="position: relative; cursor: pointer;">
                {f"<span class='order-chat-badge'>{chat['unread_count']}</span>" if chat.get('unread_count', 0) > 0 else ""}
                <div class="chat-list-info">
                <h4>{chat['service_name']}</h4>
                <p>Status: {chat['status']}</p>
                <p>Date: {chat['booking_date']}</p>
                {('<p style="color: #f1c40f;">👤 ' + chat.get('user_name', 'User') + '</p>' if 'user_name' in chat else '')}
                </div>
                </div>
                """)
                if st.button(f"Select Chat", key=f"select_{chat['order_id']}",
                             use_container_width=True, help=f"Select chat for {chat['service_name']}"):
                    st.session_state['current_chat_order'] = chat['order_id']
                    db.mark_messages_as_read(chat['order_id'], user['id'])
                    st.rerun()
        with col2:
            if st.session_state.get('current_chat_order'):
                order_id = st.session_state['current_chat_order']
                user = st.session_state['current_user']
                order = db.get_order_details(order_id)
                if not order:
                    st.error("Order not found")
                    return
                messages = db.get_chat_messages(order_id)
                other_party_name = order['technician_name'] if user['role'] == 'user' else order['user_name']
                other_party_role = "Technician" if user['role'] == 'user' else "Client"
                UIManager.md(f"""
                <div class="chat-header">
                    <h2>{order['service_name']}</h2>
                    <p>Chat with {other_party_name} ({other_party_role})</p>
                    <p style="font-size: 12px; margin-top: 5px;">Order ID: {order_id[:8]}...</p>
                </div>
                <div class="chat-messages">
                """)
                if not messages:
                    UIManager.md("""
                    <div style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                        <p style="font-size: 1.2rem;">💬 No messages yet</p>
                        <p>Start the conversation by sending a message below!</p>
                    </div>
                    """)
                else:
                    for msg in messages:
                        is_current_user = msg['sender_id'] == user['id']
                        message_class = "user" if is_current_user else "tech"
                        UIManager.md(f"""
                        <div class="chat-message {message_class}">
                        <div class="chat-message-sender">
                        {msg['sender_name']} ({'You' if is_current_user else msg['sender_role'].capitalize()})
                        </div>
                        <div class="chat-message-content">
                        {msg['message']}
                        </div>
                        <div class="chat-message-time">
                        {UIManager.format_datetime(msg['created_at'])}
                        </div>
                        </div>
                        """)
                UIManager.md('</div>')
                # Send message form
                with st.form(key="chat_message_form"):
                    message = st.text_area("Type your message...", height=80,
                                           placeholder="Write your message here...")
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if st.form_submit_button("Send", use_container_width=True):
                            if message.strip():
                                if db.save_chat_message(order_id, user['id'], message.strip()):
                                    db.mark_messages_as_read(order_id, user['id'])
                                    st.rerun()
                                else:
                                    UIManager.show_notification("Failed to send message", 'error')
                            else:
                                st.warning("Message cannot be empty.")
            else:
                st.info("👈 Select a conversation from the list")

# ==================== MORE PAGES ====================
class ProfilePage:
    @staticmethod
    def show(db):
        user = st.session_state['current_user']
        st.title("👤 Your Profile")
        # Get profile data
        profile = db.get_user_profile(user['id'])
        if not profile:
            UIManager.show_notification("Error loading profile", 'error')
            return
        # Display profile info
        col1, col2 = st.columns([1, 2])
        with col1:
            UIManager.md(f"""
            <div class="profile-card">
                <div class="profile-avatar">
                    {user['name'][0].upper() if user['name'] else 'U'}
                </div>
                <h2>{user['name']}</h2>
                <p style="color: #a29bfe;">{user['role'].capitalize()}</p>
                <p style="color: #e0e0e0; margin-top: 20px;">Member since: {profile['join_date'][:10] if profile['join_date'] else 'N/A'}</p>
            </div>
            """)
        with col2:
            UIManager.md("""
            <div style="background: rgba(30, 35, 60, 0.95); padding: 30px; border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);">
            """)
            st.subheader("Profile Information")
            with st.form("profile_form"):
                name = st.text_input("Full Name", value=profile['name'])
                email = st.text_input("Email", value=profile['email'], disabled=True)
                phone = st.text_input("Phone Number", value=profile['phone'] or "")
                bio = st.text_area("Bio", value=profile['bio'] or "",
                                  placeholder="Tell us about yourself...")
                if st.form_submit_button("Update Profile", use_container_width=True):
                    if db.update_user_profile(user['id'], name, phone, bio):
                        UIManager.show_notification("✅ Profile updated successfully!", 'success')
                        # Update session
                        st.session_state['current_user']['name'] = name
                        time.sleep(1)
                        st.rerun()
                    else:
                        UIManager.show_notification("Failed to update profile", 'error')
            UIManager.md("</div>")
        # Additional info
        UIManager.md("<br>")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📧 Email", profile['email'])
        with col2:
            st.metric("👤 Role", profile['role'].capitalize())
        with col3:
            last_login = profile['last_login'][:19] if profile['last_login'] else 'Never'
            st.metric("🕒 Last Login", last_login)
        UIManager.md("<br>")
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            AuthManager.logout()

class AdminDashboardPage:
    @staticmethod
    def show(db):
        if not st.session_state.get('current_user') or st.session_state['current_user']['role'] != 'admin':
            UIManager.show_notification("Access Denied", 'error')
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        st.title("📊 Admin Dashboard")
        stats = db.get_dashboard_stats()
        # Main stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>{stats.get('total_users', 0)}</h3>
                <p>👥 Total Users</p>
            </div>
            """)
        with col2:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>{stats.get('total_techs', 0)}</h3>
                <p>🔧 Technicians</p>
            </div>
            """)
        with col3:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>{stats.get('total_orders', 0)}</h3>
                <p>📦 Total Orders</p>
            </div>
            """)
        with col4:
            UIManager.md(f"""
            <div class="stats-card">
                <h3>${stats.get('revenue', 0):,.0f}</h3>
                <p>💰 Revenue</p>
            </div>
            """)
        # Secondary stats
        UIManager.md("<br>")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏳ Pending Orders", stats.get('pending_orders', 0))
        with col2:
            st.metric("✅ Completed Orders", stats.get('completed_orders', 0))
        with col3:
            st.metric("🛠️ Total Services", stats.get('total_services', 0))
        # Recent orders
        UIManager.md("---")
        st.subheader("📋 Recent Orders")
        orders = db.get_all_orders()[:10]  # Get last 10 orders
        if orders:
            df = pd.DataFrame(orders)
            df = df[['id', 'service_name', 'user_name', 'status', 'booking_date', 'price']]
            df.columns = ['Order ID', 'Service', 'Customer', 'Status', 'Date', 'Price']
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No orders yet")

class AllOrdersPage:
    @staticmethod
    def show(db):
        if not st.session_state.get('current_user') or st.session_state['current_user']['role'] != 'admin':
            UIManager.show_notification("Access Denied", 'error')
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        st.title("📋 All Orders")
        orders = db.get_all_orders()
        if orders:
            df = pd.DataFrame(orders)
            # Add filters
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Done"])
            with col2:
                date_filter = st.date_input("Filter by Date")
            with col3:
                service_filter = st.selectbox("Filter by Service", ["All"] + sorted(list(set(df['service_name'].tolist()))))
            # Apply filters
            if status_filter != "All":
                df = df[df['status'] == status_filter]
            if service_filter != "All":
                df = df[df['service_name'] == service_filter]
            if date_filter:
                df = df[df['booking_date'] == date_filter.strftime('%Y-%m-%d')]
            # Display
            st.dataframe(df[['id', 'service_name', 'user_name', 'status', 'booking_date', 'price', 'created_at']],
                         use_container_width=True)
            # Export option
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export as CSV",
                data=csv,
                file_name="orders_export.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No orders yet")

class AnalyticsPage:
    @staticmethod
    def show(db):
        if not st.session_state.get('current_user') or st.session_state['current_user']['role'] != 'admin':
            UIManager.show_notification("Access Denied", 'error')
            st.session_state['current_page'] = 'Home'
            st.rerun()
            return
        st.title("📈 Analytics Dashboard")
        stats = db.get_dashboard_stats()
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Revenue Overview")
            revenue_data = pd.DataFrame({
                'Category': ['Completed', 'Pending', 'Total'],
                'Amount': [stats.get('revenue', 0),
                           stats.get('pending_orders', 0) * 50,
                           stats.get('revenue', 0) + (stats.get('pending_orders', 0) * 50)]
            })
            st.bar_chart(revenue_data.set_index('Category'))
        with col2:
            st.subheader("Orders Distribution")
            orders_data = pd.DataFrame({
                'Status': ['Completed', 'Pending'],
                'Count': [stats.get('completed_orders', 0), stats.get('pending_orders', 0)]
            })
            st.line_chart(orders_data.set_index('Status'))
        # Detailed stats
        st.subheader("Detailed Statistics")
        metrics_cols = st.columns(4)
        metrics = [
            ("📊 Total Orders", stats.get('total_orders', 0)),
            ("💰 Total Revenue", f"${stats.get('revenue', 0):,.2f}"),
            ("📈 Avg Order Value", f"${stats.get('revenue', 0)/max(1, stats.get('completed_orders', 1)):.2f}"),
            ("🏆 Completion Rate", f"{(stats.get('completed_orders', 0)/max(1, stats.get('total_orders', 1))*100):.1f}%")
        ]
        for col, (label, value) in zip(metrics_cols, metrics):
            col.metric(label, value)

class AboutPage:
    @staticmethod
    def show():
        # Hero Section
        UIManager.md("""
        <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
             border-radius: 20px; margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);">
            <h1 style="font-size: 3.5rem; background: linear-gradient(to right, #fff, #a29bfe); -webkit-background-clip: text;
                       -webkit-text-fill-color: transparent; margin-bottom: 15px;">Building Connections</h1>
            <p style="font-size: 1.2rem; color: #dcdde1; max-width: 700px; margin: 0 auto;">
                Empowering communities by bridging the gap between skilled professionals and those in need.
                Trust, Quality, and Reliability - delivered.
            </p>
        </div>
        """)

        # Quick Stats Bar
        cols = st.columns(4)
        stats = [
            ("🚀", "Founded", "2023"),
            ("👥", "Active Users", "10k+"),
            ("⭐", "5-Star Reviews", "5000+"),
            ("🏙️", "Cities Served", "15+")
        ]
        for col, (icon, label, value) in zip(cols, stats):
            with col:
                UIManager.md(f"""
                <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; text-align: center;
                     border: 1px solid rgba(255,255,255,0.05); transition: transform 0.3s; cursor: default;"
                     onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1.0)'">
                    <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
                    <div style="font-size: 1.2rem; font-weight: bold; color: #a29bfe;">{value}</div>
                    <div style="font-size: 0.9rem; color: #aaa;">{label}</div>
                </div>
                """)

        UIManager.md("<br>")

        # Mission and Story Cards
        col1, col2 = st.columns(2)
        with col1:
            UIManager.md("""
            <div style="height: 100%; padding: 30px; background: rgba(30, 35, 60, 0.6); border-radius: 15px;
                 border-left: 5px solid #6c5ce7; box-shadow: 0 5px 20px rgba(0,0,0,0.2);">
                <h2 style="color: #fff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 20px;">
                    🎯 Our Mission
                </h2>
                <p style="color: #dcdde1; line-height: 1.6;">
                    Service Connect was founded with a simple yet powerful mission: to revolutionize how local services are discovered and delivered.
                    We believe everyone deserves access to high-quality help, and every skilled professional deserves a platform to shine.
                </p>
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <span style="background: rgba(108, 92, 231, 0.2); color: #a29bfe; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem;">Innovation</span>
                    <span style="background: rgba(108, 92, 231, 0.2); color: #a29bfe; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem;">Trust</span>
                    <span style="background: rgba(108, 92, 231, 0.2); color: #a29bfe; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem;">Community</span>
                </div>
            </div>
            """)
        with col2:
            UIManager.md("""
            <div style="height: 100%; padding: 30px; background: rgba(30, 35, 60, 0.6); border-radius: 15px;
                 border-left: 5px solid #e17055; box-shadow: 0 5px 20px rgba(0,0,0,0.2);">
                <h2 style="color: #fff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 20px;">
                    💡 Why Choose Us?
                </h2>
                <ul style="list-style: none; padding: 0; margin: 0; color: #dcdde1;">
                    <li style="margin-bottom: 12px; display: flex; align-items: center;">
                        <span style="color: #e17055; margin-right: 10px;">✓</span> Verified Professionals
                    </li>
                    <li style="margin-bottom: 12px; display: flex; align-items: center;">
                        <span style="color: #e17055; margin-right: 10px;">✓</span> Secure & Transparent Payments
                    </li>
                    <li style="margin-bottom: 12px; display: flex; align-items: center;">
                        <span style="color: #e17055; margin-right: 10px;">✓</span> 24/7 Dedicated Support
                    </li>
                    <li style="display: flex; align-items: center;">
                        <span style="color: #e17055; margin-right: 10px;">✓</span> Seamless Booking Experience
                    </li>
                </ul>
            </div>
            """)

        UIManager.md("<br>")

        # Team Section
        st.subheader("👥 Meet the Leadership")
        UIManager.md("<p style='color: #aaa; margin-bottom: 30px;'>The passionate team driving our vision forward.</p>")
        
        team = [
            ("👨‍💼", "John Doe", "CEO & Founder", "Visionary leader with 15y exp."),
            ("👩‍💻", "Jane Smith", "CTO", "Tech architect & AI enthusiast."),
            ("👨‍🔧", "Mike Johnson", "Head of Ops", "Ensuring smooth service delivery."),
            ("👩‍💼", "Sarah Lee", "Customer Success", "Champion of user happiness.")
        ]
        
        team_cols = st.columns(4)
        for col, (icon, name, role, bio) in zip(team_cols, team):
            with col:
                UIManager.md(f"""
                <div style="background: linear-gradient(145deg, #1e233c, #252947); padding: 30px 20px; border-radius: 18px;
                     text-align: center; border: 1px solid rgba(255,255,255,0.05); height: 280px; position: relative; overflow: hidden;
                     transition: transform 0.3s ease, box-shadow 0.3s ease;"
                     onmouseover="this.style.transform='translateY(-10px)'; this.style.boxShadow='0 15px 30px rgba(0,0,0,0.4)';"
                     onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 5px; background: linear-gradient(90deg, #6c5ce7, #a29bfe);"></div>
                    <div style="font-size: 3.5rem; margin-bottom: 15px; filter: drop-shadow(0 5px 10px rgba(0,0,0,0.3));">{icon}</div>
                    <h3 style="margin: 0; font-size: 1.2rem; color: #fff;">{name}</h3>
                    <p style="color: #6c5ce7; font-weight: 500; font-size: 0.9rem; margin: 5px 0 15px 0;">{role}</p>
                    <p style="font-size: 0.85rem; color: #b2bec3; line-height: 1.5;">{bio}</p>
                </div>
                """)

class ContactPage:
    @staticmethod
    def show(db):
        st.title("📞 Contact Us")
        UIManager.md("""
        <div style="background: rgba(30, 35, 60, 0.95); padding: 40px; border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);">
        """)
        col1, col2 = st.columns(2)
        with col1:
            UIManager.md("""
            ## Get in Touch
            We're here to help! Whether you have questions about our services,
            need technical support, or want to provide feedback, we'd love to hear from you.
            ### Contact Information
            - **📧 Email**: support@serviceconnect.com
            - **📞 Phone**: +1-234-567-8900
            - **📍 Address**: 123 Service St, Tech City
            - **🕒 Hours**: 9:00 AM - 6:00 PM (Mon-Fri)
            ### Quick Links
            - [FAQ](https://example.com/faq)
            - [Help Center](https://example.com/help)
            - [Terms of Service](https://example.com/terms)
            - [Privacy Policy](https://example.com/privacy)
            """)
        with col2:
            UIManager.md("## 📝 Contact Form")
            with st.form("contact_form"):
                name = st.text_input("Your Name")
                email = st.text_input("Your Email")
                subject = st.selectbox("Subject", [
                    "General Inquiry",
                    "Technical Support",
                    "Service Feedback",
                    "Partnership",
                    "Other"
                ])
                message = st.text_area("Your Message", height=150)
                if st.form_submit_button("Send Message", use_container_width=True):
                    if not name or not email or not message:
                        UIManager.show_notification("Please fill all required fields", 'error')
                    elif not UIManager.validate_email(email):
                        UIManager.show_notification("Invalid email format", 'error')
                    else:
                        if db.save_contact_message(name, email, subject, message):
                            UIManager.show_notification("✅ Message sent successfully! We'll get back to you soon.", 'success')
                        else:
                            UIManager.show_notification("Failed to send message. Please try again.", 'error')
        UIManager.md("</div>")
        # Map and location
        UIManager.md("<br>")
        st.subheader("📍 Our Location")
        # Simple map placeholder
        UIManager.md("""
        <div style="background: rgba(30, 35, 60, 0.8); padding: 30px; border-radius: 15px;
        text-align: center; border: 1px solid rgba(255,255,255,0.1);">
            <h3>🗺️ Service Connect Headquarters</h3>
            <p>123 Service Street, Tech City, TC 12345</p>
            <p style="color: #a29bfe;">📍 Click the map below for directions</p>
            <div style="background: rgba(0,0,0,0.3); height: 200px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center; margin-top: 20px;">
                <span style="font-size: 3rem;">🗺️</span>
            </div>
        </div>
        """)

# ==================== MAIN SERVICE APP ====================
class ServiceApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.chatbot = Chatbot(self.db.get_services())
        self._init_session_state()

    def _init_session_state(self):
        if 'current_user' not in st.session_state:
            st.session_state['current_user'] = None
        if 'current_page' not in st.session_state:
            st.session_state['current_page'] = 'Home'
        if 'selected_service' not in st.session_state:
            st.session_state['selected_service'] = None
        if 'chat_message' not in st.session_state:
            st.session_state['chat_message'] = ""
        if 'current_chat_order' not in st.session_state:
            st.session_state['current_chat_order'] = None
        if 'chatbot_history' not in st.session_state:
            st.session_state['chatbot_history'] = [
                {"role": "assistant", "content": "Hello! I'm ServiceBot. How can I help you today?"}
            ]

    def _show_sidebar_chatbot(self):
        with st.sidebar:
            st.title("🤖 ServiceBot")
            UIManager.md("""
            <div class="chatbot-container">
                <div class="chatbot-header">
                    <h2>Assistant</h2>
                    <p>Always here to help!</p>
                </div>
            </div>
            """)
            # Chat history
            # Chat history
            chat_html = '<div class="chat-messages-area">'
            for msg in st.session_state['chatbot_history']:
                align = "right" if msg['role'] == 'user' else "left"
                bg_color = "linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%)" if msg['role'] == 'user' else "rgba(255,255,255,0.1)"
                radius = "15px 15px 0 15px" if msg['role'] == 'user' else "15px 15px 15px 0"
                chat_html += dedent(f"""
                <div style="display: flex; justify-content: {align}; margin-bottom: 10px;">
                    <div style="background: {bg_color}; padding: 10px 15px; border-radius: {radius};
                         max-width: 80%; font-size: 0.9rem; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                        {msg['content']}
                    </div>
                </div>
                """).strip()
            chat_html += '</div>'
            UIManager.md(chat_html)
            # Chat input
            with st.form(key="chatbot_form", clear_on_submit=True):
                user_input = st.text_input("Ask a question...", placeholder="Type here...")
                if st.form_submit_button("Send", use_container_width=True):
                    if user_input:
                        st.session_state['chatbot_history'].append({"role": "user", "content": user_input})
                        # Update context
                        user_role = st.session_state['current_user']['role'] if st.session_state['current_user'] else 'guest'
                        self.chatbot.update_context(user_role, st.session_state['current_page'])
                        response = self.chatbot.get_response(user_input)
                        st.session_state['chatbot_history'].append({"role": "assistant", "content": response})
                        st.rerun()

    def run(self):
        UIManager.inject_css()
        
        # Navigation
        if st.session_state['current_user']:
            NavigationManager.show_navigation(self.db)
        else:
            NavigationManager.show_guest_navigation()
            
        # Page Routing
        page = st.session_state['current_page']
        
        if page == 'Home':
            HomePage.show(self.db)
        elif page == 'Login':
            LoginPage.show(self.db)
        elif page == 'Register':
            RegisterPage.show(self.db)
        elif page == 'Services':
            ServicesPage.show(self.db)
        elif page == 'My Orders':
            MyOrdersPage.show(self.db)
        elif page == 'Pending Orders':
            PendingOrdersPage.show(self.db)
        elif page == 'My Chats':
            ChatPage.show(self.db)
        elif page == 'Profile':
            ProfilePage.show(self.db)
        elif page == 'Dashboard':
            AdminDashboardPage.show(self.db)
        elif page == 'All Orders':
            AllOrdersPage.show(self.db)
        elif page == 'Analytics':
            AnalyticsPage.show(self.db)
        elif page == 'About':
            AboutPage.show()
        elif page == 'Contact Us':
            ContactPage.show(self.db)
            
        # Chatbot Sidebar
        self._show_sidebar_chatbot()
        
        # Footer
        UIManager.md("""
        <div style="text-align: center; margin-top: 50px; padding: 20px; color: rgba(255,255,255,0.5); font-size: 0.8rem;">
            &copy; 2024 Service Connect Platform. All rights reserved.
        </div>
        """)

if __name__ == "__main__":
    app = ServiceApp()
    app.run()

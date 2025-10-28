from flask import Flask, request, jsonify, render_template
import sqlite3
import hashlib
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS  # Important for frontend-backend communication

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)  # Enable CORS for all routes

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create user_profiles table for additional user information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            avatar_url TEXT,
            bio TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Email validation function
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Password strength validation
def is_strong_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is strong"

@app.route('/')
def index():
    return jsonify({"message": "P2P Chat API is running!"})

@app.route('/signup', methods=['POST', 'OPTIONS'])
def signup():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Validation
        if not username or not email or not password:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters long'}), 400
        
        if not is_valid_email(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        is_strong, password_message = is_strong_password(password)
        if not is_strong:
            return jsonify({'success': False, 'message': password_message}), 400
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Save to database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            
            user_id = cursor.lastrowid
            
            # Create empty profile
            cursor.execute(
                'INSERT INTO user_profiles (user_id) VALUES (?)',
                (user_id,)
            )
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'User registered successfully!',
                'user_id': user_id
            }), 201
            
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                return jsonify({'success': False, 'message': 'Username already exists'}), 400
            elif 'email' in str(e):
                return jsonify({'success': False, 'message': 'Email already exists'}), 400
            else:
                return jsonify({'success': False, 'message': 'Registration failed'}), 400
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error during signup: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, username, password_hash FROM users WHERE username = ? OR email = ?',
            (username, username)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            return jsonify({
                'success': True,
                'message': 'Login successful!',
                'user': {
                    'id': user[0],
                    'username': user[1]
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            
    except Exception as e:
        print(f"Error during login: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
    print("Starting server on http://127.0.0.1:8000")
    app.run(host='127.0.0.1', port=8000, debug=True)
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import os
import json
import asyncio
import websockets
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'p2p-chat-secret-key-2024'
CORS(app)

from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "message": "Authentication required"}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# WebSocket connections storage
active_connections = {}
user_peers = {}


# Database initialization
def init_db():
    conn = sqlite3.connect('p2p_chat.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # User profiles table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            location TEXT,
            website TEXT,
            status TEXT DEFAULT 'Online',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER,
            group_id INTEGER,
            message TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            file_name TEXT,
            file_size INTEGER,
            file_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id)
        )
    ''')

    # Groups table
    c.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # Group members table
    c.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            theme TEXT DEFAULT 'light',
            notifications_enabled BOOLEAN DEFAULT TRUE,
            privacy_level TEXT DEFAULT 'everyone',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# WebSocket handler
async def websocket_handler(websocket, path):
    username = None
    try:
        # Wait for initial registration message
        message = await websocket.recv()
        data = json.loads(message)

        if data.get('type') == 'register':
            username = data['username']
            user_id = data.get('user_id')

            # Store connection
            active_connections[username] = websocket
            user_peers[username] = {
                'user_id': user_id,
                'username': username,
                'is_online': True,
                'last_seen': datetime.now().isoformat()
            }

            print(f"User {username} connected via WebSocket")

            # Send confirmation
            await websocket.send(json.dumps({
                'type': 'user_registered',
                'username': username,
                'user_id': user_id,
                'message': 'Successfully connected to P2P Chat server'
            }))

            # Send current peer list
            await broadcast_peer_list()

            # Keep connection alive and handle messages
            try:
                async for message in websocket:
                    data = json.loads(message)
                    await handle_websocket_message(data, websocket, username)
            except websockets.exceptions.ConnectionClosed:
                print(f"WebSocket connection closed for {username}")

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up on disconnect
        if username and username in active_connections:
            del active_connections[username]
        if username and username in user_peers:
            user_peers[username]['is_online'] = False
            user_peers[username]['last_seen'] = datetime.now().isoformat()
        await broadcast_peer_list()


        #qwertyuiop
        


async def handle_websocket_message(data, websocket, username):
    message_type = data.get('type')

    if message_type == 'send_message':
        await handle_send_message(data, username)
    elif message_type == 'get_peers':
        await send_peer_list(websocket)
    elif message_type == 'broadcast_message':
        await handle_broadcast_message(data, username)
    elif message_type == 'create_group':
        await handle_create_group(data, username)
    elif message_type == 'call_request':
        await handle_call_request(data, username)
    elif message_type == 'call_accepted':
        await handle_call_accepted(data, username)
    elif message_type == 'call_rejected':
        await handle_call_rejected(data, username)
    elif message_type == 'call_end':
        await handle_call_end(data, username)
    elif message_type == 'file_message':
        await handle_file_message(data, username)


async def handle_send_message(data, sender_username):
    receiver_username = data.get('to')
    message_text = data.get('message')

    # Save message to database
    conn = sqlite3.connect('p2p_chat.db')
    c = conn.cursor()

    # Get user IDs
    c.execute('SELECT id FROM users WHERE username = ?', (sender_username,))
    sender = c.fetchone()
    c.execute('SELECT id FROM users WHERE username = ?', (receiver_username,))
    receiver = c.fetchone()

    if sender and receiver:
        c.execute('''
            INSERT INTO messages (sender_id, receiver_id, message, message_type)
            VALUES (?, ?, ?, ?)
        ''', (sender[0], receiver[0], message_text, 'text'))
        conn.commit()

    conn.close()

    # Forward message to recipient if online
    if receiver_username in active_connections:
        try:
            await active_connections[receiver_username].send(json.dumps({
                'type': 'message',
                'sender_username': sender_username,
                'sender_id': user_peers[sender_username]['user_id'],
                'message': message_text,
                'timestamp': datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send message to {receiver_username}")


async def handle_file_message(data, sender_username):
    receiver_username = data.get('to')
    file_data = {
        'file_name': data.get('file_name'),
        'file_size': data.get('file_size'),
        'file_type': data.get('file_type')
    }

    # Save file message to database
    conn = sqlite3.connect('p2p_chat.db')
    c = conn.cursor()

    c.execute('SELECT id FROM users WHERE username = ?', (sender_username,))
    sender = c.fetchone()
    c.execute('SELECT id FROM users WHERE username = ?', (receiver_username,))
    receiver = c.fetchone()

    if sender and receiver:
        c.execute('''
            INSERT INTO messages (sender_id, receiver_id, message, message_type, file_name, file_size, file_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (sender[0], receiver[0], f"File: {file_data['file_name']}", 'file',
              file_data['file_name'], file_data['file_size'], file_data['file_type']))
        conn.commit()

    conn.close()

    # Forward file message to recipient
    if receiver_username in active_connections:
        try:
            await active_connections[receiver_username].send(json.dumps({
                'type': 'file_message',
                'sender_username': sender_username,
                'sender_id': user_peers[sender_username]['user_id'],
                'file_name': file_data['file_name'],
                'file_size': file_data['file_size'],
                'file_type': file_data['file_type'],
                'timestamp': datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send file message to {receiver_username}")


async def handle_call_request(data, sender_username):
    receiver_username = data.get('to')
    call_type = data.get('call_type', 'audio')

    if receiver_username in active_connections:
        try:
            await active_connections[receiver_username].send(json.dumps({
                'type': 'call_request',
                'from': sender_username,
                'from_id': user_peers[sender_username]['user_id'],
                'call_type': call_type,
                'timestamp': datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send call request to {receiver_username}")


async def handle_call_accepted(data, sender_username):
    receiver_username = data.get('to')

    if receiver_username in active_connections:
        try:
            await active_connections[receiver_username].send(json.dumps({
                'type': 'call_accepted',
                'from': sender_username,
                'from_id': user_peers[sender_username]['user_id'],
                'timestamp': datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send call accepted to {receiver_username}")


async def handle_call_rejected(data, sender_username):
    receiver_username = data.get('to')

    if receiver_username in active_connections:
        try:
            await active_connections[receiver_username].send(json.dumps({
                'type': 'call_rejected',
                'from': sender_username,
                'from_id': user_peers[sender_username]['user_id'],
                'timestamp': datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send call rejected to {receiver_username}")


async def handle_call_end(data, sender_username):
    receiver_username = data.get('to')

    if receiver_username in active_connections:
        try:
            await active_connections[receiver_username].send(json.dumps({
                'type': 'call_end',
                'from': sender_username,
                'from_id': user_peers[sender_username]['user_id'],
                'timestamp': datetime.now().isoformat()
            }))
        except:
            print(f"Failed to send call end to {receiver_username}")


async def handle_broadcast_message(data, sender_username):
    message_text = data.get('message')

    # Broadcast to all connected users except sender
    for username, ws in active_connections.items():
        if username != sender_username:
            try:
                await ws.send(json.dumps({
                    'type': 'message',
                    'sender_username': sender_username,
                    'sender_id': user_peers[sender_username]['user_id'],
                    'message': message_text,
                    'timestamp': datetime.now().isoformat(),
                    'is_broadcast': True
                }))
            except:
                print(f"Failed to broadcast to {username}")


async def handle_create_group(data, creator_username):
    group_name = data.get('group_name')
    members = data.get('members', [])

    conn = sqlite3.connect('p2p_chat.db')
    c = conn.cursor()

    # Get creator ID
    c.execute('SELECT id FROM users WHERE username = ?', (creator_username,))
    creator = c.fetchone()

    if creator:
        # Create group
        c.execute('INSERT INTO groups (name, created_by) VALUES (?, ?)', (group_name, creator[0]))
        group_id = c.lastrowid

        # Add creator to group
        c.execute('INSERT INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, creator[0]))

        # Add other members
        for member_username in members:
            c.execute('SELECT id FROM users WHERE username = ?', (member_username,))
            member = c.fetchone()
            if member:
                c.execute('INSERT INTO group_members (group_id, user_id) VALUES (?, ?)', (group_id, member[0]))

        conn.commit()

    conn.close()


async def send_peer_list(websocket):
    peers_list = []
    for username, info in user_peers.items():
        peers_list.append({
            'username': username,
            'user_id': info['user_id'],
            'is_online': info['is_online'],
            'last_seen': info['last_seen']
        })

    await websocket.send(json.dumps({
        'type': 'peer_list',
        'peers': peers_list
    }))


async def broadcast_peer_list():
    peers_list = []
    for username, info in user_peers.items():
        peers_list.append({
            'username': username,
            'user_id': info['user_id'],
            'is_online': info['is_online'],
            'last_seen': info['last_seen']
        })

    for ws in active_connections.values():
        try:
            await ws.send(json.dumps({
                'type': 'peer_list',
                'peers': peers_list
            }))
        except:
            continue


def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Bind websocket to all interfaces so other machines can connect
    start_server = websockets.serve(websocket_handler, "0.0.0.0", 8766)

    print("WebSocket server starting on ws://0.0.0.0:8766 (listening on all interfaces)")
    loop.run_until_complete(start_server)
    loop.run_forever()


# REST API Routes
@app.route('/')
def index():
    return jsonify({"message": "P2P Chat API"})


@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"success": False, "message": "All fields are required"})

    hashed_password = hash_password(password)

    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                  (username, email, hashed_password))

        # Create default profile
        user_id = c.lastrowid
        c.execute('INSERT INTO user_profiles (user_id, full_name, bio) VALUES (?, ?, ?)',
                  (user_id, username, f"Welcome to {username}'s profile!"))

        # Create default settings
        c.execute('INSERT INTO user_settings (user_id) VALUES (?)', (user_id,))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "User created successfully"})

    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username or email already exists"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"success": False, "message": "All fields are required"})

    hashed_password = hash_password(password)

    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()
        c.execute('SELECT id, username, email FROM users WHERE username = ? AND password = ?',
                  (username, hashed_password))
        user = c.fetchone()
        conn.close()

        if user:
            user_data = {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "user_id": user[0],  # For compatibility with stp.html
                "profile_data": {
                    "avatar": f"https://i.pravatar.cc/150?u={user[1]}"
                }
            }
            # Set server-side session for this user so protected pages can use it
            session['user_id'] = user[0]
            session['username'] = user[1]
            session.permanent = True
            return jsonify({"success": True, "message": "Login successful", "user": user_data})
        else:
            return jsonify({"success": False, "message": "Invalid credentials"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/user/profile/<username>')
def get_user_profile(username):
    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()

        c.execute('''
            SELECT u.id, u.username, u.email, up.full_name, up.bio, up.avatar_url, up.location, up.website, up.status
            FROM users u 
            LEFT JOIN user_profiles up ON u.id = up.user_id 
            WHERE u.username = ?
        ''', (username,))

        profile = c.fetchone()
        conn.close()

        if profile:
            profile_data = {
                "id": profile[0],
                "username": profile[1],
                "email": profile[2],
                "full_name": profile[3] or profile[1],
                "bio": profile[4] or f"Welcome to {profile[1]}'s profile!",
                "avatar_url": profile[5] or f"https://i.pravatar.cc/150?u={profile[1]}",
                "location": profile[6] or "Unknown location",
                "website": profile[7] or "No website",
                "status": profile[8] or "Online"
            }
            return jsonify({"success": True, "profile": profile_data})
        else:
            return jsonify({"success": False, "message": "User not found"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))


# Serve and protect HTML pages so only authenticated users may access them
@app.route('/tp.html')
@login_required
def tp_page():
    return send_from_directory(app.root_path, 'tp.html')


@app.route('/profile.html')
@login_required
def profile_page():
    return send_from_directory(app.root_path, 'profile.html')


@app.route('/setting.html')
@login_required
def setting_page():
    return send_from_directory(app.root_path, 'setting.html')


@app.route('/api/user/update_profile', methods=['POST'])
def update_profile():
    data = request.json
    username = data.get('username')

    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()

        # Get user ID
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        user = c.fetchone()

        if not user:
            return jsonify({"success": False, "message": "User not found"})

        user_id = user[0]

        # Update profile
        c.execute('''
            INSERT OR REPLACE INTO user_profiles 
            (user_id, full_name, bio, avatar_url, location, website, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('full_name'),
            data.get('bio'),
            data.get('avatar_url'),
            data.get('location'),
            data.get('website'),
            data.get('status', 'Online')
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Profile updated successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/chat/messages/<int:user_id>')
def get_user_messages(user_id):
    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()

        c.execute('''
            SELECT m.*, u.username as sender_username 
            FROM messages m 
            JOIN users u ON m.sender_id = u.id 
            WHERE m.receiver_id = ? OR m.sender_id = ?
            ORDER BY m.timestamp DESC
            LIMIT 50
        ''', (user_id, user_id))

        messages = c.fetchall()
        conn.close()

        messages_list = []
        for msg in messages:
            messages_list.append({
                'id': msg[0],
                'sender_id': msg[1],
                'receiver_id': msg[2],
                'message': msg[4],
                'message_type': msg[5],
                'file_name': msg[6],
                'file_size': msg[7],
                'file_type': msg[8],
                'timestamp': msg[9],
                'sender_username': msg[10]
            })

        return jsonify({"success": True, "messages": messages_list})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/chat/peers')
def get_online_peers():
    try:
        peers_list = []
        for username, info in user_peers.items():
            peers_list.append({
                'username': username,
                'user_id': info['user_id'],
                'is_online': info['is_online'],
                'last_seen': info['last_seen']
            })

        return jsonify({"success": True, "peers": peers_list})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    data = request.json
    user_id = data.get('user_id')

    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()

        c.execute('''
            INSERT OR REPLACE INTO user_settings 
            (user_id, theme, notifications_enabled, privacy_level) 
            VALUES (?, ?, ?, ?)
        ''', (
            user_id,
            data.get('theme', 'light'),
            data.get('notifications_enabled', True),
            data.get('privacy_level', 'everyone')
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Settings updated successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/settings/<int:user_id>')
def get_settings(user_id):
    try:
        conn = sqlite3.connect('p2p_chat.db')
        c = conn.cursor()

        c.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
        settings = c.fetchone()

        if settings:
            settings_data = {
                'theme': settings[2],
                'notifications_enabled': bool(settings[3]),
                'privacy_level': settings[4]
            }
            return jsonify({"success": True, "settings": settings_data})
        else:
            # Return default settings
            return jsonify({"success": True, "settings": {
                'theme': 'light',
                'notifications_enabled': True,
                'privacy_level': 'everyone'
            }})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


if __name__ == '__main__':
    init_db()

    # Start WebSocket server in a separate thread
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()

    print("Starting Flask server on http://0.0.0.0:5000 (listening on all interfaces)")
    print("WebSocket server on ws://0.0.0.0:8766")
    app.run(host='0.0.0.0', debug=True, port=5000, use_reloader=False)

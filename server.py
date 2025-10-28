# server.py - FIXED VERSION
import asyncio
import websockets
import json
import sqlite3
from datetime import datetime
import uuid


class P2PChatServer:
    def __init__(self):
        self.connected_clients = {}  # websocket: user_info
        self.setup_database()

    def setup_database(self):
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                is_online BOOLEAN,
                last_seen TIMESTAMP
            )
        ''')

        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT,
                receiver_id TEXT,
                message_text TEXT,
                timestamp TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    async def handle_connection(self, websocket, path):
        print(f"New connection from {websocket.remote_address}")

        try:
            async for message in websocket:
                data = json.loads(message)
                await self.handle_message(data, websocket)

        except websockets.exceptions.ConnectionClosed:
            await self.handle_disconnection(websocket)
        except Exception as e:
            print(f"Error: {e}")
            await self.send_error(websocket, str(e))

    async def handle_message(self, data, websocket):
        message_type = data.get('type')

        if message_type == 'register':
            await self.register_user(data, websocket)
        elif message_type == 'get_peers':
            await self.send_peer_list(websocket)
        elif message_type == 'send_message':
            await self.handle_send_message(data, websocket)
        else:
            await self.send_error(websocket, f"Unknown message type: {message_type}")

    async def register_user(self, data, websocket):
        username = data.get('username')
        user_id = data.get('user_id')

        if not username:
            await self.send_error(websocket, "Username required")
            return

        # Generate user ID if not provided
        if not user_id:
            user_id = str(uuid.uuid4())

        # Store connection
        self.connected_clients[websocket] = {
            'user_id': user_id,
            'username': username,
            'address': websocket.remote_address
        }

        # Save to database (FIXED: Only store basic types)
        self.save_user(user_id, username, True)

        # Send confirmation
        response = {
            'type': 'user_registered',
            'user_id': user_id,
            'username': username,
            'message': 'Registration successful'
        }
        await websocket.send(json.dumps(response))

        # Notify all clients about new user
        await self.broadcast_peer_list()

        print(f"User registered: {username} ({user_id})")

    async def send_peer_list(self, websocket):
        peers = []
        for client_info in self.connected_clients.values():
            peers.append({
                'id': client_info['user_id'],
                'username': client_info['username'],
                'is_online': True
            })

        # Also include offline users from database
        offline_users = self.get_offline_users()
        peers.extend(offline_users)

        response = {
            'type': 'peer_list',
            'peers': peers
        }
        await websocket.send(json.dumps(response))

    async def handle_send_message(self, data, websocket):
        sender_info = self.connected_clients.get(websocket)
        if not sender_info:
            await self.send_error(websocket, "Not registered")
            return

        message_text = data.get('message')
        to_id = data.get('to_id')
        to_username = data.get('to')

        if not message_text:
            await self.send_error(websocket, "Message text required")
            return

        # Create message object
        message_id = str(uuid.uuid4())
        message_data = {
            'type': 'message',
            'message_id': message_id,
            'sender_id': sender_info['user_id'],
            'sender_username': sender_info['username'],
            'message': message_text,
            'timestamp': datetime.now().isoformat()
        }

        # Add target information
        if to_id:
            message_data['receiver_id'] = to_id
        if to_username:
            message_data['receiver_username'] = to_username

        # Save message to database (FIXED: Only store basic types)
        self.save_message(
            message_id=message_id,
            sender_id=sender_info['user_id'],
            receiver_id=to_id,
            message_text=message_text
        )

        # Broadcast to all connected clients
        await self.broadcast_message(message_data)

        print(f"Message from {sender_info['username']}: {message_text}")

    async def broadcast_message(self, message_data):
        disconnected = []
        for ws in self.connected_clients.keys():
            try:
                await ws.send(json.dumps(message_data))
            except:
                disconnected.append(ws)

        # Clean up disconnected clients
        for ws in disconnected:
            await self.handle_disconnection(ws)

    async def broadcast_peer_list(self):
        peers = []
        for client_info in self.connected_clients.values():
            peers.append({
                'id': client_info['user_id'],
                'username': client_info['username'],
                'is_online': True
            })

        offline_users = self.get_offline_users()
        peers.extend(offline_users)

        response = {
            'type': 'peer_list',
            'peers': peers
        }

        disconnected = []
        for ws in self.connected_clients.keys():
            try:
                await ws.send(json.dumps(response))
            except:
                disconnected.append(ws)

        for ws in disconnected:
            await self.handle_disconnection(ws)

    async def handle_disconnection(self, websocket):
        if websocket in self.connected_clients:
            user_info = self.connected_clients[websocket]
            username = user_info['username']
            user_id = user_info['user_id']

            # Update user status in database
            self.save_user(user_id, username, False)

            del self.connected_clients[websocket]
            print(f"User disconnected: {username}")

            # Notify other clients
            await self.broadcast_peer_list()

    async def send_error(self, websocket, error_message):
        error_data = {
            'type': 'error',
            'message': error_message
        }
        try:
            await websocket.send(json.dumps(error_data))
        except:
            pass  # Client already disconnected

    def save_user(self, user_id, username, is_online):
        """FIXED: Only store basic types in database"""
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO users (id, username, is_online, last_seen)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, is_online, datetime.now()))

        conn.commit()
        conn.close()

    def save_message(self, message_id, sender_id, receiver_id, message_text):
        """FIXED: Only store basic types in database"""
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO messages (id, sender_id, receiver_id, message_text, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (message_id, sender_id, receiver_id, message_text, datetime.now()))

        conn.commit()
        conn.close()

    def get_offline_users(self):
        """FIXED: Only return basic types"""
        conn = sqlite3.connect('chat.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, is_online FROM users WHERE is_online = FALSE
        ''')

        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'is_online': bool(row[2])
            })

        conn.close()
        return users


async def main():
    server = P2PChatServer()

    # Start WebSocket server
    start_server = await websockets.serve(
        server.handle_connection, "localhost", 8765
    )

    print("🚀 P2P Chat Server running on ws://localhost:8765")
    print("📝 Make sure your frontend connects to: ws://localhost:8765")
    print("✅ Server is ready to accept connections!")

    # Keep server running
    await start_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
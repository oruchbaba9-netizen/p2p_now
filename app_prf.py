from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from database import Database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

CORS(app)

# Initialize database
try:
    db = Database()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {e}")
    exit(1)


@app.route('/')
def index():
    return jsonify({"message": "P2P Chat Backend API", "status": "running"})


# User Authentication
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        profile_data = data.get('profile_data', {})

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        # Generate unique IDs
        did = f"did:p2p:user:{uuid.uuid4()}"
        node_id = f"node_{uuid.uuid4().hex[:16]}"

        user_id = db.create_user(username, password, did, node_id, profile_data)

        if user_id:
            return jsonify({
                "message": "User registered successfully",
                "user_id": user_id,
                "did": did,
                "node_id": node_id
            }), 201
        else:
            return jsonify({"error": "Username already exists"}), 400
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        user = db.get_user(username)

        if user and user['password'] == password:
            # Update online status
            db.update_user_online_status(user['id'], True)

            return jsonify({
                "user_id": user['id'],
                "username": user['username'],
                "did": user['did'],
                "node_id": user['node_id'],
                "profile_data": user['profile_data']
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if user_id:
            db.update_user_online_status(user_id, False)

        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500


# Peers Management
@app.route('/api/peers', methods=['GET'])
def get_peers():
    try:
        peers = db.get_peers()
        return jsonify({"peers": peers}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get peers: {str(e)}"}), 500


@app.route('/api/peers/discover', methods=['POST'])
def discover_peers():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        # Add some demo peers discovered via DHT
        demo_peers = [
            {
                'peer_id': f'peer_{uuid.uuid4().hex[:8]}',
                'username': f'User_{uuid.uuid4().hex[:6]}',
                'discovered_via_dht': True,
                'is_online': True
            } for _ in range(3)
        ]

        for peer in demo_peers:
            db.add_peer(
                peer['peer_id'],
                peer['username'],
                discovered_via_dht=peer['discovered_via_dht']
            )
            db.update_peer_online_status(peer['peer_id'], peer['is_online'])

        peers = db.get_peers()
        return jsonify({
            "message": f"Discovered {len(demo_peers)} new peers via DHT",
            "peers": peers
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to discover peers: {str(e)}"}), 500


# Messages
@app.route('/api/messages/<int:user_id>', methods=['GET'])
def get_messages(user_id):
    try:
        messages = db.get_user_messages(user_id)
        return jsonify({"messages": messages}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get messages: {str(e)}"}), 500


@app.route('/api/messages/send', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        group_id = data.get('group_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')

        if not sender_id or not content:
            return jsonify({"error": "Sender ID and content required"}), 400

        message_id = db.save_message(sender_id, receiver_id, group_id, content, message_type)

        if message_id:
            return jsonify({"message_id": message_id, "status": "sent"}), 200
        else:
            return jsonify({"error": "Failed to send message"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to send message: {str(e)}"}), 500


if __name__ == '__main__':
    print("Starting P2P Chat Backend...")
    print("API available at: http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
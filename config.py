import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'p2p-chat-secret-key'
    DATABASE_PATH = 'p2p_chat.db'
    UPLOAD_FOLDER = 'uploads'
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    WS_HOST = 'localhost'
    WS_PORT = 8765
    API_HOST = '0.0.0.0'
    API_PORT = 8000
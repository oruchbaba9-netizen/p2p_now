from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json

@dataclass
class User:
    id: int
    username: str
    password: str
    did: Optional[str] = None
    node_id: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'did': self.did,
            'node_id': self.node_id,
            'profile_data': self.profile_data or {},
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class Peer:
    id: int
    peer_id: str
    username: str
    ip_address: Optional[str] = None
    port: Optional[int] = None
    public_key: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None
    discovered_via_dht: bool = False
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'id': self.id,
            'peer_id': self.peer_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'port': self.port,
            'public_key': self.public_key,
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'discovered_via_dht': self.discovered_via_dht,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class Message:
    id: int
    sender_id: int
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    encrypted_content: str = ""
    message_type: str = "text"
    file_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    delivered: bool = False
    read_receipt: bool = False
    sender_username: Optional[str] = None

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'group_id': self.group_id,
            'encrypted_content': self.encrypted_content,
            'message_type': self.message_type,
            'file_data': self.file_data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'delivered': self.delivered,
            'read_receipt': self.read_receipt,
            'sender_username': self.sender_username
        }

@dataclass
class Group:
    id: int
    name: str
    created_by: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
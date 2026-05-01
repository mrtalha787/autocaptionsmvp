import json
import hashlib
import os
import uuid
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def load_users(store_path: Path) -> Dict[str, Dict]:
    if store_path.exists():
        try:
            return json.loads(store_path.read_text())
        except Exception:
            return {}
    return {}


def save_users(store_path: Path, users: Dict[str, Dict]) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(users, indent=2))


def register_user(store_path: Path, username: str, password: str) -> bool:
    users = load_users(store_path)
    if username in users:
        return False
    salt = os.urandom(8).hex()
    users[username] = {
        "salt": salt,
        "password": _hash_password(password, salt),
        "auth_method": "local",
        "created_at": datetime.now().isoformat(),
    }
    save_users(store_path, users)
    return True


def authenticate_user(store_path: Path, username: str, password: str) -> bool:
    users = load_users(store_path)
    if username not in users:
        return False
    user = users[username]
    hashed = _hash_password(password, user["salt"])
    return hashed == user["password"]


# ============= OAUTH & SOCIAL LOGIN =============


def register_oauth_user(
    store_path: Path,
    email: str,
    provider: str,
    provider_id: str,
    display_name: str = "None",
) -> tuple[bool, str]:
    """Register or retrieve an OAuth user.
    
    Args:
        store_path: Path to users.json
        email: User email
        provider: OAuth provider (google, facebook)
        provider_id: User ID from provider
        display_name: Display name from provider
        
    Returns:
        (success, username)
    """
    users = load_users(store_path)
    
    # Check if user already exists with this email
    for username, user_data in users.items():
        if user_data.get("email") == email:
            # Update OAuth info if needed
            if provider not in user_data.get("oauth_providers", {}):
                user_data["oauth_providers"] = user_data.get("oauth_providers", {})
                user_data["oauth_providers"][provider] = provider_id
                save_users(store_path, users)
            return True, username
    
    # Create new OAuth user
    username = email.split("@")[0] + "_" + provider[:3]  # e.g., john_goo
    counter = 1
    original_username = username
    while username in users:
        username = f"{original_username}_{counter}"
        counter += 1
    
    users[username] = {
        "email": email,
        "auth_method": provider,
        "display_name": display_name or email,
        "oauth_providers": {provider: provider_id},
        "created_at": datetime.now().isoformat(),
    }
    save_users(store_path, users)
    return True, username


# ============= SESSION MANAGEMENT (Single Tab Login) =============


class SessionManager:
    """Manages user sessions to enforce single-tab login."""
    
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.sessions_dir / "sessions.json"
    
    def _load_sessions(self) -> Dict[str, Dict]:
        """Load active sessions."""
        if self.sessions_file.exists():
            try:
                return json.loads(self.sessions_file.read_text())
            except:
                return {}
        return {}
    
    def _save_sessions(self, sessions: Dict) -> None:
        """Save sessions to disk."""
        self.sessions_file.write_text(json.dumps(sessions, indent=2))
    
    def create_session(self, username: str) -> str:
        """Create a new session token for user. Invalidates previous sessions.
        
        Returns:
            session_token
        """
        sessions = self._load_sessions()
        
        # Invalidate all previous sessions for this user
        sessions = {
            sid: data
            for sid, data in sessions.items()
            if data.get("username") != username
        }
        
        # Create new session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "username": username,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        }
        self._save_sessions(sessions)
        return session_id
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """Validate session token and return username if valid.
        
        Returns:
            username if valid, None otherwise
        """
        sessions = self._load_sessions()
        if session_token not in sessions:
            return None
        
        session = sessions[session_token]
        expires = datetime.fromisoformat(session["expires_at"])
        
        if datetime.now() > expires:
            # Session expired
            del sessions[session_token]
            self._save_sessions(sessions)
            return None
        
        return session.get("username")
    
    def invalidate_session(self, session_token: str) -> None:
        """Invalidate (logout) a session."""
        sessions = self._load_sessions()
        if session_token in sessions:
            del sessions[session_token]
            self._save_sessions(sessions)
    
    def get_user_sessions(self, username: str) -> list:
        """Get all active sessions for a user."""
        sessions = self._load_sessions()
        user_sessions = []
        for sid, data in sessions.items():
            if data.get("username") == username:
                expires = datetime.fromisoformat(data["expires_at"])
                if datetime.now() <= expires:
                    user_sessions.append(sid)
        return user_sessions


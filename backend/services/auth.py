import json
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional


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
    store_path.write_text(json.dumps(users))


def register_user(store_path: Path, username: str, password: str) -> bool:
    users = load_users(store_path)
    if username in users:
        return False
    salt = os.urandom(8).hex()
    users[username] = {"salt": salt, "password": _hash_password(password, salt)}
    save_users(store_path, users)
    return True


def authenticate_user(store_path: Path, username: str, password: str) -> bool:
    users = load_users(store_path)
    if username not in users:
        return False
    user = users[username]
    hashed = _hash_password(password, user["salt"])
    return hashed == user["password"]

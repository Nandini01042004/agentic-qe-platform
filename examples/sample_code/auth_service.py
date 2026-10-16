"""Enterprise Authentication Service with Token Management and Policy Validation."""

import hashlib
import hmac
import time
import base64
import json
from typing import Dict, Any, Optional


class AuthError(Exception):
    """Base exception for authentication failures."""
    pass


class UserNotFoundError(AuthError):
    """Raised when the specified user is not present in storage."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when password verification fails."""
    pass


class AuthService:
    """
    Enterprise Authentication Service handling user registration,
    salted password hashing, JWT-style signature verification, and role checks.
    """

    def __init__(self, secret_key: str = "enterprise-secret-key"):
        if not secret_key or len(secret_key) < 8:
            raise ValueError("Secret key must be at least 8 characters long.")
        self.secret_key = secret_key
        self._user_db: Dict[str, Dict[str, Any]] = {}

    def _hash_password(self, password: str, salt: str) -> str:
        """Computes SHA-256 hash of password with salt."""
        hasher = hashlib.sha256()
        hasher.update((salt + password).encode("utf-8"))
        return hasher.hexdigest()

    def register_user(self, username: str, password: str, role: str = "user") -> Dict[str, Any]:
        """
        Registers a new user with password validation and salting.
        Raises ValueError if username exists or password is weak.
        """
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long.")

        clean_username = username.strip().lower()
        if clean_username in self._user_db:
            raise ValueError(f"User '{clean_username}' already exists.")

        # Password strength validation
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit.")

        salt = hashlib.sha256(str(time.time()).encode("utf-8")).hexdigest()[:16]
        pw_hash = self._hash_password(password, salt)

        record = {
            "username": clean_username,
            "password_hash": pw_hash,
            "salt": salt,
            "role": role,
            "created_at": time.time(),
        }
        self._user_db[clean_username] = record

        # Return sanitized representation
        return {
            "username": clean_username,
            "role": role,
            "created_at": record["created_at"],
        }

    def authenticate(self, username: str, password: str) -> str:
        """
        Validates credentials and issues a signed security token.
        Raises UserNotFoundError or InvalidCredentialsError.
        """
        clean_username = username.strip().lower()
        if clean_username not in self._user_db:
            raise UserNotFoundError(f"User '{clean_username}' not found.")

        user = self._user_db[clean_username]
        expected_hash = self._hash_password(password, user["salt"])

        if not hmac.compare_digest(user["password_hash"], expected_hash):
            raise InvalidCredentialsError("Invalid credentials provided.")

        return self._issue_token(user)

    def _issue_token(self, user: Dict[str, Any]) -> str:
        """Creates a signed HMAC token encoding user identity and role."""
        payload = {
            "sub": user["username"],
            "role": user["role"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

        sig = hmac.new(self.secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{sig}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifies token integrity and expiration.
        Returns decoded claims dictionary.
        """
        parts = token.split(".")
        if len(parts) != 2:
            raise ValueError("Malformed token format.")

        payload_b64, signature = parts
        expected_sig = hmac.new(self.secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Token signature verification failed.")

        # Re-add padding if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding

        decoded = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))

        if time.time() > decoded.get("exp", 0):
            raise ValueError("Token has expired.")

        return decoded

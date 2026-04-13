"""
Encryption utilities for securing Canvas API keys.
Uses Fernet symmetric encryption from cryptography library.
"""

import os
from cryptography.fernet import Fernet

# Load or create encryption key
ENCRYPTION_KEY_FILE = ".encryption_key"

def get_or_create_key():
    """Get encryption key from file or create a new one."""
    if os.path.exists(ENCRYPTION_KEY_FILE):
        with open(ENCRYPTION_KEY_FILE, "rb") as f:
            return f.read()
    
    # Create new key
    key = Fernet.generate_key()
    with open(ENCRYPTION_KEY_FILE, "wb") as f:
        f.write(key)
    return key

def encrypt_token(token: str) -> str:
    """Encrypt a Canvas API token."""
    key = get_or_create_key()
    cipher = Fernet(key)
    encrypted = cipher.encrypt(token.encode())
    return encrypted.decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a Canvas API token."""
    try:
        key = get_or_create_key()
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

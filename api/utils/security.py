import secrets
import hashlib


def hash_api_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()


def generate_api_key():
    """
    Generates a new API key and returns:
    - plain_key (what user gets)
    - hashed_key (what is stored in DB)
    """

    plain_key = secrets.token_hex(32)  # 64-char key
    hashed_key = hash_api_key(plain_key)

    return plain_key, hashed_key

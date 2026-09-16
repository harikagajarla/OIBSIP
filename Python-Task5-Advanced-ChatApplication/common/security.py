"""Password hashing helpers. Passwords are never persisted in plaintext."""
import hashlib
import secrets

ITERATIONS = 310_000

def hash_password(password: str) -> tuple[str, str]:
    if not isinstance(password, str) or len(password) < 6:
        raise ValueError("Password must contain at least 6 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()

def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    try:
        calculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS).hex()
        return secrets.compare_digest(calculated, digest_hex)
    except (TypeError, ValueError):
        return False

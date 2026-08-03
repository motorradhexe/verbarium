"""Password hashing and session tokens. → D15"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

#: Argon2id with the library defaults, which track current guidance.
_hasher = PasswordHasher()

#: A hash of a password nobody has, used to spend the same time verifying a
#: login for an address that does not exist. Without it, response time tells
#: an attacker which addresses are registered.
_DUMMY_HASH = _hasher.hash("password-for-a-user-that-does-not-exist")

SESSION_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with weaker parameters than current ones."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def spend_dummy_verification() -> None:
    """Burn one verification's worth of time on a hash that cannot match."""
    verify_password("any password", _DUMMY_HASH)


def generate_session_token() -> str:
    """A 256-bit random token. This value is what the client stores."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """The value stored server-side.

    SHA-256 rather than Argon2: the token is already 256 bits of randomness,
    so there is nothing to brute-force, and sessions are verified on every
    request where a deliberately slow hash would be felt. Hashing at all is
    what matters — a leaked database must not hand over usable sessions.
    """
    return hashlib.sha256(token.encode()).hexdigest()

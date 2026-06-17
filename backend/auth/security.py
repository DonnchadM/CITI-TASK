"""Password hashing for the auth service.

Uses PBKDF2-HMAC-SHA256 from the standard library (the scheme behind Django's
default hasher): a per-password random salt and a high iteration count, stored in
a self-describing ``algorithm$iterations$salt$hash`` string. Stdlib-only means no
native extension, so it loads identically on LocalStack, AWS Lambda, and in tests
— unlike bcrypt, whose compiled wheel is tied to the build platform's glibc.
"""

import base64
import hashlib
import hmac
import os

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16


def hash_password(plain: str) -> str:
    """Hash a plaintext password with a fresh random salt."""
    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return "{}${}${}${}".format(
        _ALGORITHM,
        _ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def verify_password(plain: str, stored: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        derived = hashlib.pbkdf2_hmac(
            "sha256", plain.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(derived, expected)
    except (ValueError, TypeError):
        return False


def hash_password(password: str, /) -> str:
    """
    Hash a password using PBKDF2 with SHA-256.

    Args:
        password: The plain-text password to hash.

    Returns the encoded password string in the format:
    `pbkdf2_sha256$<iterations>$<salt>$<digest>`
    """
    ...


def verify_password(password: str, encoded_password: str, /) -> bool:
    """
    Verify a password against an encoded password string.

    Args:
        password: The plain-text password to verify.
        encoded_password: The encoded password string to verify against.

    Returns `True` if the password matches, `False` otherwise.
    """
    ...

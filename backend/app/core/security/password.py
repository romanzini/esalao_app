"""Password hashing utilities using Argon2."""

from passlib.context import CryptContext

# Argon2 password hashing context
# Using Argon2id variant (hybrid mode - best security)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4,  # 4 parallel threads
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    Args:
        password: Plain text password to hash

    Returns:
        Argon2 hash string

    Example:
        >>> hash_password("my_secret_password")
        '$argon2id$v=19$m=65536,t=3,p=4$...'
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against an Argon2 hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Argon2 hash to verify against

    Returns:
        True if password matches hash, False otherwise

    Example:
        >>> hash_value = hash_password("my_password")
        >>> verify_password("my_password", hash_value)
        True
        >>> verify_password("wrong_password", hash_value)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be updated.

    Useful when Argon2 parameters are changed in configuration.

    Args:
        hashed_password: Argon2 hash to check

    Returns:
        True if hash should be regenerated, False otherwise
    """
    return pwd_context.needs_update(hashed_password)

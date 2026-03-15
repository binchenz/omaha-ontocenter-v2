"""Secrets management for configuration encryption/decryption.

This module provides functions to encrypt and decrypt sensitive values in configuration
files using Fernet symmetric encryption.
"""

from copy import deepcopy
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from omaha.utils.exceptions import SecurityError


def generate_key() -> bytes:
    """Generate a new Fernet encryption key.

    Returns:
        bytes: A new Fernet encryption key

    Example:
        >>> key = generate_key()
        >>> isinstance(key, bytes)
        True
    """
    return Fernet.generate_key()


def encrypt_value(value: str, key: bytes) -> str:
    """Encrypt a string value using Fernet encryption.

    Args:
        value: The plaintext string to encrypt
        key: The Fernet encryption key

    Returns:
        str: Base64-encoded encrypted string

    Example:
        >>> key = generate_key()
        >>> encrypted = encrypt_value("secret", key)
        >>> isinstance(encrypted, str)
        True
    """
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(value.encode())
    return encrypted_bytes.decode()


def decrypt_value(encrypted_value: str, key: bytes) -> str:
    """Decrypt an encrypted string using Fernet decryption.

    Args:
        encrypted_value: The base64-encoded encrypted string
        key: The Fernet encryption key

    Returns:
        str: The original plaintext string

    Raises:
        SecurityError: If decryption fails due to invalid key or corrupted data

    Example:
        >>> key = generate_key()
        >>> encrypted = encrypt_value("secret", key)
        >>> decrypt_value(encrypted, key)
        'secret'
    """
    try:
        fernet = Fernet(key)
        decrypted_bytes = fernet.decrypt(encrypted_value.encode())
        return decrypted_bytes.decode()
    except (InvalidToken, Exception) as e:
        raise SecurityError(
            f"Decryption failed: {str(e)}",
            context={"encrypted_value_length": len(encrypted_value)}
        )


def _get_nested_value(data: dict, path_parts: list[str]) -> Any:
    """Get value from nested dict using path parts.

    Args:
        data: The dictionary to traverse
        path_parts: List of keys to traverse

    Returns:
        The value at the path, or None if not found
    """
    current = data
    for part in path_parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _set_nested_value(data: dict, path_parts: list[str], value: Any) -> None:
    """Set value in nested dict using path parts.

    Args:
        data: The dictionary to modify
        path_parts: List of keys to traverse
        value: The value to set
    """
    current = data
    for part in path_parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[path_parts[-1]] = value


def _process_path_with_wildcard(
    data: dict,
    path_parts: list[str],
    key: bytes,
    encrypt: bool
) -> None:
    """Process a path that may contain wildcards.

    Args:
        data: The dictionary to process
        path_parts: List of path parts (may contain '*')
        key: The encryption key
        encrypt: True to encrypt, False to decrypt
    """
    if not path_parts:
        return

    first_part = path_parts[0]
    remaining_parts = path_parts[1:]

    if first_part == "*":
        # Wildcard: process all items in current level
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and remaining_parts:
                    _process_path_with_wildcard(item, remaining_parts, key, encrypt)
        elif isinstance(data, dict):
            for item_key in data:
                if remaining_parts:
                    _process_path_with_wildcard(data[item_key], remaining_parts, key, encrypt)
    else:
        # Regular key
        if first_part in data:
            if remaining_parts:
                # More path parts to process
                _process_path_with_wildcard(data[first_part], remaining_parts, key, encrypt)
            else:
                # Final part: encrypt/decrypt the value
                current_value = data[first_part]
                if isinstance(current_value, str):
                    if encrypt:
                        data[first_part] = encrypt_value(current_value, key)
                    else:
                        data[first_part] = decrypt_value(current_value, key)


def encrypt_config_secrets(
    config_dict: dict,
    key: bytes,
    paths: list[str]
) -> dict:
    """Encrypt values at specified paths in a configuration dictionary.

    Recursively traverses the configuration dictionary and encrypts values
    at the specified paths. Supports wildcard (*) notation for array indices.

    Args:
        config_dict: The configuration dictionary to process
        key: The Fernet encryption key
        paths: List of dot-notation paths to encrypt (e.g., ["datasources.*.connection.password"])

    Returns:
        dict: A new dictionary with encrypted values

    Example:
        >>> key = generate_key()
        >>> config = {"db": {"password": "secret"}}
        >>> encrypted = encrypt_config_secrets(config, key, ["db.password"])
        >>> encrypted["db"]["password"] != "secret"
        True
    """
    result = deepcopy(config_dict)

    for path in paths:
        path_parts = path.split(".")
        _process_path_with_wildcard(result, path_parts, key, encrypt=True)

    return result


def decrypt_config_secrets(
    config_dict: dict,
    key: bytes,
    paths: list[str]
) -> dict:
    """Decrypt values at specified paths in a configuration dictionary.

    Recursively traverses the configuration dictionary and decrypts values
    at the specified paths. Supports wildcard (*) notation for array indices.

    Args:
        config_dict: The configuration dictionary to process
        key: The Fernet encryption key
        paths: List of dot-notation paths to decrypt (e.g., ["datasources.*.connection.password"])

    Returns:
        dict: A new dictionary with decrypted values

    Raises:
        SecurityError: If decryption fails for any value

    Example:
        >>> key = generate_key()
        >>> config = {"db": {"password": "secret"}}
        >>> encrypted = encrypt_config_secrets(config, key, ["db.password"])
        >>> decrypted = decrypt_config_secrets(encrypted, key, ["db.password"])
        >>> decrypted["db"]["password"]
        'secret'
    """
    result = deepcopy(config_dict)

    for path in paths:
        path_parts = path.split(".")
        _process_path_with_wildcard(result, path_parts, key, encrypt=False)

    return result

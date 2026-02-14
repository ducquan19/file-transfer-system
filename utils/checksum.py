import hashlib


def calculate_checksum(data: bytes) -> str:
    """
    Calculate MD5 checksum of the given binary data.

    Args:
        data: Binary data to calculate checksum for

    Returns:
        Hexadecimal string representation of the MD5 checksum
    """
    return hashlib.md5(data).hexdigest()


def is_valid_utf8(data: bytes) -> bool:
    """
    Check if the given binary data is valid UTF-8 encoded.

    Args:
        data: Binary data to validate

    Returns:
        True if data is valid UTF-8, False otherwise
    """
    try:
        data.decode('utf-8', 'strict')
        return True
    except UnicodeDecodeError:
        return False

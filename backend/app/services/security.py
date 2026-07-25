from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Protege una contraseña antes de almacenarla."""
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Compara una contraseña con su hash almacenado."""
    return password_hash.verify(password, stored_hash)


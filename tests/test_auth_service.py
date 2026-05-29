"""Tests for password hashing and JWT roundtrip."""
import pytest
from jose import jwt

from backend.app.security import hash_password, verify_password, create_access_token, decode_token
from backend.app.config import settings


def test_hash_is_not_plaintext():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert len(hashed) > 20


def test_verify_correct_password():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    token = create_access_token(user_id=42, role="admin")
    payload = decode_token(token)
    assert payload["user_id"] == 42
    assert payload["role"] == "admin"


def test_jwt_invalid_raises():
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token("this.is.not.valid")


def test_jwt_tampered_raises():
    token = create_access_token(user_id=1, role="user")
    tampered = token[:-5] + "XXXXX"
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token(tampered)

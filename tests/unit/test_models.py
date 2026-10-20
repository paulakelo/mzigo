"""Unit tests for PII phone number hashing."""

from backend.models import hash_phone


def test_phone_hashing_consistency():
    phone = "+254712345678"
    hash1 = hash_phone(phone)
    hash2 = hash_phone("0712345678")
    assert len(hash1) == 24
    assert len(hash2) == 24
    assert hash_phone(phone) == hash1

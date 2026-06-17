"""Signed connect-token roundtrip and tamper tests."""

from app.connect_token import make_token, verify_token

USER = "4309c607-0e7d-47c6-8b4f-57b58bdf7b66"


def test_roundtrip_recovers_user_id():
    assert verify_token(make_token(USER)) == USER


def test_token_is_url_safe_and_short():
    tok = make_token(USER)
    assert tok.isalnum() and len(tok) <= 64


def test_tampered_token_rejected():
    tok = make_token(USER)
    assert verify_token(tok[:-1] + ("0" if tok[-1] != "0" else "1")) is None


def test_wrong_length_rejected():
    assert verify_token("short") is None
    assert verify_token("") is None

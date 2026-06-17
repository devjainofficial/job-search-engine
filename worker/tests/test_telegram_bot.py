"""Tests for the Telegram webhook update parsing (pure, no network/DB)."""

from app.telegram_bot import parse_start_token


def test_parse_start_token_extracts_token():
    update = {"message": {"text": "/start abc123", "chat": {"id": 42}}}
    assert parse_start_token(update) == "abc123"


def test_plain_start_has_no_token():
    assert parse_start_token({"message": {"text": "/start", "chat": {"id": 1}}}) is None


def test_non_start_message_has_no_token():
    assert parse_start_token({"message": {"text": "hello", "chat": {"id": 1}}}) is None


def test_handles_missing_message():
    assert parse_start_token({}) is None


def test_token_with_extra_spaces():
    assert parse_start_token({"message": {"text": "/start   tok  "}}) == "tok"

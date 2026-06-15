"""Dedup logic tests. Per CLAUDE.md, write these before trusting the key."""

from app.canonical import (
    canonical_key,
    description_hash,
    normalize_title,
)


def test_same_job_across_sources_and_days_collapses():
    # Same posting, different boards, different scrape times -> one key.
    a = canonical_key("Acme Inc", "Software Engineer", "Remote", "Build cool things.")
    b = canonical_key("Acme Inc", "Software Engineer", "Remote", "Build cool things.")
    assert a == b


def test_case_whitespace_and_html_noise_do_not_change_key():
    clean = canonical_key("Acme", "Software Engineer", "Bangalore", "Build APIs.")
    noisy = canonical_key(
        "  ACME  ",
        "software   engineer",
        "BANGALORE",
        "<p>Build   APIs.</p>",
    )
    assert clean == noisy


def test_seniority_and_parens_normalize_away():
    base = normalize_title("Software Engineer")
    assert normalize_title("Sr. Software Engineer") == base
    assert normalize_title("Software Engineer (Remote)") == base
    assert normalize_title("Software Engineer III") == base


def test_different_companies_produce_different_keys():
    a = canonical_key("Acme", "Software Engineer", "Remote", "desc")
    b = canonical_key("Globex", "Software Engineer", "Remote", "desc")
    assert a != b


def test_different_descriptions_produce_different_keys():
    a = canonical_key("Acme", "Software Engineer", "Remote", "Work on payments.")
    b = canonical_key("Acme", "Software Engineer", "Remote", "Work on search infra.")
    assert a != b


def test_description_hash_is_stable_and_fixed_length():
    h1 = description_hash("Hello world")
    h2 = description_hash("hello   world")
    assert h1 == h2
    assert len(h1) == len(description_hash(""))


def test_empty_description_is_handled():
    key = canonical_key("Acme", "Engineer", "Remote", None)
    assert key.count("|") == 3

"""Location detection and ranking-boost tests."""

from app.geo import (
    IN_COUNTRY,
    OUT_COUNTRY,
    REMOTE,
    classify_location,
    is_india,
    is_remote,
    location_boost,
)


def test_classify_location_buckets():
    me = "Gandhinagar, Gujarat"
    assert classify_location("Bengaluru, India", me) == IN_COUNTRY
    assert classify_location("Remote", me) == REMOTE
    assert classify_location("San Francisco, CA", me) == OUT_COUNTRY


def test_remote_detection():
    assert is_remote("Remote")
    assert is_remote("Worldwide")
    assert is_remote("Anywhere (Global)")
    assert not is_remote("San Francisco, CA")


def test_india_detection():
    assert is_india("Bengaluru, India")
    assert is_india("Gandhinagar, Gujarat")
    assert is_india("Remote India")
    assert not is_india("Berlin, Germany")


def test_boost_prefers_remote_and_india_for_india_user():
    india_remote = location_boost("Remote", "Gandhinagar, Gujarat", "remote")
    foreign_onsite = location_boost("San Francisco, CA", "Gandhinagar, Gujarat", "remote")
    assert india_remote > foreign_onsite
    # India + remote should out-rank a plain foreign onsite role.
    assert location_boost("Bengaluru, India", "Gandhinagar", "any") > 0
    assert foreign_onsite == 0.0

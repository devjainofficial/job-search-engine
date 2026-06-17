"""Seniority inference and filtering tests."""

from app.seniority import ENTRY, INTERN, MID, SENIOR, job_level, seniority_ok


def test_job_level_inference():
    assert job_level("Software Engineer Intern") == INTERN
    assert job_level("Software Engineer, New Grad") == ENTRY
    assert job_level("Junior Backend Developer") == ENTRY
    assert job_level("Software Engineer") == MID
    assert job_level("Senior Software Engineer") == SENIOR
    assert job_level("Staff Software Engineer") == SENIOR


def test_unknown_experience_accepts_all():
    assert seniority_ok("Software Engineer Intern", None) is True


def test_experienced_user_drops_intern_and_newgrad():
    assert seniority_ok("Software Engineer Intern", 5) is False
    assert seniority_ok("Software Engineer, New Grad", 5) is False
    assert seniority_ok("Junior Developer", 5) is False
    assert seniority_ok("Senior Software Engineer", 5) is True
    assert seniority_ok("Software Engineer", 5) is True


def test_one_year_drops_only_internships():
    assert seniority_ok("Engineering Intern", 1) is False
    assert seniority_ok("Software Engineer, New Grad", 1) is True

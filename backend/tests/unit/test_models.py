"""Unit tests: Pydantic schema validation and business rules."""

import pytest
from pydantic import ValidationError


def test_person_create_valid_and_invalid(loader):
    models = loader("people", "models")
    person = models.PersonCreate(name="Ada", staff_type="DIRECT")
    assert person.name == "Ada"
    assert person.staff_type.value == "DIRECT"
    assert person.is_org_leader is False  # default

    with pytest.raises(ValidationError):
        models.PersonCreate(name="Ada", staff_type="BOGUS")   # bad enum
    with pytest.raises(ValidationError):
        models.PersonCreate(staff_type="DIRECT")              # missing name
    with pytest.raises(ValidationError):
        models.PersonCreate(name="Ada", staff_type="DIRECT", surprise="x")  # extra forbidden


def test_person_metadata_allows_extra_fields(loader):
    models = loader("people", "models")
    person = models.PersonCreate(
        name="Ada", staff_type="DIRECT",
        metadata={"employee_id": "E1", "team_color": "blue"},
    )
    dumped = person.model_dump(mode="json")
    assert dumped["metadata"]["employee_id"] == "E1"
    assert dumped["metadata"]["team_color"] == "blue"   # extra field preserved


def test_achievement_month_normalized_to_first(loader):
    models = loader("achievements", "models")
    ach = models.AchievementCreate(team_id="5c138c12-bae5-4d49-b0a9-784d3053cd41",
                                   month="2026-06-17", title="Shipped v1")
    assert str(ach.month) == "2026-06-01"


def test_user_create_requires_valid_role_and_email(loader):
    models = loader("auth", "models")
    user = models.UserCreate(email="a@b.co", password="longenough", role="MANAGER")
    assert user.role.value == "MANAGER"
    with pytest.raises(ValidationError):
        models.UserCreate(email="not-an-email", password="longenough", role="MANAGER")
    with pytest.raises(ValidationError):
        models.UserCreate(email="a@b.co", password="short", role="MANAGER")  # < 8 chars

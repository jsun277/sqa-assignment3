from datetime import date
from unittest.mock import patch

import pytest

from src.auth import AuthService
from src.drill_service import DrillService
from src.exceptions import (
    DuplicateUserException,
    InvalidCredentialsException,
    InvalidDrillDataException,
)
from src.models import Athlete, Category, Priority, Role


class DummyAlertService:
    def send(self, athlete, drill):
        pass


def test_athlete_can_create_drill(drill_service, athlete):
    # Category: Happy path
    # Arrange
    title = "Bag work"

    # Act
    drill = drill_service.create_drill(
        actor=athlete,
        title=title,
        description="5 rounds",
        priority=Priority.MEDIUM,
        due_date=date(2026, 7, 1),
        category=Category.TRAINING,
    )

    # Assert
    assert drill.title == title
    assert drill.owner_username == athlete.username


def test_login_returns_authenticated_user(auth_service):
    # Category: Happy path
    # Arrange
    auth_service.signup("fighter", "secret", Role.ATHLETE)

    # Act
    user = auth_service.login("fighter", "secret")

    # Assert
    assert user.username == "fighter"
    assert user.role is Role.ATHLETE


def test_drill_service_works_with_no_op_alert_service(auth_service, athlete):
    # Category: Happy path
    # Arrange
    dummy = DummyAlertService()
    service = DrillService(auth_service=auth_service, alert_service=dummy)
    drill = service.create_drill(
        actor=athlete,
        title="Shadow box",
        description="",
        priority=Priority.LOW,
        due_date=date(2026, 1, 1),
        category=Category.TRAINING,
        alert_enabled=True,
    )

    # Act
    triggered = service.trigger_alerts(today=date(2026, 5, 1))

    # Assert
    assert triggered == [drill]


def test_signup_with_duplicate_username_raises_exception(auth_service):
    # Category: Invalid input
    # Arrange
    auth_service.signup("duplicate", "pw", Role.ATHLETE)

    # Act / Assert
    with pytest.raises(DuplicateUserException):
        auth_service.signup("duplicate", "different", Role.ATHLETE)


def test_create_drill_with_empty_title_raises_exception(drill_service, athlete):
    # Category: Invalid input
    # Arrange
    empty_title = "   "

    # Act / Assert
    with pytest.raises(InvalidDrillDataException):
        drill_service.create_drill(
            actor=athlete,
            title=empty_title,
            description="x",
            priority=Priority.LOW,
            due_date=date(2026, 5, 1),
            category=Category.TRAINING,
        )


def test_login_with_wrong_password_raises_exception(auth_service):
    # Category: Invalid input
    # Arrange
    auth_service.signup("boxer", "rightpw", Role.ATHLETE)

    # Act / Assert
    with pytest.raises(InvalidCredentialsException):
        auth_service.login("boxer", "wrongpw")


def test_athlete_role_representative(auth_service):
    # Category: Equivalence class
    # Arrange
    user = auth_service.signup("rep_athlete", "pw", Role.ATHLETE)

    # Act
    role = user.role

    # Assert
    assert role is Role.ATHLETE
    assert isinstance(user, Athlete)


def test_login_always_returns_same_user_for_valid_credentials(auth_service):
    # Category: Equivalence class
    # Arrange
    stub_user = Athlete(
        username="stub_user",
        password_hash="ignored",
        role=Role.ATHLETE,
    )

    # Act
    with patch.object(AuthService, "login", return_value=stub_user) as stubbed_login:
        result_one = auth_service.login("any_username", "any_password")
        result_two = auth_service.login("other_username", "other_password")

    # Assert
    assert result_one is stub_user
    assert result_two is stub_user
    assert stubbed_login.call_count == 2

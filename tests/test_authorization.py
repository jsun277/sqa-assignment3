from datetime import date

import pytest

from src.exceptions import AthleteNotOnRosterException, UnauthorizedAccessException
from src.models import Category, Priority, Role


def test_coach_assigning_to_athlete_not_on_roster_raises_exception(
    drill_service, coach, auth_service
):
    # Category: Exception handling, Business logic
    # Arrange
    stranger = auth_service.signup("stranger", "pw", Role.ATHLETE)

    # Act / Assert
    with pytest.raises(AthleteNotOnRosterException):
        drill_service.create_drill(
            actor=coach,
            title="Unauthorized plan",
            description="",
            priority=Priority.LOW,
            due_date=date(2026, 6, 1),
            category=Category.TRAINING,
            owner_username=stranger.username,
        )


def test_athlete_cannot_view_another_athletes_drills(
    drill_service, athlete, other_athlete, sample_drill
):
    # Category: Business logic
    # Arrange
    expected = []

    # Act
    visible = drill_service.list_drills(other_athlete)

    # Assert
    assert visible == expected


def test_coach_can_view_all_drills_for_roster_athlete(
    drill_service, coach, athlete
):
    # Category: Business logic, Happy path
    # Arrange
    first = drill_service.create_drill(
        actor=athlete,
        title="Sparring",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    second = drill_service.create_drill(
        actor=athlete,
        title="Stretching",
        description="",
        priority=Priority.LOW,
        due_date=date(2026, 6, 2),
        category=Category.RECOVERY,
    )

    # Act
    visible = drill_service.list_drills(coach)

    # Assert
    assert sorted(d.drill_id for d in visible) == sorted(
        [first.drill_id, second.drill_id]
    )

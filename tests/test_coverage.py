from datetime import date

import pytest

from src.alert_service import InMemoryAlertService
from src.exceptions import (
    InvalidCredentialsException,
    InvalidDrillDataException,
    InvalidRoleException,
)
from src.kis import KIS
from src.models import Category, Priority, Role


def test_kis_facade_end_to_end_drives_every_pass_through():
    # Category: Happy path, Business logic
    # Arrange
    recorder = InMemoryAlertService()
    facade = KIS(alert_service=recorder)
    athlete = facade.signup("ath", "pw", Role.ATHLETE)
    facade.signup("coach", "pw", Role.COACH)
    facade.assign_athlete_to_coach("coach", "ath")
    facade.login("ath", "pw")

    # Act
    drill = facade.create_drill(
        actor=athlete,
        title="Sprint",
        description="Track work",
        priority=Priority.HIGH,
        due_date=date(2026, 1, 1),
        category=Category.TRAINING,
        alert_enabled=True,
    )
    fetched = facade.get_drill(athlete, drill.drill_id)
    listed = facade.list_drills(athlete)
    facade.set_alert(athlete, drill.drill_id, True)
    sorted_drills = facade.sort_drills([drill], by="priority")
    filtered = facade.filter_drills([drill], category=Category.TRAINING)
    triggered = facade.trigger_alerts(today=date(2026, 6, 1))
    facade.trigger_alert_for(athlete, drill.drill_id)
    facade.mark_complete(athlete, drill.drill_id)
    facade.mark_incomplete(athlete, drill.drill_id)
    facade.toggle_completion(athlete, drill.drill_id)
    facade.delete_drill(athlete, drill.drill_id)

    # Assert
    assert fetched is drill
    assert listed == [drill]
    assert sorted_drills == [drill]
    assert filtered == [drill]
    assert triggered == [drill]
    assert facade.list_drills(athlete) == []
    assert len(recorder.sent) == 2


def test_update_drill_changes_every_field(drill_service, athlete, sample_drill):
    # Category: Happy path
    # Arrange
    new_date = date(2026, 12, 1)

    # Act
    updated = drill_service.update_drill(
        actor=athlete,
        drill_id=sample_drill.drill_id,
        title="New title",
        description="New desc",
        priority=Priority.LOW,
        due_date=new_date,
        category=Category.ADMIN,
        alert_enabled=True,
    )

    # Assert
    assert (
        updated.title,
        updated.description,
        updated.priority,
        updated.due_date,
        updated.category,
        updated.alert_enabled,
    ) == ("New title", "New desc", Priority.LOW, new_date, Category.ADMIN, True)


def test_update_drill_rejects_invalid_fields(drill_service, athlete, sample_drill):
    # Category: Invalid input
    # Arrange
    drill_id = sample_drill.drill_id

    # Act / Assert
    with pytest.raises(InvalidDrillDataException):
        drill_service.update_drill(actor=athlete, drill_id=drill_id, title="   ")
    with pytest.raises(InvalidDrillDataException):
        drill_service.update_drill(actor=athlete, drill_id=drill_id, priority="HIGH")
    with pytest.raises(InvalidDrillDataException):
        drill_service.update_drill(actor=athlete, drill_id=drill_id, due_date="soon")
    with pytest.raises(InvalidDrillDataException):
        drill_service.update_drill(actor=athlete, drill_id=drill_id, category="T")


def test_filter_drills_by_completion_status(drill_service, athlete):
    # Category: Business logic
    # Arrange
    done = drill_service.create_drill(
        actor=athlete,
        title="Done",
        description="",
        priority=Priority.LOW,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    pending = drill_service.create_drill(
        actor=athlete,
        title="Pending",
        description="",
        priority=Priority.LOW,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    drill_service.mark_complete(actor=athlete, drill_id=done.drill_id)

    # Act
    completed = drill_service.filter_drills([done, pending], completed=True)
    incomplete = drill_service.filter_drills([done, pending], completed=False)

    # Assert
    assert completed == [done]
    assert incomplete == [pending]


def test_trigger_alerts_skips_disabled_and_not_overdue(
    drill_service, alert_recorder, athlete
):
    # Category: Business logic, Boundary / Edge
    # Arrange
    drill_service.create_drill(
        actor=athlete,
        title="Disabled",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 1, 1),
        category=Category.TRAINING,
        alert_enabled=False,
    )
    drill_service.create_drill(
        actor=athlete,
        title="Future",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 12, 31),
        category=Category.TRAINING,
        alert_enabled=True,
    )

    # Act
    triggered = drill_service.trigger_alerts(today=date(2026, 5, 1))

    # Assert
    assert triggered == []
    assert alert_recorder.sent == []


def test_input_validation_paths(drill_service, auth_service, athlete, coach):
    # Category: Invalid input
    # Arrange
    bad_date = "2026-01-01"

    # Act / Assert
    with pytest.raises(InvalidCredentialsException):
        auth_service.signup("", "pw", Role.ATHLETE)
    with pytest.raises(InvalidRoleException):
        auth_service.signup("u", "pw", "ATHLETE")
    with pytest.raises(InvalidDrillDataException):
        drill_service.create_drill(
            actor=athlete, title="x", description="", priority="HIGH",
            due_date=date(2026, 6, 1), category=Category.TRAINING,
        )
    with pytest.raises(InvalidDrillDataException):
        drill_service.create_drill(
            actor=athlete, title="x", description="", priority=Priority.LOW,
            due_date=bad_date, category=Category.TRAINING,
        )
    with pytest.raises(InvalidDrillDataException):
        drill_service.create_drill(
            actor=coach, title="x", description="", priority=Priority.LOW,
            due_date=date(2026, 6, 1), category=Category.TRAINING,
            owner_username=None,
        )
    with pytest.raises(InvalidDrillDataException):
        drill_service.sort_drills([], by="garbage_key")


def test_auth_role_helpers_reject_wrong_role(auth_service):
    # Category: Exception handling
    # Arrange
    auth_service.signup("an_athlete", "pw", Role.ATHLETE)
    auth_service.signup("a_coach", "pw", Role.COACH)

    # Act / Assert
    with pytest.raises(InvalidRoleException):
        auth_service.get_coach("an_athlete")
    with pytest.raises(InvalidRoleException):
        auth_service.get_athlete("a_coach")

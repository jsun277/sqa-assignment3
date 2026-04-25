from datetime import date

import pytest

from src.exceptions import DrillNotFoundException, UnauthorizedAccessException
from src.models import Category, Priority


def test_coach_can_assign_drill_to_athlete(drill_service, coach, athlete):
    # Category: Happy path
    # Arrange
    title = "Recovery swim"

    # Act
    drill = drill_service.create_drill(
        actor=coach,
        title=title,
        description="30 min easy",
        priority=Priority.LOW,
        due_date=date(2026, 6, 10),
        category=Category.RECOVERY,
        owner_username=athlete.username,
    )

    # Assert
    assert drill.owner_username == athlete.username
    assert drill.title == title


def test_athlete_can_mark_drill_complete(drill_service, athlete, sample_drill):
    # Category: Happy path
    # Arrange
    drill_id = sample_drill.drill_id

    # Act
    updated = drill_service.mark_complete(actor=athlete, drill_id=drill_id)

    # Assert
    assert updated.completion_status is True


def test_drills_sorted_by_priority(drill_service, athlete):
    # Category: Happy path, Business logic
    # Arrange
    low = drill_service.create_drill(
        actor=athlete,
        title="Stretching",
        description="",
        priority=Priority.LOW,
        due_date=date(2026, 6, 1),
        category=Category.RECOVERY,
    )
    high = drill_service.create_drill(
        actor=athlete,
        title="Sparring",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 6, 2),
        category=Category.TRAINING,
    )
    medium = drill_service.create_drill(
        actor=athlete,
        title="Film review",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 3),
        category=Category.ADMIN,
    )

    # Act
    sorted_drills = drill_service.sort_drills([low, high, medium], by="priority")

    # Assert
    assert sorted_drills == [high, medium, low]


def test_filter_drills_by_category(drill_service, athlete):
    # Category: Happy path, Business logic
    # Arrange
    training = drill_service.create_drill(
        actor=athlete,
        title="Bag",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    drill_service.create_drill(
        actor=athlete,
        title="Physio",
        description="",
        priority=Priority.LOW,
        due_date=date(2026, 6, 1),
        category=Category.MEDICAL,
    )

    # Act
    all_drills = drill_service.list_drills(athlete)
    filtered = drill_service.filter_drills(all_drills, category=Category.TRAINING)

    # Assert
    assert filtered == [training]


def test_set_reminder_on_nonexistent_drill_raises_exception(drill_service, athlete):
    # Category: Invalid input
    # Arrange
    missing_id = 9999

    # Act / Assert
    with pytest.raises(DrillNotFoundException):
        drill_service.set_alert(actor=athlete, drill_id=missing_id, enabled=True)


def test_filter_drills_returns_empty_list_when_no_match(drill_service, athlete):
    # Category: Boundary / Edge
    # Arrange
    drill_service.create_drill(
        actor=athlete,
        title="Bag",
        description="heavy bag",
        priority=Priority.HIGH,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    all_drills = drill_service.list_drills(athlete)

    # Act
    filtered = drill_service.filter_drills(all_drills, keyword="basketball")

    # Assert
    assert filtered == []


def test_sort_drills_when_list_has_single_drill(drill_service, sample_drill):
    # Category: Boundary / Edge
    # Arrange
    single = [sample_drill]

    # Act
    result = drill_service.sort_drills(single, by="priority")

    # Assert
    assert result == [sample_drill]


def test_drills_with_same_priority_stable_sort(drill_service, athlete):
    # Category: Boundary / Edge
    # Arrange
    first = drill_service.create_drill(
        actor=athlete,
        title="A",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    second = drill_service.create_drill(
        actor=athlete,
        title="B",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 2),
        category=Category.TRAINING,
    )
    third = drill_service.create_drill(
        actor=athlete,
        title="C",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 3),
        category=Category.TRAINING,
    )

    # Act
    sorted_drills = drill_service.sort_drills([first, second, third], by="priority")

    # Assert
    assert sorted_drills == [first, second, third]


def test_mark_complete_on_already_completed_drill(drill_service, athlete, sample_drill):
    # Category: Boundary / Edge
    # Arrange
    drill_service.mark_complete(actor=athlete, drill_id=sample_drill.drill_id)

    # Act
    updated = drill_service.mark_complete(actor=athlete, drill_id=sample_drill.drill_id)

    # Assert
    assert updated.completion_status is True


def test_high_priority_drill_representative(drill_service, athlete):
    # Category: Equivalence class
    # Arrange
    title = "Championship sparring"

    # Act
    drill = drill_service.create_drill(
        actor=athlete,
        title=title,
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )

    # Assert
    assert drill.priority is Priority.HIGH


def test_medical_category_drill_representative(drill_service, athlete):
    # Category: Equivalence class
    # Arrange
    title = "MRI follow-up"

    # Act
    drill = drill_service.create_drill(
        actor=athlete,
        title=title,
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 6, 1),
        category=Category.MEDICAL,
    )

    # Assert
    assert drill.category is Category.MEDICAL


def test_delete_nonexistent_drill_raises_drill_not_found(drill_service, athlete):
    # Category: Exception handling
    # Arrange
    missing_id = 424242

    # Act / Assert
    with pytest.raises(DrillNotFoundException):
        drill_service.delete_drill(actor=athlete, drill_id=missing_id)


def test_athlete_accessing_another_athletes_drill_raises_unauthorized(
    drill_service, athlete, other_athlete, sample_drill
):
    # Category: Exception handling, Business logic
    # Arrange
    drill_id = sample_drill.drill_id

    # Act / Assert
    with pytest.raises(UnauthorizedAccessException):
        drill_service.get_drill(actor=other_athlete, drill_id=drill_id)


def test_drills_sorted_by_due_date_ascending(drill_service, athlete):
    # Category: Business logic
    # Arrange
    later = drill_service.create_drill(
        actor=athlete,
        title="Later",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 8, 1),
        category=Category.TRAINING,
    )
    earlier = drill_service.create_drill(
        actor=athlete,
        title="Earlier",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 5, 1),
        category=Category.TRAINING,
    )
    middle = drill_service.create_drill(
        actor=athlete,
        title="Middle",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 7, 1),
        category=Category.TRAINING,
    )

    # Act
    sorted_drills = drill_service.sort_drills([later, earlier, middle], by="due_date")

    # Assert
    assert sorted_drills == [earlier, middle, later]


def test_keyword_search_matches_title_and_description(drill_service, athlete):
    # Category: Business logic
    # Arrange
    in_title = drill_service.create_drill(
        actor=athlete,
        title="Footwork ladder",
        description="agility cones",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 1),
        category=Category.TRAINING,
    )
    in_description = drill_service.create_drill(
        actor=athlete,
        title="Conditioning",
        description="Heavy footwork intervals",
        priority=Priority.MEDIUM,
        due_date=date(2026, 6, 2),
        category=Category.TRAINING,
    )
    drill_service.create_drill(
        actor=athlete,
        title="Recovery swim",
        description="cool down",
        priority=Priority.LOW,
        due_date=date(2026, 6, 3),
        category=Category.RECOVERY,
    )

    # Act
    matches = drill_service.filter_drills(
        drill_service.list_drills(athlete),
        keyword="footwork",
    )

    # Assert
    assert sorted(d.drill_id for d in matches) == sorted(
        [in_title.drill_id, in_description.drill_id]
    )

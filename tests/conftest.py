from datetime import date

import pytest

from src.alert_service import InMemoryAlertService
from src.auth import AuthService
from src.drill_service import DrillService
from src.kis import KIS
from src.models import Category, Priority, Role


@pytest.fixture
def auth_service():
    return AuthService()


@pytest.fixture
def alert_recorder():
    return InMemoryAlertService()


@pytest.fixture
def drill_service(auth_service, alert_recorder):
    return DrillService(auth_service=auth_service, alert_service=alert_recorder)


@pytest.fixture
def kis():
    return KIS()


@pytest.fixture
def athlete(auth_service):
    return auth_service.signup("ath1", "pw123", Role.ATHLETE)


@pytest.fixture
def other_athlete(auth_service):
    return auth_service.signup("ath2", "pw456", Role.ATHLETE)


@pytest.fixture
def coach(auth_service, athlete):
    created = auth_service.signup("coach1", "pwcoach", Role.COACH)
    created.add_to_roster(athlete.username)
    return created


@pytest.fixture
def sample_due_date():
    return date(2026, 6, 1)


@pytest.fixture
def sample_drill(drill_service, athlete, sample_due_date):
    return drill_service.create_drill(
        actor=athlete,
        title="Sprints",
        description="Hill sprints at dawn",
        priority=Priority.HIGH,
        due_date=sample_due_date,
        category=Category.TRAINING,
    )

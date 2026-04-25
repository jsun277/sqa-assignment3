from datetime import date
from unittest.mock import MagicMock

from src.drill_service import DrillService
from src.models import Category, Priority


class SpyAlertService:
    def __init__(self):
        self.call_count = 0
        self.last_athlete = None
        self.last_drill = None

    def send(self, athlete, drill):
        self.call_count += 1
        self.last_athlete = athlete
        self.last_drill = drill


class FakeAlertService:
    def __init__(self):
        self.alerts_by_athlete = {}

    def send(self, athlete, drill):
        self.alerts_by_athlete.setdefault(athlete.username, []).append(drill)

    def alerts_for(self, username):
        return list(self.alerts_by_athlete.get(username, []))


def test_risk_alert_triggered_when_reminder_set(auth_service, athlete):
    # Category: Business logic
    # Arrange
    spy = SpyAlertService()
    service = DrillService(auth_service=auth_service, alert_service=spy)
    drill = service.create_drill(
        actor=athlete,
        title="Overdue sprint",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 1, 1),
        category=Category.TRAINING,
        alert_enabled=True,
    )

    # Act
    service.trigger_alerts(today=date(2026, 5, 1))

    # Assert
    assert spy.call_count == 1
    assert spy.last_drill is drill


def test_alert_service_called_with_correct_athlete_and_drill(auth_service, athlete):
    # Category: Business logic
    # Arrange
    mock_alerts = MagicMock()
    service = DrillService(auth_service=auth_service, alert_service=mock_alerts)
    drill = service.create_drill(
        actor=athlete,
        title="Conditioning",
        description="",
        priority=Priority.MEDIUM,
        due_date=date(2026, 1, 15),
        category=Category.TRAINING,
        alert_enabled=True,
    )

    # Act
    service.trigger_alerts(today=date(2026, 5, 1))

    # Assert
    mock_alerts.send.assert_called_once_with(athlete, drill)


def test_multiple_athletes_alerts_isolated(auth_service):
    # Category: Business logic
    # Arrange
    fake = FakeAlertService()
    service = DrillService(auth_service=auth_service, alert_service=fake)
    from src.models import Role

    ath_a = auth_service.signup("alpha", "pw", Role.ATHLETE)
    ath_b = auth_service.signup("bravo", "pw", Role.ATHLETE)
    drill_a = service.create_drill(
        actor=ath_a,
        title="Alpha drill",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 1, 1),
        category=Category.TRAINING,
        alert_enabled=True,
    )
    drill_b = service.create_drill(
        actor=ath_b,
        title="Bravo drill",
        description="",
        priority=Priority.HIGH,
        due_date=date(2026, 1, 1),
        category=Category.TRAINING,
        alert_enabled=True,
    )

    # Act
    service.trigger_alerts(today=date(2026, 5, 1))

    # Assert
    assert fake.alerts_for("alpha") == [drill_a]
    assert fake.alerts_for("bravo") == [drill_b]

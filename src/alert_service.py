"""Alert delivery abstraction.

The KIS domain layer must never reach the network or any concrete notification
backend on its own. Instead, drill services accept anything that satisfies the
:class:`AlertService` protocol, and call ``send`` when a risk alert fires. Tests
substitute a fake recorder; production code can plug in an SMS, email, or push
adapter without touching the domain.
"""

from __future__ import annotations

from typing import List, Protocol, Tuple

from .models import Athlete, Drill


class AlertService(Protocol):
    """Protocol every alert backend must satisfy.

    Implementations should treat ``send`` as a fire-and-forget side effect.
    Returning normally signals success; raising propagates to the caller.
    """

    def send(self, athlete: Athlete, drill: Drill) -> None:
        """Deliver a risk alert about ``drill`` to ``athlete``."""
        ...


class NoOpAlertService:
    """Default :class:`AlertService` implementation that swallows every alert.

    Used by :class:`~src.kis.KIS` when the caller does not supply an alert
    backend. Keeps domain code exercisable without configuring delivery.
    """

    def send(self, athlete: Athlete, drill: Drill) -> None:
        """Do nothing. Provided so the protocol is satisfied."""
        return None


class InMemoryAlertService:
    """Simple :class:`AlertService` that records every alert in a list.

    Useful as a development default and as a reference implementation for tests
    that need to assert on what was sent without writing a custom mock.
    """

    def __init__(self) -> None:
        """Initialize the recorder with an empty event log."""
        self.sent: List[Tuple[str, int]] = []

    def send(self, athlete: Athlete, drill: Drill) -> None:
        """Record a (username, drill_id) tuple for the alert that fired."""
        self.sent.append((athlete.username, drill.drill_id))

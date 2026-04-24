"""Domain models and enumerations for the KIS system.

This module defines the data shapes used throughout the rest of the domain
layer: the :class:`Role`, :class:`Priority`, and :class:`Category` enums, the
:class:`User` hierarchy (:class:`Athlete`, :class:`Coach`), and the
:class:`Drill` task unit. Models are plain dataclasses — they hold state and
expose small helpers, but business rules and authorization live in the service
layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional


class Role(Enum):
    """The two roles a KIS user can hold."""

    ATHLETE = "ATHLETE"
    COACH = "COACH"


class Priority(Enum):
    """Priority levels for a drill, ordered from least to most urgent."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Category(Enum):
    """The fixed set of categories a drill can belong to."""

    TRAINING = "TRAINING"
    RECOVERY = "RECOVERY"
    MEDICAL = "MEDICAL"
    ADMIN = "ADMIN"


@dataclass
class User:
    """Base class for all KIS users.

    Attributes:
        username: The unique identifier the user logs in with.
        password_hash: A stored password representation. The auth layer treats
            this opaquely — it may be a real hash or a stub for testing.
        role: The :class:`Role` this user holds.
    """

    username: str
    password_hash: str
    role: Role


@dataclass
class Athlete(User):
    """An athlete user. Owns drills and can manage their own task list."""

    def __post_init__(self) -> None:
        """Force the role to ATHLETE regardless of what was passed in."""
        self.role = Role.ATHLETE


@dataclass
class Coach(User):
    """A coach user. Manages a roster of athletes and assigns them drills.

    Attributes:
        roster: Usernames of the athletes this coach is responsible for.
    """

    roster: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Force the role to COACH regardless of what was passed in."""
        self.role = Role.COACH

    def add_to_roster(self, athlete_username: str) -> None:
        """Add an athlete username to this coach's roster if not already present.

        Args:
            athlete_username: The athlete's unique username.
        """
        if athlete_username not in self.roster:
            self.roster.append(athlete_username)

    def has_on_roster(self, athlete_username: str) -> bool:
        """Return True if the given athlete is on this coach's roster."""
        return athlete_username in self.roster


@dataclass
class Drill:
    """A single training/recovery/admin task assigned to an athlete.

    Attributes:
        drill_id: A stable identifier assigned by :class:`DrillService`.
        title: Short human-readable title.
        description: Longer free-form description.
        priority: A :class:`Priority` value.
        due_date: The date by which the drill should be completed.
        category: A :class:`Category` value.
        owner_username: The username of the athlete who owns this drill.
        completion_status: True when the athlete has marked the drill done.
        alert_enabled: True when a risk alert should fire if the drill is
            overdue. The actual delivery is handled by an injected
            ``AlertService`` — this flag only records intent.
    """

    drill_id: int
    title: str
    description: str
    priority: Priority
    due_date: date
    category: Category
    owner_username: str
    completion_status: bool = False
    alert_enabled: bool = False

    def is_overdue(self, today: Optional[date] = None) -> bool:
        """Return True if the drill is past its due date and still incomplete.

        Args:
            today: The reference date to compare against. Defaults to
                :func:`datetime.date.today` — callers (and tests) may override
                it to keep behavior deterministic.
        """
        reference = today or date.today()
        return (not self.completion_status) and self.due_date < reference

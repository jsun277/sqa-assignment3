"""Drill CRUD, sorting, filtering, completion, and risk-alert dispatch.

:class:`DrillService` is the heart of the domain. It owns the in-memory drill
store, enforces ownership/roster authorization on every mutation, and dispatches
risk alerts through the injected :class:`AlertService`. It does not know about
HTTP, persistence, or logging — those are someone else's problem.
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, Iterable, List, Optional

from .alert_service import AlertService
from .auth import AuthService
from .exceptions import (
    AthleteNotOnRosterException,
    DrillNotFoundException,
    InvalidDrillDataException,
    UnauthorizedAccessException,
)
from .models import Athlete, Category, Coach, Drill, Priority, Role, User


# ---------------------------------------------------------------------------
# Sort key helpers
# ---------------------------------------------------------------------------

SortKey = Callable[[Drill], object]

_SORT_KEYS: Dict[str, SortKey] = {
    # Higher priority first.
    "priority": lambda d: -d.priority.value,
    # Earliest due date first.
    "due_date": lambda d: d.due_date,
    # Incomplete drills first (False sorts before True).
    "completion_status": lambda d: d.completion_status,
}


class DrillService:
    """Manage the lifecycle of every :class:`Drill` in the system."""

    def __init__(self, auth_service: AuthService, alert_service: AlertService) -> None:
        """Store the collaborators and initialize an empty drill table.

        Args:
            auth_service: Used to resolve usernames into users and to verify
                roster membership when a coach acts on an athlete's drill.
            alert_service: Injected delivery backend for risk alerts. Anything
                satisfying the :class:`AlertService` protocol is acceptable.
        """
        self._auth = auth_service
        self._alerts = alert_service
        self._drills: Dict[int, Drill] = {}
        self._next_id: int = 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _allocate_id(self) -> int:
        """Return the next available drill id and advance the counter."""
        drill_id = self._next_id
        self._next_id += 1
        return drill_id

    def _get_drill_or_raise(self, drill_id: int) -> Drill:
        """Return the drill with ``drill_id`` or raise :class:`DrillNotFoundException`."""
        drill = self._drills.get(drill_id)
        if drill is None:
            raise DrillNotFoundException(f"No drill with id {drill_id}.")
        return drill

    def _authorize(self, actor: User, drill: Drill) -> None:
        """Raise :class:`UnauthorizedAccessException` if ``actor`` cannot touch ``drill``.

        Athletes may only act on drills they own. Coaches may act on drills
        owned by any athlete on their roster. Anything else is rejected.
        """
        if isinstance(actor, Athlete):
            if drill.owner_username != actor.username:
                raise UnauthorizedAccessException(
                    f"Athlete '{actor.username}' cannot access drill {drill.drill_id}."
                )
            return

        if isinstance(actor, Coach):
            if not actor.has_on_roster(drill.owner_username):
                raise UnauthorizedAccessException(
                    f"Coach '{actor.username}' has no roster authority over "
                    f"athlete '{drill.owner_username}'."
                )
            return

        raise UnauthorizedAccessException(
            f"User '{actor.username}' has an unsupported role for this action."
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_drill(
        self,
        actor: User,
        title: str,
        description: str,
        priority: Priority,
        due_date: date,
        category: Category,
        owner_username: Optional[str] = None,
        alert_enabled: bool = False,
    ) -> Drill:
        """Create and store a new drill.

        Args:
            actor: The user performing the creation. Athletes implicitly own
                the new drill. Coaches must supply ``owner_username`` and the
                target athlete must be on their roster.
            title: Required, non-blank.
            description: Free-form text. May be empty.
            priority: A :class:`Priority` value.
            due_date: A :class:`datetime.date` value.
            category: A :class:`Category` value.
            owner_username: Required when ``actor`` is a :class:`Coach`.
                Ignored when the actor is an :class:`Athlete`.
            alert_enabled: Initial state for the drill's risk-alert flag.

        Returns:
            The newly stored :class:`Drill`.

        Raises:
            InvalidDrillDataException: If validation fails.
            AthleteNotOnRosterException: If a coach targets an athlete that is
                not on their roster.
            UnauthorizedAccessException: If the actor's role is unsupported.
        """
        if not title or not title.strip():
            raise InvalidDrillDataException("Drill title must be non-empty.")
        if not isinstance(priority, Priority):
            raise InvalidDrillDataException(
                f"priority must be a Priority enum, got {type(priority).__name__}."
            )
        if not isinstance(category, Category):
            raise InvalidDrillDataException(
                f"category must be a Category enum, got {type(category).__name__}."
            )
        if not isinstance(due_date, date):
            raise InvalidDrillDataException(
                f"due_date must be a date, got {type(due_date).__name__}."
            )

        resolved_owner = self._resolve_owner(actor, owner_username)

        drill = Drill(
            drill_id=self._allocate_id(),
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category=category,
            owner_username=resolved_owner,
            alert_enabled=alert_enabled,
        )
        self._drills[drill.drill_id] = drill
        return drill

    def _resolve_owner(self, actor: User, owner_username: Optional[str]) -> str:
        """Decide the owner username for a new drill, enforcing role rules."""
        if isinstance(actor, Athlete):
            return actor.username

        if isinstance(actor, Coach):
            if not owner_username:
                raise InvalidDrillDataException(
                    "Coaches must specify owner_username when creating a drill."
                )
            if not actor.has_on_roster(owner_username):
                raise AthleteNotOnRosterException(
                    f"Athlete '{owner_username}' is not on coach "
                    f"'{actor.username}'s roster."
                )
            # Make sure the target user actually exists and is an athlete.
            self._auth.get_athlete(owner_username)
            return owner_username

        raise UnauthorizedAccessException(
            f"User '{actor.username}' has an unsupported role for this action."
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_drill(self, actor: User, drill_id: int) -> Drill:
        """Return the drill with ``drill_id`` if ``actor`` is allowed to see it.

        Raises:
            DrillNotFoundException: If no drill with that id exists.
            UnauthorizedAccessException: If the actor cannot access the drill.
        """
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        return drill

    def list_drills(self, actor: User) -> List[Drill]:
        """Return every drill ``actor`` is allowed to see.

        Athletes see only their own drills. Coaches see drills for every
        athlete on their roster.
        """
        return [d for d in self._drills.values() if self._can_view(actor, d)]

    def _can_view(self, actor: User, drill: Drill) -> bool:
        """Return True if ``actor`` is allowed to view ``drill``."""
        try:
            self._authorize(actor, drill)
        except UnauthorizedAccessException:
            return False
        return True

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_drill(
        self,
        actor: User,
        drill_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[date] = None,
        category: Optional[Category] = None,
        alert_enabled: Optional[bool] = None,
    ) -> Drill:
        """Update one or more fields on an existing drill.

        Only the fields explicitly passed in are changed. Authorization is
        enforced before any mutation occurs. Validation errors do not partially
        update the drill.

        Returns:
            The updated :class:`Drill`.

        Raises:
            DrillNotFoundException: If the drill does not exist.
            UnauthorizedAccessException: If the actor cannot mutate the drill.
            InvalidDrillDataException: If any provided field is invalid.
        """
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)

        if title is not None:
            if not title.strip():
                raise InvalidDrillDataException("Drill title must be non-empty.")
            drill.title = title
        if description is not None:
            drill.description = description
        if priority is not None:
            if not isinstance(priority, Priority):
                raise InvalidDrillDataException(
                    f"priority must be a Priority enum, got {type(priority).__name__}."
                )
            drill.priority = priority
        if due_date is not None:
            if not isinstance(due_date, date):
                raise InvalidDrillDataException(
                    f"due_date must be a date, got {type(due_date).__name__}."
                )
            drill.due_date = due_date
        if category is not None:
            if not isinstance(category, Category):
                raise InvalidDrillDataException(
                    f"category must be a Category enum, got {type(category).__name__}."
                )
            drill.category = category
        if alert_enabled is not None:
            drill.alert_enabled = bool(alert_enabled)

        return drill

    def mark_complete(self, actor: User, drill_id: int) -> Drill:
        """Mark ``drill_id`` as complete and return the updated drill."""
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        drill.completion_status = True
        return drill

    def mark_incomplete(self, actor: User, drill_id: int) -> Drill:
        """Mark ``drill_id`` as incomplete and return the updated drill."""
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        drill.completion_status = False
        return drill

    def toggle_completion(self, actor: User, drill_id: int) -> Drill:
        """Flip the completion status of ``drill_id`` and return the drill."""
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        drill.completion_status = not drill.completion_status
        return drill

    def set_alert(self, actor: User, drill_id: int, enabled: bool) -> Drill:
        """Enable or disable the risk-alert flag on a drill."""
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        drill.alert_enabled = bool(enabled)
        return drill

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_drill(self, actor: User, drill_id: int) -> None:
        """Delete the drill with ``drill_id`` after authorizing ``actor``.

        Raises:
            DrillNotFoundException: If the drill does not exist.
            UnauthorizedAccessException: If the actor cannot mutate the drill.
        """
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        del self._drills[drill_id]

    # ------------------------------------------------------------------
    # Sort / filter
    # ------------------------------------------------------------------

    def sort_drills(
        self,
        drills: Iterable[Drill],
        by: str,
    ) -> List[Drill]:
        """Return ``drills`` sorted by the named field.

        Args:
            drills: Any iterable of :class:`Drill` instances.
            by: One of ``"priority"``, ``"due_date"``, or
                ``"completion_status"``.

        Raises:
            InvalidDrillDataException: If ``by`` is not a recognized sort key.
        """
        key = _SORT_KEYS.get(by)
        if key is None:
            raise InvalidDrillDataException(
                f"Unknown sort key '{by}'. "
                f"Expected one of: {sorted(_SORT_KEYS)}."
            )
        return sorted(drills, key=key)

    def filter_drills(
        self,
        drills: Iterable[Drill],
        *,
        category: Optional[Category] = None,
        keyword: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> List[Drill]:
        """Return the subset of ``drills`` matching every supplied filter.

        Args:
            drills: Any iterable of :class:`Drill` instances.
            category: If provided, only drills with this category are kept.
            keyword: If provided, only drills whose title or description
                contains the substring (case-insensitive) are kept.
            completed: If provided, only drills with this completion status
                are kept.
        """
        kw = keyword.lower().strip() if keyword else None

        result: List[Drill] = []
        for drill in drills:
            if category is not None and drill.category is not category:
                continue
            if completed is not None and drill.completion_status is not completed:
                continue
            if kw:
                haystack = f"{drill.title} {drill.description}".lower()
                if kw not in haystack:
                    continue
            result.append(drill)
        return result

    # ------------------------------------------------------------------
    # Risk alerts
    # ------------------------------------------------------------------

    def trigger_alerts(self, today: Optional[date] = None) -> List[Drill]:
        """Send a risk alert for every overdue, alert-enabled drill.

        For each matching drill, the injected :class:`AlertService` is invoked
        with the owning athlete and the drill itself. Athletes whose accounts
        have been removed are silently skipped — no alert is sent and no error
        is raised.

        Args:
            today: Reference date used to decide whether a drill is overdue.
                Defaults to :func:`datetime.date.today`. Tests should pass an
                explicit value to keep behavior deterministic.

        Returns:
            The list of drills for which an alert was actually dispatched.
        """
        reference = today or date.today()
        triggered: List[Drill] = []
        for drill in self._drills.values():
            if not drill.alert_enabled:
                continue
            if not drill.is_overdue(reference):
                continue
            owner = self._auth.find(drill.owner_username)
            if not isinstance(owner, Athlete):
                continue
            self._alerts.send(owner, drill)
            triggered.append(drill)
        return triggered

    def trigger_alert_for(self, actor: User, drill_id: int) -> Drill:
        """Force-send an alert for a single drill, regardless of due date.

        Useful for manual reminders. Authorization is enforced just like any
        other drill mutation.

        Raises:
            DrillNotFoundException: If the drill does not exist.
            UnauthorizedAccessException: If the actor cannot access the drill.
            InvalidDrillDataException: If the drill's owner is no longer
                registered as an athlete.
        """
        drill = self._get_drill_or_raise(drill_id)
        self._authorize(actor, drill)
        owner = self._auth.find(drill.owner_username)
        if not isinstance(owner, Athlete):
            raise InvalidDrillDataException(
                f"Drill {drill_id} owner '{drill.owner_username}' is not a "
                f"registered athlete."
            )
        self._alerts.send(owner, drill)
        return drill

"""KIS — Kinetic Intelligence System domain layer.

Public re-exports for convenience. Callers should import from :mod:`src`
rather than reaching into individual submodules.
"""

from .alert_service import AlertService, InMemoryAlertService, NoOpAlertService
from .auth import AuthService
from .drill_service import DrillService
from .exceptions import (
    AthleteNotOnRosterException,
    AuthException,
    DrillException,
    DrillNotFoundException,
    DuplicateDrillException,
    DuplicateUserException,
    InvalidCredentialsException,
    InvalidDrillDataException,
    InvalidRoleException,
    KISException,
    UnauthorizedAccessException,
    UserNotFoundException,
)
from .kis import KIS
from .models import Athlete, Category, Coach, Drill, Priority, Role, User

__all__ = [
    # Facade
    "KIS",
    # Services
    "AuthService",
    "DrillService",
    "AlertService",
    "NoOpAlertService",
    "InMemoryAlertService",
    # Models
    "User",
    "Athlete",
    "Coach",
    "Drill",
    # Enums
    "Role",
    "Priority",
    "Category",
    # Exceptions
    "KISException",
    "AuthException",
    "DrillException",
    "DuplicateUserException",
    "InvalidCredentialsException",
    "UserNotFoundException",
    "InvalidRoleException",
    "UnauthorizedAccessException",
    "AthleteNotOnRosterException",
    "DrillNotFoundException",
    "InvalidDrillDataException",
    "DuplicateDrillException",
]

"""Custom exception hierarchy for the KIS domain.

All domain errors inherit from :class:`KISException` so callers can catch any
KIS-originated failure with a single `except KISException` clause while still
being able to discriminate on more specific subclasses.
"""


class KISException(Exception):
    """Base class for every exception raised by the KIS domain layer."""


# ---------------------------------------------------------------------------
# Authentication / user management
# ---------------------------------------------------------------------------


class AuthException(KISException):
    """Base class for authentication and user-management failures."""


class DuplicateUserException(AuthException):
    """Raised when a signup attempts to reuse an existing username."""


class InvalidCredentialsException(AuthException):
    """Raised when a login attempt does not match a stored user/password."""


class UserNotFoundException(AuthException):
    """Raised when a lookup is performed for a username that does not exist."""


class InvalidRoleException(AuthException):
    """Raised when an operation is attempted by a user with the wrong role."""


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class UnauthorizedAccessException(KISException):
    """Raised when an actor tries to access or mutate a drill they do not own."""


class AthleteNotOnRosterException(KISException):
    """Raised when a coach acts on an athlete that is not on their roster."""


# ---------------------------------------------------------------------------
# Drill lifecycle
# ---------------------------------------------------------------------------


class DrillException(KISException):
    """Base class for drill-related failures."""


class DrillNotFoundException(DrillException):
    """Raised when a drill id does not resolve to a stored drill."""


class InvalidDrillDataException(DrillException):
    """Raised when drill input fails validation (e.g. blank title)."""


class DuplicateDrillException(DrillException):
    """Raised when attempting to create a drill with an id that already exists."""

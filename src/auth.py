"""User authentication and lookup.

:class:`AuthService` owns the in-memory user table. It is intentionally simple
— passwords are stored using :func:`hashlib.sha256` rather than a real KDF
because this is a teaching codebase with no real users. The interface is shaped
so a stronger backend could be dropped in without touching callers.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

from .exceptions import (
    DuplicateUserException,
    InvalidCredentialsException,
    InvalidRoleException,
    UserNotFoundException,
)
from .models import Athlete, Coach, Role, User


def _hash_password(password: str) -> str:
    """Return a deterministic hex digest of ``password``.

    SHA-256 is used as a stand-in for a real password KDF. It is good enough
    to keep plaintext out of the user table without pulling in a third-party
    dependency.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class AuthService:
    """Manage user signup, login, and lookup against an in-memory store."""

    def __init__(self) -> None:
        """Initialize the service with an empty user table."""
        self._users: Dict[str, User] = {}

    # ------------------------------------------------------------------
    # Signup / login
    # ------------------------------------------------------------------

    def signup(self, username: str, password: str, role: Role) -> User:
        """Create a new user and return it.

        Args:
            username: A non-empty unique username.
            password: A non-empty password to hash and store.
            role: The :class:`Role` the new user will hold. Determines whether
                an :class:`Athlete` or :class:`Coach` instance is created.

        Returns:
            The newly created :class:`User`.

        Raises:
            DuplicateUserException: If ``username`` is already registered.
            InvalidCredentialsException: If username or password is blank.
            InvalidRoleException: If ``role`` is not a :class:`Role` member.
        """
        if not username or not password:
            raise InvalidCredentialsException(
                "Username and password must be non-empty."
            )
        if not isinstance(role, Role):
            raise InvalidRoleException(f"Unknown role: {role!r}")
        if username in self._users:
            raise DuplicateUserException(
                f"Username '{username}' is already taken."
            )

        password_hash = _hash_password(password)
        user: User
        if role is Role.ATHLETE:
            user = Athlete(username=username, password_hash=password_hash, role=role)
        else:
            user = Coach(username=username, password_hash=password_hash, role=role)

        self._users[username] = user
        return user

    def login(self, username: str, password: str) -> User:
        """Validate credentials and return the matching user.

        Args:
            username: The username to look up.
            password: The plaintext password to verify against the stored hash.

        Returns:
            The authenticated :class:`User`.

        Raises:
            InvalidCredentialsException: If the user does not exist or the
                password does not match. The same exception is used for both
                cases on purpose so callers cannot probe for usernames.
        """
        user = self._users.get(username)
        if user is None or user.password_hash != _hash_password(password):
            raise InvalidCredentialsException("Invalid username or password.")
        return user

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_user(self, username: str) -> User:
        """Return the user with ``username`` or raise if absent.

        Args:
            username: The username to look up.

        Raises:
            UserNotFoundException: If no user is registered with that username.
        """
        user = self._users.get(username)
        if user is None:
            raise UserNotFoundException(f"No user with username '{username}'.")
        return user

    def list_users(self) -> List[User]:
        """Return a list of all registered users in insertion order."""
        return list(self._users.values())

    def exists(self, username: str) -> bool:
        """Return True if a user with ``username`` is registered."""
        return username in self._users

    def get_athlete(self, username: str) -> Athlete:
        """Return the user with ``username`` if they are an Athlete.

        Raises:
            UserNotFoundException: If no user is registered with that username.
            InvalidRoleException: If the user exists but is not an Athlete.
        """
        user = self.get_user(username)
        if not isinstance(user, Athlete):
            raise InvalidRoleException(
                f"User '{username}' is not an athlete."
            )
        return user

    def get_coach(self, username: str) -> Coach:
        """Return the user with ``username`` if they are a Coach.

        Raises:
            UserNotFoundException: If no user is registered with that username.
            InvalidRoleException: If the user exists but is not a Coach.
        """
        user = self.get_user(username)
        if not isinstance(user, Coach):
            raise InvalidRoleException(
                f"User '{username}' is not a coach."
            )
        return user

    def find(self, username: str) -> Optional[User]:
        """Return the user with ``username`` or ``None`` if absent."""
        return self._users.get(username)

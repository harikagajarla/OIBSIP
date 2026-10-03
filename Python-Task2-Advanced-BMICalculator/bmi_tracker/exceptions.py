"""Custom exceptions so each layer can report problems clearly."""


class BMITrackerError(Exception):
    """Base class for all application errors."""


class ValidationError(BMITrackerError):
    """The user supplied invalid input. The message is safe to show to the user."""


class DuplicateUserError(ValidationError):
    """A user with this name already exists."""


class DatabaseError(BMITrackerError):
    """Reading from or writing to the database failed."""

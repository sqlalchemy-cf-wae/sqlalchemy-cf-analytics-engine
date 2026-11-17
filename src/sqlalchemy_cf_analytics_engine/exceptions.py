"""The exception hierarchy required by PEP 249."""

# pylint: disable=redefined-builtin


class Warning(Exception):  # noqa: A001
    """Important warnings, such as data truncation."""


class Error(Exception):
    """Base class of every error raised by this driver."""


class InterfaceError(Error):
    """The driver was misused, or Cloudflare's reply could not be read."""


class DatabaseError(Error):
    """An error reported by Cloudflare."""


class DataError(DatabaseError):
    """A problem with the data, such as a value out of range."""


class OperationalError(DatabaseError):
    """The request failed: network errors, timeouts, rate limits, 5xx replies."""


class IntegrityError(DatabaseError):
    """Relational integrity was affected. Unused: the driver is read-only."""


class InternalError(DatabaseError):
    """Cloudflare reported an internal error."""


class ProgrammingError(DatabaseError):
    """The query was rejected: bad SQL, unknown dataset or column, bad token."""


class NotSupportedError(DatabaseError):
    """The query or method is not supported, such as writes or transactions."""

"""
PEP 249 driver for the Workers Analytics Engine SQL API.

The driver sends SQL to
``https://api.cloudflare.com/client/v4/accounts/{account_id}/analytics_engine/sql``
with the API token as a bearer token, and turns the JSON reply into
``description`` and rows. The API host is fixed: it never comes from the
connection URI, so the token cannot be sent anywhere else.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy_cf_analytics_engine.exceptions import InterfaceError

apilevel = "2.0"
threadsafety = 1  # threads may share the module, but not connections
paramstyle = "pyformat"

API_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}/analytics_engine/sql"
)


def connect(account_id: str, api_token: str, timeout: float = 30.0) -> Connection:
    """Return a connection. Nothing is sent to Cloudflare until a query runs."""
    if not account_id or not api_token:
        raise InterfaceError(
            "Both a Cloudflare account ID and an API token are required, "
            "e.g. cfwae://{account_id}:{api_token}@"
        )
    return Connection(account_id, api_token, timeout)


class Connection:
    """Holds the credentials. The SQL API is stateless, so there is no session."""

    def __init__(self, account_id: str, api_token: str, timeout: float) -> None:
        self.account_id = account_id
        self.api_token = api_token
        self.timeout = timeout
        self.closed = False

    def cursor(self) -> Cursor:
        self._check_open()
        return Cursor(self)

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        """No-op: the driver is read-only and has no transactions."""

    def rollback(self) -> None:
        """No-op: the driver is read-only and has no transactions."""

    def _check_open(self) -> None:
        if self.closed:
            raise InterfaceError("Connection is closed")


class Cursor:
    """Runs one query at a time and holds its result."""

    arraysize = 1

    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.description: list[tuple[Any, ...]] | None = None
        self.rowcount = -1
        self.closed = False
        self._rows: list[tuple[Any, ...]] = []
        self._position = 0

    def execute(self, operation: str, parameters: Any = None) -> Cursor:
        """
        Send ``operation`` to the SQL API and store the result.

        TODO:
        - refuse anything that is not SELECT, SHOW or WITH (NotSupportedError)
        - strip a trailing semicolon and append ``FORMAT JSON``
        - POST to API_URL with ``Authorization: Bearer <api_token>``
        - 401/403 -> ProgrammingError, 400 -> ProgrammingError with
          Cloudflare's message, 429/5xx/timeout -> retry with backoff, then
          OperationalError, invalid JSON -> InterfaceError
        - build ``description`` from ``meta`` and rows from ``data``,
          converting types (see types.py)
        """
        self._check_open()
        raise NotImplementedError

    def executemany(self, operation: str, seq_of_parameters: Sequence[Any]) -> None:
        raise NotImplementedError("executemany is not supported")

    def fetchone(self) -> tuple[Any, ...] | None:
        self._check_executed()
        if self._position >= len(self._rows):
            return None
        row = self._rows[self._position]
        self._position += 1
        return row

    def fetchmany(self, size: int | None = None) -> list[tuple[Any, ...]]:
        self._check_executed()
        size = size or self.arraysize
        rows = self._rows[self._position : self._position + size]
        self._position += len(rows)
        return rows

    def fetchall(self) -> list[tuple[Any, ...]]:
        self._check_executed()
        rows = self._rows[self._position :]
        self._position = len(self._rows)
        return rows

    def close(self) -> None:
        self.closed = True

    def setinputsizes(self, sizes: Any) -> None:
        """Required by PEP 249; does nothing."""

    def setoutputsize(self, size: Any, column: Any = None) -> None:
        """Required by PEP 249; does nothing."""

    def _check_open(self) -> None:
        if self.closed:
            raise InterfaceError("Cursor is closed")
        self.connection._check_open()

    def _check_executed(self) -> None:
        self._check_open()
        if self.description is None:
            raise InterfaceError("No query has been executed")

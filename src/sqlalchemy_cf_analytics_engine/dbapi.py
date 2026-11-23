"""
PEP 249 driver for the Workers Analytics Engine SQL API.

The driver sends SQL to
``https://api.cloudflare.com/client/v4/accounts/{account_id}/analytics_engine/sql``
with the API token as a bearer token, and turns the JSON reply into
``description`` and rows. The API host is fixed: it never comes from the
connection URI, so the token cannot be sent anywhere else.
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from datetime import datetime
from typing import Any

import httpx

from sqlalchemy_cf_analytics_engine.exceptions import (
    InterfaceError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
)

apilevel = "2.0"
threadsafety = 1  # threads may share the module, but not connections
paramstyle = "pyformat"

API_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}/analytics_engine/sql"
)
_READ_ONLY_QUERY_PREFIX = re.compile(r"(?:SELECT\b|SHOW\s+TABLES\b)", re.IGNORECASE)
_FORMAT_JSON_SUFFIX = re.compile(r"\bFORMAT\s+JSON$", re.IGNORECASE)


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
        """Execute one read-only query and buffer its result."""
        self._check_open()
        self.description = None
        self._rows = []
        self._position = 0
        self.rowcount = -1

        if parameters:
            raise NotSupportedError("Bound parameters are not supported yet")
        sql = operation.strip().removesuffix(";").rstrip()
        if ";" in sql or not _READ_ONLY_QUERY_PREFIX.match(sql):
            raise NotSupportedError("Expected one SELECT or SHOW TABLES query")
        if not _FORMAT_JSON_SUFFIX.search(sql):
            sql += "\nFORMAT JSON"

        connection = self.connection
        for attempt in range(3):
            try:
                response = httpx.post(
                    API_URL.format(account_id=connection.account_id),
                    headers={"Authorization": f"Bearer {connection.api_token}"},
                    content=sql.encode(),
                    timeout=connection.timeout,
                )
            except httpx.TimeoutException as exc:
                if attempt == 2:
                    raise OperationalError("Cloudflare query timed out") from exc
            except httpx.RequestError as exc:
                raise OperationalError("Cloudflare request failed") from exc
            else:
                if response.status_code != 429 and response.status_code < 500:
                    break
                if attempt == 2:
                    raise OperationalError(
                        f"Cloudflare returned HTTP {response.status_code}"
                    )
            time.sleep(0.25 * 2**attempt)

        if not response.is_success:
            raise ProgrammingError(
                f"Cloudflare HTTP {response.status_code}: {response.text}"
            )

        try:
            result = response.json()
            meta, data = result["meta"], result["data"]
            if not isinstance(meta, list) or not isinstance(data, list):
                raise TypeError("Expected arrays for meta and data")
            columns = [(column["name"], column["type"]) for column in meta]
            rows = [
                tuple(_convert(row[name], type_name) for name, type_name in columns)
                for row in data
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise InterfaceError("Invalid Cloudflare SQL response") from exc

        self.description = [
            (name, kind, None, None, None, None, None) for name, kind in columns
        ]
        self._rows = rows
        self.rowcount = len(rows)
        return self

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


def _convert(value: Any, type_name: str) -> Any:
    if value is None:
        return None
    if type_name == "DateTime":
        return datetime.fromisoformat(value)
    if type_name in ("UInt32", "UInt64"):
        return int(value)
    if type_name == "Float64":
        return float(value)
    return str(value)

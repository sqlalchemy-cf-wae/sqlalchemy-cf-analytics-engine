"""SQLAlchemy dialect for Cloudflare Workers Analytics Engine."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from sqlalchemy.engine import default
from sqlalchemy.engine.url import URL


class CloudflareAnalyticsEngineDialect(default.DefaultDialect):
    """
    Read-only dialect for ``cfwae://{account_id}:{api_token}@`` URIs.

    Each Analytics Engine dataset is exposed as a table in a single, unnamed
    schema.
    """

    name = "cfwae"
    driver = "httpx"

    supports_statement_cache = True
    supports_alter = False
    supports_sequences = False
    supports_native_boolean = False
    postfetch_lastrowid = False

    @classmethod
    def import_dbapi(cls) -> ModuleType:
        import sqlalchemy_cf_analytics_engine as dbapi

        return dbapi

    def create_connect_args(self, url: URL) -> tuple[list[Any], dict[str, Any]]:
        """
        Turn the URI into ``connect()`` arguments.

        The host is ignored, so the token always goes to Cloudflare's fixed API
        address. Missing credentials are reported by ``connect()``.
        """
        return [], {"account_id": url.username, "api_token": url.password}

    def do_rollback(self, dbapi_connection: Any) -> None:
        """Nothing to roll back: the driver is read-only."""

    def get_schema_names(self, connection: Any, **kw: Any) -> list[str]:
        return []

    def get_table_names(
        self, connection: Any, schema: str | None = None, **kw: Any
    ) -> list[str]:
        """TODO: run ``SHOW TABLES`` and return the dataset names."""
        raise NotImplementedError

    def get_view_names(
        self, connection: Any, schema: str | None = None, **kw: Any
    ) -> list[str]:
        return []

    def has_table(
        self, connection: Any, table_name: str, schema: str | None = None, **kw: Any
    ) -> bool:
        return table_name in self.get_table_names(connection, schema, **kw)

    def get_columns(
        self, connection: Any, table_name: str, schema: str | None = None, **kw: Any
    ) -> list[dict[str, Any]]:
        """
        TODO: return the fixed dataset schema: timestamp, _sample_interval,
        index1, blob1-blob20 and double1-double20, typed with types.py.
        """
        raise NotImplementedError

    def get_pk_constraint(
        self, connection: Any, table_name: str, schema: str | None = None, **kw: Any
    ) -> dict[str, Any]:
        return {"constrained_columns": [], "name": None}

    def get_foreign_keys(
        self, connection: Any, table_name: str, schema: str | None = None, **kw: Any
    ) -> list[dict[str, Any]]:
        return []

    def get_indexes(
        self, connection: Any, table_name: str, schema: str | None = None, **kw: Any
    ) -> list[dict[str, Any]]:
        return []

"""Smoke tests for the package skeleton."""

import pytest
from sqlalchemy import create_engine

import sqlalchemy_cf_analytics_engine as dbapi
from sqlalchemy_cf_analytics_engine.dialect import CloudflareAnalyticsEngineDialect


def test_dbapi_module_attributes() -> None:
    assert dbapi.apilevel == "2.0"
    assert dbapi.threadsafety == 1
    assert dbapi.paramstyle == "pyformat"


@pytest.mark.parametrize("account_id,api_token", [("", "token"), ("account", "")])
def test_connect_requires_credentials(account_id: str, api_token: str) -> None:
    with pytest.raises(dbapi.InterfaceError):
        dbapi.connect(account_id, api_token)


def test_fetch_before_execute_is_an_interface_error() -> None:
    cursor = dbapi.connect("account", "token").cursor()
    with pytest.raises(dbapi.InterfaceError):
        cursor.fetchall()


def test_cursor_after_close_is_an_interface_error() -> None:
    connection = dbapi.connect("account", "token")
    connection.close()
    with pytest.raises(dbapi.InterfaceError):
        connection.cursor()


@pytest.mark.parametrize(
    "uri", ["cfwae://account:token@", "cfwae+httpx://account:token@"]
)
def test_entry_point_registers_dialect(uri: str) -> None:
    """Needs the package installed (``pip install -e .``) for the entry point."""
    engine = create_engine(uri)
    assert isinstance(engine.dialect, CloudflareAnalyticsEngineDialect)
    assert engine.dialect.name == "cfwae"
    assert engine.dialect.driver == "httpx"


def test_create_connect_args_ignores_host() -> None:
    engine = create_engine("cfwae://account:token@elsewhere.example")
    _, kwargs = engine.dialect.create_connect_args(engine.url)
    assert kwargs == {"account_id": "account", "api_token": "token"}

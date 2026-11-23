from datetime import datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, exc, text

import sqlalchemy_cf_analytics_engine as dbapi


def recorded(name):
    path = Path(__file__).parent / "fixtures" / "responses" / f"{name}.txt"
    body, status = path.read_text().rsplit("\nHTTP ", 1)
    return httpx.Response(int(status), content=body)


def test_sqlalchemy_query(monkeypatch):
    def post(url, *, headers, content, timeout):
        assert (
            url
            == "https://api.cloudflare.com/client/v4/accounts/account/analytics_engine/sql"
        )
        assert headers == {"Authorization": "Bearer token"}
        assert content.endswith(b"\nFORMAT JSON")
        assert b";" not in content
        return recorded("time_grain_hour")

    monkeypatch.setattr(httpx, "post", post)
    engine = create_engine("cfwae://account:token@ignored.example")
    with engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT toStartOfInterval(timestamp, INTERVAL '1' HOUR) AS hour, "
                "SUM(_sample_interval) AS requests FROM api_requests GROUP BY hour;"
            )
        )
        assert list(result.keys()) == ["hour", "requests"]
        assert result.all() == [(datetime.fromisoformat("2026-11-17 21:00:00"), 414)]
        with pytest.raises(exc.NotSupportedError):
            connection.exec_driver_sql("DELETE FROM api_requests")


def test_empty_then_failed_query(monkeypatch):
    responses = iter([recorded("select_zero_rows"), recorded("error_bad_sql")])
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: next(responses))
    cursor = dbapi.connect("account", "token").cursor()
    cursor.execute("SELECT blob1 FROM api_requests LIMIT 0")
    assert cursor.description[0][0] == "blob1"
    assert cursor.fetchall() == []
    with pytest.raises(dbapi.ProgrammingError, match="422"):
        cursor.execute("SELECT bad")
    with pytest.raises(dbapi.InterfaceError):
        cursor.fetchall()


def test_rate_limit_then_success(monkeypatch):
    responses = iter([httpx.Response(429), recorded("show_tables")])
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: next(responses))
    monkeypatch.setattr(
        "sqlalchemy_cf_analytics_engine.dbapi.time.sleep", lambda _: None
    )
    cursor = dbapi.connect("account", "token").cursor()
    assert cursor.execute("SHOW TABLES").fetchone() == ("api_requests",)

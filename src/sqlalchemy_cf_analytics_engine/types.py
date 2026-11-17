"""Mapping from Workers Analytics Engine column types to SQLAlchemy types."""

from __future__ import annotations

from sqlalchemy import types

# TODO: confirm the type names the SQL API reports in ``meta`` and fill this in.
TYPE_MAP: dict[str, type[types.TypeEngine]] = {
    "DateTime": types.DateTime,
    "String": types.String,
    "Float64": types.Float,
    "UInt32": types.Integer,
    "UInt64": types.BigInteger,
}


def get_sqla_type(type_name: str) -> types.TypeEngine:
    """Return the SQLAlchemy type for a WAE type name. Unknown types are text."""
    return TYPE_MAP.get(type_name, types.String)()

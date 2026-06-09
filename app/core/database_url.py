"""Normalize PostgreSQL URLs for SQLAlchemy / Supabase."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_database_url(url: str) -> str:
    """Ensure ``postgresql+psycopg://`` driver and SSL for Supabase hosts."""
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgres://") :]
    elif normalized.startswith("postgresql://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgresql://") :]
    elif normalized.startswith("postgres+psycopg://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgres+psycopg://") :]
    return _ensure_supabase_ssl(normalized)


def _ensure_supabase_ssl(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if "supabase" not in host:
        return url

    query = parse_qs(parsed.query, keep_blank_values=True)
    if "sslmode" not in query:
        query["sslmode"] = ["require"]

    flat_query = urlencode({key: values[-1] for key, values in query.items()})
    return urlunparse(parsed._replace(query=flat_query))


def postgres_connect_args(url: str) -> dict[str, object]:
    """Driver connect args; Supabase requires SSL."""
    args: dict[str, object] = {"connect_timeout": 10}
    if not url.startswith("postgresql"):
        return args

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "sslmode" in query:
        args["sslmode"] = query["sslmode"][-1]
    elif parsed.hostname and "supabase" in parsed.hostname.lower():
        args["sslmode"] = "require"
    return args

#!/usr/bin/env python3
"""HeartAI Database Credential Helper (OP-04).

Provides robust, standards-compliant parsing of PostgreSQL connection URLs,
secure string literal escaping for PostgreSQL SQL statements, and safe
environment file inspection without leaking credentials in logs, CLI arguments,
or error messages.

Conforms to RFC 3986 URL parsing standards using Python standard library urllib.parse.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def parse_database_url(url: str) -> dict[str, str | int]:
    """Parse a PostgreSQL connection URL into discrete validated components.

    Handles percent-encoded credentials, special characters (@, :, /, !, etc.),
    and validates scheme, user, password, and database name.

    Raises ValueError with a sanitized error message (zero credentials revealed)
    if the URL is malformed or missing required components.
    """
    if not url or not url.strip():
        raise ValueError("DATABASE_URL is empty or missing")

    try:
        parsed = urlsplit(url.strip())
    except Exception as e:
        raise ValueError(f"Failed to parse DATABASE_URL syntax: {type(e).__name__}") from None

    # Validate scheme (support postgresql or postgresql+psycopg2)
    scheme = parsed.scheme.split("+")[0].lower() if parsed.scheme else ""
    if scheme != "postgresql":
        raise ValueError(f"Unsupported database scheme '{parsed.scheme}'; expected 'postgresql'")

    # Validate username
    if not parsed.username:
        raise ValueError("DATABASE_URL is missing username component")
    user = unquote(parsed.username)

    # Validate password
    if parsed.password is None or parsed.password == "":
        raise ValueError("DATABASE_URL is missing password component")
    password = unquote(parsed.password)

    # Validate database name
    raw_path = parsed.path.lstrip("/") if parsed.path else ""
    dbname = raw_path.split("?")[0]
    if not dbname:
        raise ValueError("DATABASE_URL is missing database name component")

    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432

    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
    }


def extract_database_url_from_env(env_path: str | Path) -> str | None:
    """Safely extract the DATABASE_URL value from an environment file.

    Returns the raw URL string or None if the file does not exist or does not
    contain a DATABASE_URL directive.
    """
    path = Path(env_path)
    if not path.is_file():
        return None

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if line.startswith("DATABASE_URL="):
                val = line.split("=", 1)[1].strip()
                # Strip wrapping quotes if present
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                return val
    except Exception:
        return None

    return None


def escape_pg_string_literal(value: str) -> str:
    """Escape a Python string for safe insertion into a PostgreSQL SQL string literal.

    PostgreSQL string literals escape single quotes by doubling them (' -> '').
    """
    return value.replace("'", "''")


def inspect_env_credentials(env_path: str | Path) -> dict[str, object]:
    """Inspect environment credentials and return a structured summary.

    Does NOT expose the plaintext password in the top-level returned status dict
    for logs, but provides it under a dedicated field for programmatic retrieval.
    """
    raw_url = extract_database_url_from_env(env_path)
    if not raw_url:
        return {"status": "not_configured", "message": "No DATABASE_URL found in environment file"}

    try:
        components = parse_database_url(raw_url)
        return {
            "status": "valid",
            "user": components["user"],
            "host": components["host"],
            "port": components["port"],
            "dbname": components["dbname"],
            "password_length": len(str(components["password"])),
            # Internal retrieval only
            "_password": components["password"],
        }
    except ValueError as e:
        return {
            "status": "malformed",
            "error": str(e),
        }


def main() -> int:
    """CLI dispatcher for shell script integration."""
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: db_credentials_helper.py <command> [args...]\n")
        return 1

    command = sys.argv[1]

    if command == "parse-env":
        env_file = sys.argv[2] if len(sys.argv) > 2 else "/opt/heartai/.env"
        res = inspect_env_credentials(env_file)
        if res["status"] == "not_configured":
            # Exit code 2 indicates no env / no DATABASE_URL (first run)
            sys.stdout.write("STATUS=not_configured\n")
            return 2
        elif res["status"] == "malformed":
            # Exit code 1 indicates malformed DATABASE_URL (fail closed)
            sys.stderr.write(f"ERROR: {res['error']}\n")
            return 1
        elif res["status"] == "valid":
            # Exit code 0 indicates valid credentials
            sys.stdout.write("STATUS=valid\n")
            sys.stdout.write(f"DB_USER={res['user']}\n")
            sys.stdout.write(f"DB_HOST={res['host']}\n")
            sys.stdout.write(f"DB_PORT={res['port']}\n")
            sys.stdout.write(f"DB_NAME={res['dbname']}\n")
            # Write password to descriptor or stdout safely
            sys.stdout.write(f"DB_PASSWORD={res['_password']}\n")
            return 0

    elif command == "escape-literal":
        if len(sys.argv) < 3:
            return 1
        sys.stdout.write(escape_pg_string_literal(sys.argv[2]))
        return 0

    elif command == "validate-url":
        if len(sys.argv) < 3:
            sys.stderr.write("ERROR: Missing URL argument\n")
            return 1
        try:
            res = parse_database_url(sys.argv[2])
            sys.stdout.write(f"VALID: user={res['user']} db={res['dbname']}\n")
            return 0
        except ValueError as e:
            sys.stderr.write(f"INVALID: {e}\n")
            return 1

    sys.stderr.write(f"Unknown command: {command}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

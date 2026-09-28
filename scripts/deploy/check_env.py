#!/usr/bin/env python3
"""Validate a production env file without printing secret values."""

import os
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

WEAK = {"CHANGE_ME", "pdoom", "password", "postgres", "secret", "changeme"}
REQUIRED = (
    "NODE_ENV",
    "PDOOM_ENV",
    "APP_BASE_URL",
    "DATABASE_URL",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "ACME_EMAIL",
    "PDOOM_WEB_IMAGE",
    "PDOOM_BACKUP_DIR",
)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if any(token in line for token in ("$(", "`", "$", "\x00")):
            fail(f"line {number} must be a KEY=VALUE assignment without shell expansion")
        if "=" not in line:
            fail(f"line {number} must be a KEY=VALUE assignment")
        key, value = line.split("=", 1)
        if not key.isidentifier() or not key.isupper():
            fail(f"line {number} has an invalid key")
        values[key] = value
    return values


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check_env.py <env-file>")
    path = Path(sys.argv[1])
    if not path.is_file():
        fail("env file is missing")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        fail("env file must not be readable by group or others; chmod 600")
    values = load(path)
    for key in REQUIRED:
        if key not in values or not values[key].strip():
            fail(f"{key} is required")
    if values["NODE_ENV"] != "production" or values["PDOOM_ENV"] != "production":
        fail("NODE_ENV and PDOOM_ENV must be production")
    origin = urlparse(values["APP_BASE_URL"])
    if origin.scheme != "https" or not origin.hostname or origin.username or origin.password:
        fail("APP_BASE_URL must be an https origin")
    if origin.path not in ("", "/") or origin.query or origin.fragment:
        fail("APP_BASE_URL must be an origin without a path, query, or fragment")
    if origin.hostname != "pdoom.live":
        fail("APP_BASE_URL host must be pdoom.live")
    database = urlparse(values["DATABASE_URL"])
    if database.scheme not in {"postgres", "postgresql"} or not database.hostname:
        fail("DATABASE_URL must be a postgres URL")
    if not database.username or not database.password or not database.path.strip("/"):
        fail("DATABASE_URL must include a user, password, and database name")
    if database.username != values["POSTGRES_USER"] or database.path.strip("/") != values["POSTGRES_DB"]:
        fail("DATABASE_URL user or database does not match POSTGRES_USER and POSTGRES_DB")
    if database.hostname != "postgres":
        fail("DATABASE_URL host must be the compose service name postgres")
    if values["POSTGRES_PASSWORD"] in WEAK or database.password in WEAK or len(values["POSTGRES_PASSWORD"]) < 16:
        fail("POSTGRES_PASSWORD is missing or too weak")
    if values["POSTGRES_PASSWORD"] != database.password:
        fail("DATABASE_URL password does not match POSTGRES_PASSWORD")
    email = values["ACME_EMAIL"]
    if "@" not in email or email.endswith("@example.com"):
        fail("ACME_EMAIL must be a real mailbox")
    if not values["PDOOM_WEB_IMAGE"].startswith("pdoom-live:"):
        fail("PDOOM_WEB_IMAGE must be a pdoom-live image tag")
    backup = Path(values["PDOOM_BACKUP_DIR"])
    if not backup.is_absolute():
        fail("PDOOM_BACKUP_DIR must be an absolute path")
    hook = values.get("PDOOM_BACKUP_HOOK", "")
    if hook:
        hook_path = Path(hook)
        if not hook_path.is_absolute() or not hook_path.is_file() or not os.access(hook_path, os.X_OK):
            fail("PDOOM_BACKUP_HOOK must be an absolute executable file")
    print("env file ok")


if __name__ == "__main__":
    main()

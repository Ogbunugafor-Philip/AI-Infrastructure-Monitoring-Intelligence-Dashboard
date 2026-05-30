#!/usr/bin/env python3
"""
Create (or promote) the Super Admin user.

Reads SUPER_ADMIN_EMAIL from .env (overridable with --email). The password is
taken from --password, else from stdin if piped, else prompted securely via
getpass (no echo). The password is hashed with Argon2 and NEVER printed.

Usage:
    python scripts/create_super_admin.py --email you@example.com
    # then enter the password at the secure prompt
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Ensure the backend package root is importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decouple import Config, RepositoryEnv  # noqa: E402
from sqlalchemy import select  # noqa: E402

from database import AsyncSessionLocal, engine  # noqa: E402
from models.enums import UserRole  # noqa: E402
from models.user import User  # noqa: E402
from utils.security import hash_password  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_config = Config(RepositoryEnv(str(PROJECT_ROOT / ".env")))


def _read_password(provided: str | None) -> str:
    if provided:
        return provided
    if not sys.stdin.isatty():
        # Non-interactive: read a single line from stdin.
        line = sys.stdin.readline().strip()
        if line:
            return line
    return getpass.getpass("Enter Super Admin password (input hidden): ")


async def _run(email: str, password: str) -> None:
    hashed = hash_password(password)
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            existing.role = UserRole.super_admin
            existing.hashed_password = hashed
            existing.is_active = True
            existing.is_locked = False
            existing.failed_login_attempts = 0
            action = "updated existing user to super_admin"
        else:
            db.add(User(
                email=email,
                full_name="Super Admin",
                hashed_password=hashed,
                role=UserRole.super_admin,
                is_active=True,
            ))
            action = "created new super_admin user"
        await db.commit()
    await engine.dispose()
    # Confirmation WITHOUT the password.
    print(f"OK: {action} for {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote the Super Admin user.")
    parser.add_argument("--email", default=_config("SUPER_ADMIN_EMAIL", default=""))
    parser.add_argument("--password", default=None, help="Optional; otherwise prompted/stdin.")
    args = parser.parse_args()

    email = (args.email or "").strip()
    if not email:
        print("ERROR: no email provided (set SUPER_ADMIN_EMAIL in .env or pass --email)", file=sys.stderr)
        sys.exit(1)

    password = _read_password(args.password)
    if not password or len(password) < 8:
        print("ERROR: password must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_run(email, password))


if __name__ == "__main__":
    main()

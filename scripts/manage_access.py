"""Operator CLI for provisioning project-member accounts and memberships.

Run interactively on the trusted host. Passwords are read with getpass and never
accepted as command-line arguments or printed. Requires an authenticated admin.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
import uuid

from config import get_settings
from database import Database
from services.access_control import AccessControl


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project Continue access administration")
    parser.add_argument("--admin-email", help="Administrator email; prompted when omitted")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Create a project member account")
    create.add_argument("--email", required=True)
    create.add_argument("--role", choices=("owner", "editor", "viewer"), default="viewer")

    bootstrap = commands.add_parser("bootstrap-owner", help="Assign the first owner of a project")
    bootstrap.add_argument("--project-id", required=True)

    grant = commands.add_parser("grant-project", help="Grant or update project membership")
    grant.add_argument("--project-id", required=True)
    grant.add_argument("--email", required=True)
    grant.add_argument("--role", choices=("owner", "editor", "viewer"), default="viewer")

    commands.add_parser("list-users", help="List account IDs, emails, roles and enabled state")
    commands.add_parser("list-projects", help="List project IDs and names")
    return parser


def _admin_principal(access: AccessControl, email: str | None) -> dict:
    address = email or input("Administrator email: ").strip()
    password = getpass.getpass("Administrator password: ")
    principal = access.authenticate(address, password)
    if principal is None or principal.get("role") != "admin":
        raise PermissionError("Administrator authentication failed")
    return principal


def _new_password() -> str:
    password = getpass.getpass("New account password (12+ characters): ")
    confirmation = getpass.getpass("Confirm new account password: ")
    if password != confirmation:
        raise ValueError("Password confirmation does not match")
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    return password


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = get_settings()
    signing_key = os.environ.get("SESSION_SIGNING_KEY", "")
    database = Database(settings.database_path)
    try:
        access = AccessControl(database, signing_key)
        actor = _admin_principal(access, args.admin_email)

        if args.command == "create-user":
            password = _new_password()
            user_id = "user-" + uuid.uuid4().hex
            access.create_user(user_id, args.email, password, role=args.role)
            print(f"USER CREATED: {user_id} ({args.role})")
        elif args.command == "bootstrap-owner":
            access.bootstrap_project_owner(actor, args.project_id)
            print(f"PROJECT OWNER BOOTSTRAPPED: {args.project_id}")
        elif args.command == "grant-project":
            with database.connection() as connection:
                row = connection.execute(
                    "SELECT id FROM pc_users WHERE email=? COLLATE NOCASE AND enabled=1",
                    (args.email.strip(),),
                ).fetchone()
            if row is None:
                raise KeyError("Enabled account not found")
            access.grant_project(actor, args.project_id, row["id"], role=args.role)
            print(f"PROJECT MEMBERSHIP SET: {args.project_id} ({args.role})")
        elif args.command == "list-users":
            with database.connection() as connection:
                rows = connection.execute(
                    "SELECT id,email,role,enabled FROM pc_users ORDER BY email"
                ).fetchall()
            for row in rows:
                print(f"{row['id']}\t{row['email']}\t{row['role']}\t{'enabled' if row['enabled'] else 'disabled'}")
            print(f"USER COUNT: {len(rows)}")
        elif args.command == "list-projects":
            with database.connection() as connection:
                rows = connection.execute("SELECT id,name FROM projects ORDER BY name").fetchall()
            for row in rows:
                print(f"{row['id']}\t{row['name']}")
            print(f"PROJECT COUNT: {len(rows)}")
        return 0
    except Exception as exc:
        # Do not emit passwords, signing keys, SQL details or exception messages.
        print(f"ACCESS ADMINISTRATION FAILED: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

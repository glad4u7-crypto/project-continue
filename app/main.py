"""Core application entry point."""

from config import settings


def main() -> int:
    """Run the lightweight application bootstrap and return an exit code."""
    print(
        f"{settings.app_name} core entry point ready "
        f"[{settings.app_env}]"
    )
    return 0

"""Read-only probe for the public Streamlit server health endpoint.

This checks HTTP reachability only. It does not authenticate, read application
records, inspect provider logs, or change/restart the hosted application.
"""
from __future__ import annotations

import argparse
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirectHandler(HTTPRedirectHandler):
    """Do not follow redirects away from the configured dashboard origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_dashboard_health(base_url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Return a sanitized health result without exposing the supplied URL."""
    try:
        parsed = urlsplit(base_url.strip())
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            return False, "URL must be an HTTPS dashboard origin without credentials, query, or fragment"
        path = parsed.path.rstrip("/")
        health_url = urlunsplit((parsed.scheme, parsed.netloc, f"{path}/_stcore/health", "", ""))
        request = Request(
            health_url,
            headers={"Accept": "text/plain", "User-Agent": "Project-Continue-Health-Check/1.0"},
            method="GET",
        )
        opener = build_opener(_NoRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            if response.status == 200:
                return True, "Streamlit health endpoint returned HTTP 200"
            return False, f"Streamlit health endpoint returned HTTP {response.status}"
    except HTTPError as exc:
        return False, f"Streamlit health endpoint returned HTTP {exc.code}"
    except (URLError, TimeoutError, OSError, ValueError):
        return False, "Streamlit health endpoint could not be reached"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("STREAMLIT_APP_URL", ""))
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    if not args.url.strip():
        print("SKIP: STREAMLIT_APP_URL is not configured")
        return 0
    if not 0 < args.timeout <= 30:
        print("FAIL: timeout must be greater than 0 and at most 30 seconds")
        return 1
    passed, detail = check_dashboard_health(args.url, args.timeout)
    print(("PASS: " if passed else "FAIL: ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

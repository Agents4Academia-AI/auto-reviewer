"""Shared-password auth with a per-user display name, via a signed cookie.

Deliberately minimal: one shared password gates access, and each visitor picks
a display name at login. The cookie stores that name, signed (not encrypted)
with itsdangerous so it can't be forged — it's an identity *label* for a
trusted group, not real authentication. If REVIEWER_SITE_PASSWORD is unset,
auth is disabled entirely and everyone is the "guest" user — convenient for
local dev. Swapping to real accounts later means replacing this one module.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer

from web import settings

_serializer = URLSafeSerializer(settings.SECRET_KEY, salt="reviewer-auth")
# Identity used when auth is disabled (dev), so review ownership still works.
GUEST = "guest"


def auth_enabled() -> bool:
    return bool(settings.SITE_PASSWORD)


def password_ok(candidate: str) -> bool:
    return bool(settings.SITE_PASSWORD) and candidate == settings.SITE_PASSWORD


def issue_cookie(response, username: str) -> None:
    token = _serializer.dumps(username)
    response.set_cookie(
        settings.SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


def clear_cookie(response) -> None:
    response.delete_cookie(settings.SESSION_COOKIE)


def current_user(request: Request) -> str | None:
    """The logged-in display name, or None if not authenticated.

    When auth is disabled, everyone is GUEST so ownership attribution still
    works in dev.
    """
    if not auth_enabled():
        return GUEST
    token = request.cookies.get(settings.SESSION_COOKIE)
    if not token:
        return None
    try:
        name = _serializer.loads(token)
    except BadSignature:
        return None
    return name if isinstance(name, str) and name else None


def is_authenticated(request: Request) -> bool:
    return current_user(request) is not None


def require_auth(request: Request):
    """FastAPI dependency. Redirects browser routes to /login when logged out."""
    if not is_authenticated(request):
        # 303 so the browser issues a GET to /login.
        raise _RedirectToLogin()


class _RedirectToLogin(Exception):
    pass


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)

"""Shared-password auth via a signed cookie.

Deliberately minimal: one password for everyone, no user accounts. The cookie
is signed (not encrypted) with itsdangerous so it can't be forged. If
REVIEWER_SITE_PASSWORD is unset, auth is disabled entirely — convenient for
local dev. Swapping to real accounts later means replacing this one module.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer

from web import settings

_serializer = URLSafeSerializer(settings.SECRET_KEY, salt="reviewer-auth")
_AUTH_VALUE = "ok"


def auth_enabled() -> bool:
    return bool(settings.SITE_PASSWORD)


def password_ok(candidate: str) -> bool:
    return bool(settings.SITE_PASSWORD) and candidate == settings.SITE_PASSWORD


def issue_cookie(response) -> None:
    token = _serializer.dumps(_AUTH_VALUE)
    response.set_cookie(
        settings.SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


def clear_cookie(response) -> None:
    response.delete_cookie(settings.SESSION_COOKIE)


def is_authenticated(request: Request) -> bool:
    if not auth_enabled():
        return True
    token = request.cookies.get(settings.SESSION_COOKIE)
    if not token:
        return False
    try:
        return _serializer.loads(token) == _AUTH_VALUE
    except BadSignature:
        return False


def require_auth(request: Request):
    """FastAPI dependency. Redirects browser routes to /login when logged out."""
    if not is_authenticated(request):
        # 303 so the browser issues a GET to /login.
        raise _RedirectToLogin()


class _RedirectToLogin(Exception):
    pass


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)

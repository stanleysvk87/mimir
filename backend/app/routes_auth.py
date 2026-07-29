from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import (
    COOKIE_NAME,
    check_password,
    clear_failed_logins,
    create_session,
    is_locked_out,
    record_failed_login,
    require_auth,
)
from app.models import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    ip = _client_ip(request)
    if is_locked_out(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts -- try again in a few minutes.",
        )

    if not check_password(payload.password):
        record_failed_login(ip)
        raise HTTPException(status_code=401, detail="Wrong password")

    clear_failed_logins(ip)
    token = create_session()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=14 * 24 * 3600,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.post("/verify", dependencies=[Depends(require_auth)])
def verify(payload: LoginRequest):
    return {"ok": check_password(payload.password)}

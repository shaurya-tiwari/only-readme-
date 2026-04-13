"""Worker and admin session endpoints."""

import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.password_auth import verify_password
from backend.core.rate_limit import auth_rate_limiter
from backend.core.session_auth import create_session_token, get_current_session
from backend.database import get_db
from backend.db.models import Worker
from backend.schemas.auth import AdminLoginRequest, WorkerLoginRequest

router = APIRouter(prefix="/api/auth", tags=["Auth"])
SESSION_COOKIE_NAME = "rideshield_session"
SESSION_COOKIE_MAX_AGE = settings.SESSION_DURATION_HOURS * 3600
SESSION_COOKIE_SECURE = settings.SESSION_COOKIE_SECURE
SESSION_COOKIE_SAMESITE = settings.SESSION_COOKIE_SAMESITE


def worker_session_payload(worker: Worker) -> dict:
    return {
        "role": "worker",
        "worker_id": str(worker.id),
        "name": worker.name,
        "phone": worker.phone,
    }


@router.post("/worker/login")
async def worker_login(
    request: WorkerLoginRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_host = http_request.client.host if http_request.client else "unknown"
    await auth_rate_limiter.hit(
        f"worker:{client_host}:{request.phone}",
        limit=settings.AUTH_RATE_LIMIT_ATTEMPTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    worker = (await db.execute(select(Worker).where(Worker.phone == request.phone))).scalar_one_or_none()
    if not worker or not verify_password(request.password, worker.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker credentials.",
        )
    if worker.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Worker account is {worker.status}.",
        )

    token = create_session_token(worker_session_payload(worker))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {
        "token": token,
        "session": {
            "role": "worker",
            "worker_id": str(worker.id),
            "name": worker.name,
            "phone": worker.phone,
        },
        "message": "Worker signed in.",
    }


@router.post("/admin/login")
async def admin_login(request: AdminLoginRequest, http_request: Request, response: Response):
    client_host = http_request.client.host if http_request.client else "unknown"
    await auth_rate_limiter.hit(
        f"admin:{client_host}:{request.username}",
        limit=settings.AUTH_RATE_LIMIT_ATTEMPTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    username_ok = hmac.compare_digest(request.username.encode(), settings.ADMIN_USERNAME.encode())
    password_ok = hmac.compare_digest(request.password.encode(), settings.ADMIN_PASSWORD.encode())
    if not username_ok or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )

    token = create_session_token(
        {
            "role": "admin",
            "admin_id": "rideshield-admin",
            "name": "RideShield Admin",
            "username": settings.ADMIN_USERNAME,
        }
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {
        "token": token,
        "session": {
            "role": "admin",
            "admin_id": "rideshield-admin",
            "name": "RideShield Admin",
            "username": settings.ADMIN_USERNAME,
        },
        "message": "Admin signed in.",
    }


@router.get("/me")
async def get_current_auth_session(session: dict = Depends(get_current_session)):
    return {
        "session": session,
    }


@router.post("/logout")
async def logout(response: Response):
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {"message": "Session cleared."}

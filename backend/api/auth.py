"""
Sprint 3 auth endpoints for worker and admin session flows.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.session_auth import create_session_token, get_current_session
from backend.database import get_db
from backend.db.models import Worker
from backend.schemas.auth import AdminLoginRequest, WorkerLoginRequest

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def worker_session_payload(worker: Worker) -> dict:
    return {
        "role": "worker",
        "worker_id": str(worker.id),
        "name": worker.name,
        "phone": worker.phone,
    }


@router.post("/worker/login")
async def worker_login(request: WorkerLoginRequest, db: AsyncSession = Depends(get_db)):
    worker = (await db.execute(select(Worker).where(Worker.phone == request.phone))).scalar_one_or_none()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found for this phone number.",
        )
    if worker.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Worker account is {worker.status}.",
        )

    token = create_session_token(worker_session_payload(worker))
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
async def admin_login(request: AdminLoginRequest):
    if request.username != settings.ADMIN_USERNAME or request.password != settings.ADMIN_PASSWORD:
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
async def logout():
    return {"message": "Client-side session cleared."}

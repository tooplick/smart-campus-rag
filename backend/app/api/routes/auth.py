from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.admin import Admin
from app.schemas.auth import LoginRequest, LoginResponse, InitializeRequest, ChangePasswordRequest
from app.utils.response import success_response, error_response
from app.api.deps import get_current_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    admin = await db.get(Admin, 1)
    if admin is None:
        return error_response("Admin not initialized", status_code=400)

    if not verify_password(req.password, admin.password_hash):
        return error_response("Invalid credentials", status_code=401)

    if admin.status != 1:
        return error_response("Admin account is disabled", status_code=403)

    admin.last_login_at = datetime.now(timezone.utc)
    token = create_access_token({"sub": admin.username, "admin_id": admin.id})

    return success_response({
        "token": token,
        "must_change_password": admin.must_change_password,
        "username": admin.username,
    })


@router.post("/initialize")
async def initialize(req: InitializeRequest, db: AsyncSession = Depends(get_db)):
    admin = await db.get(Admin, 1)
    if admin is None:
        return error_response("Admin not initialized", status_code=400)

    if not admin.must_change_password:
        return error_response("Already initialized", status_code=400)

    if len(req.new_password) < 6:
        return error_response("Password must be at least 6 characters", status_code=400)

    admin.password_hash = hash_password(req.new_password)
    admin.must_change_password = False
    admin.password_changed_at = datetime.now(timezone.utc)

    if req.new_username:
        admin.username = req.new_username

    token = create_access_token({"sub": admin.username, "admin_id": admin.id})

    return success_response({
        "token": token,
        "must_change_password": False,
        "username": admin.username,
    })


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.old_password, admin.password_hash):
        return error_response("Invalid old password", status_code=400)

    if len(req.new_password) < 6:
        return error_response("Password must be at least 6 characters", status_code=400)

    admin.password_hash = hash_password(req.new_password)
    admin.password_changed_at = datetime.now(timezone.utc)

    return success_response(message="Password changed successfully")


@router.get("/me")
async def get_me(admin: Admin = Depends(get_current_admin)):
    return success_response({
        "id": admin.id,
        "username": admin.username,
        "must_change_password": admin.must_change_password,
        "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None,
    })

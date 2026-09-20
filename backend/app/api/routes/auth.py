from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.admin import Admin
from app.schemas.auth import LoginRequest, InitializeRequest, ChangePasswordRequest
from app.utils.response import success_response, error_response
from app.api.deps import get_current_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _build_login_data(admin: Admin, token: str, message: str = "success"):
    return success_response(
        data={
            "token": token,
            "token_type": "Bearer",
            "admin": {"username": admin.username},
            "must_change_password": admin.must_change_password,
        },
        message=message,
    )


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    admin = await db.get(Admin, 1)
    if admin is None:
        return error_response("Admin not initialized", status_code=400, code="ADMIN_NOT_INITIALIZED")

    if not verify_password(req.password, admin.password_hash):
        return error_response("用户名或密码错误", status_code=401, code="INVALID_CREDENTIALS")

    if admin.status != 1:
        return error_response("管理员账户已禁用", status_code=403, code="ADMIN_DISABLED")

    admin.last_login_at = datetime.now(timezone.utc)
    token = create_access_token({"sub": admin.username, "admin_id": admin.id})

    msg = "password initialization required" if admin.must_change_password else "success"
    await db.commit()
    return _build_login_data(admin, token, message=msg)


@router.post("/initialize")
async def initialize(req: InitializeRequest, db: AsyncSession = Depends(get_db)):
    admin = await db.get(Admin, 1)
    if admin is None:
        return error_response("Admin not initialized", status_code=400, code="ADMIN_NOT_INITIALIZED")

    if not admin.must_change_password:
        return error_response("已经初始化过了", status_code=409, code="ALREADY_INITIALIZED")

    if not verify_password(req.current_password, admin.password_hash):
        return error_response("当前密码错误", status_code=400, code="INVALID_CURRENT_PASSWORD")

    if len(req.new_password) < 6:
        return error_response("密码长度不能少于6位", status_code=422, code="PASSWORD_TOO_SHORT")

    admin.username = req.username
    admin.password_hash = hash_password(req.new_password)
    admin.must_change_password = False
    admin.password_changed_at = datetime.now(timezone.utc)

    token = create_access_token({"sub": admin.username, "admin_id": admin.id})
    await db.commit()

    return success_response(
        data={
            "token": token,
            "token_type": "Bearer",
            "admin": {"username": admin.username},
            "must_change_password": False,
        },
        message="initialized successfully",
    )


@router.get("/me")
async def get_me(admin: Admin = Depends(get_current_admin)):
    return success_response(
        data={
            "username": admin.username,
            "must_change_password": admin.must_change_password,
        }
    )


@router.post("/logout")
async def logout(admin: Admin = Depends(get_current_admin)):
    return success_response(message="logged out")


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.old_password, admin.password_hash):
        return error_response("旧密码错误", status_code=400, code="INVALID_OLD_PASSWORD")

    if len(req.new_password) < 6:
        return error_response("密码长度不能少于6位", status_code=422, code="PASSWORD_TOO_SHORT")

    admin.password_hash = hash_password(req.new_password)
    admin.password_changed_at = datetime.now(timezone.utc)
    await db.commit()

    return success_response(message="密码修改成功")

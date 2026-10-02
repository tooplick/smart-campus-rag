"""模型配置管理 API:多套 profile 的增删改查与启用切换(读写 app-config.yaml)。

密钥脱敏:list 返回 api_key_configured 布尔,不回传 api_key 明文;
修改 api_key 时整体覆盖,留空表示不改。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import get_current_admin
from app.core.app_config import MODEL_TYPES, AppConfigError, AppConfigStore, get_app_config
from app.models.admin import Admin
from app.services.model_swap import OPTIONAL_TYPES, apply_model_change
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/admin/model-profiles", tags=["model-profiles"])


class ProfileCreate(BaseModel):
    type: str
    name: str = Field(min_length=1, max_length=100)
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class ProfileUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class ActivePayload(BaseModel):
    type: str
    name: str | None = None


def _view(store: AppConfigStore, model_type: str) -> dict:
    raw = store.list_profiles(model_type)
    profiles = {
        name: {
            "base_url": p.get("base_url", ""),
            "model": p.get("model", ""),
            "api_key_configured": bool(p.get("api_key")),
        }
        for name, p in raw["profiles"].items()
    }
    return {"active": raw["active"], "profiles": profiles}


@router.get("")
async def list_model_profiles(
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    try:
        return success_response(data={t: _view(store, t) for t in MODEL_TYPES})
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.post("")
async def create_model_profile(
    req: ProfileCreate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    try:
        will_activate = store.list_profiles(req.type)["active"] is None
        if will_activate and (not req.base_url.strip() or not req.model.strip()):
            # 首个配置会被自动启用:先校验完整性,避免「写入成功却激活失败」的半成品
            return error_response("启用配置需填写 base_url 与 model", status_code=422, code="INCOMPLETE_PROFILE")
        store.add_profile(req.type, req.name, {"base_url": req.base_url, "api_key": req.api_key, "model": req.model})
        if will_activate:
            # 该类型尚无启用配置时自动启用,省一次手动切换;仅启用(改变运行实例)时才热替换
            store.set_active(req.type, req.name)
            apply_model_change(request.app, req.type, store)
        return success_response(data=_view(store, req.type), message="已添加")
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.put("/{model_type}/{name}")
async def update_model_profile(
    model_type: str,
    name: str,
    req: ProfileUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    try:
        fields = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v not in (None, "")}
        store.update_profile(model_type, name, fields)
        if store.list_profiles(model_type)["active"] == name:
            apply_model_change(request.app, model_type, store)
        return success_response(data=_view(store, model_type), message="已保存")
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.delete("/{model_type}/{name}")
async def delete_model_profile(
    model_type: str,
    name: str,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    try:
        store.delete_profile(model_type, name)
        return success_response(data=_view(store, model_type), message="已删除")
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")


@router.put("/active")
async def set_active_profile(
    req: ActivePayload,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    store: AppConfigStore = Depends(get_app_config),
):
    if req.type not in MODEL_TYPES:
        return error_response(f"无效的模型类型: {req.type}", status_code=422, code="INVALID_MODEL_TYPE")
    if req.name is None and req.type not in OPTIONAL_TYPES:
        return error_response(f"{req.type} 不支持停用", status_code=422, code="CANNOT_DISABLE")
    try:
        store.set_active(req.type, req.name)
        apply_model_change(request.app, req.type, store)
        return success_response(data=_view(store, req.type), message="已切换")
    except AppConfigError as e:
        return error_response(str(e), status_code=422, code="APP_CONFIG_ERROR")

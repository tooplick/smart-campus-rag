"""应用配置文件(app-config.yaml)读写。

约定(用户定):所有配置存储入配置文件——模型配置(models 区,多套 profile + active 指针)
与 RAG 参数(rag 区)。system_configs 表退役,不再读写。文件是唯一事实源,手编文件同样有效,
程序内「读改写」全程持可重入锁。
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import yaml

MODEL_TYPES = ("llm", "embedding", "vision", "rerank")
PROFILE_FIELDS = ("base_url", "api_key", "model")

# 与 RAGConfig 默认值一致;文件缺项回退此处
# 注意 request_timeout 必须写 float(60.0):_coerce_rag_value 按此值类型强转
RAG_DEFAULTS: dict[str, int | float] = {
    "chunk_size": 600,
    "chunk_overlap": 80,
    "candidate_top_k": 8,
    "final_top_k": 5,
    "similarity_threshold": 0.6,
    "vector_weight": 0.7,
    "auto_keywords": 5,
    "auto_questions": 2,
    "temperature": 0.2,
    "max_tokens": 2048,
    # 可选运行参数(设置页「运行参数」区可改,保存即热更新)
    "embedding_batch_size": 32,
    "embedding_max_retries": 3,
    "llm_max_retries": 3,
    "request_timeout": 120.0,
}


class AppConfigError(ValueError):
    """配置文件操作错误(参数非法、名称冲突等)。"""


def write_config(path: str | Path, data: dict[str, Any]) -> None:
    """原子写配置:同目录临时文件 + os.replace,避免写一半被杀/磁盘满留损坏文件。

    AppConfigStore 与迁移脚本共用(迁移 --force 下先截断既有文件同样有此风险)。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _coerce_rag_value(key: str, value: Any) -> int | float:
    """按 RAG_DEFAULTS 默认值类型强转;坏值抛 AppConfigError 而非裸 ValueError。"""
    try:
        return type(RAG_DEFAULTS[key])(value)  # type: ignore[return-value]
    except (ValueError, TypeError) as e:
        raise AppConfigError(f"配置值类型非法: {key}") from e


class AppConfigStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    # ---------- 底层读写 ----------
    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"models": {}, "rag": {}}
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise AppConfigError("配置文件 YAML 解析失败") from e
        except (UnicodeDecodeError, OSError) as e:
            # 非 UTF-8 字节 / 读盘失败:与 YAML 解析失败同档处理,统一报「配置文件读取失败」
            raise AppConfigError("配置文件读取失败") from e
        if not isinstance(data, dict):
            raise AppConfigError("配置文件根节点必须是映射")
        models = data.setdefault("models", {})
        if not isinstance(models, dict):
            raise AppConfigError("models 必须是映射")
        rag = data.setdefault("rag", {})
        if not isinstance(rag, dict):
            raise AppConfigError("rag 必须是映射")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        write_config(self.path, data)

    def _type_section(self, data: dict[str, Any], model_type: str) -> dict[str, Any]:
        if model_type not in MODEL_TYPES:
            raise AppConfigError(f"无效的模型类型: {model_type}")
        section = data["models"].setdefault(model_type, {})
        if not isinstance(section, dict):
            raise AppConfigError(f"models.{model_type} 必须是映射")
        profiles = section.setdefault("profiles", {})
        if not isinstance(profiles, dict):
            raise AppConfigError(f"models.{model_type}.profiles 必须是映射")
        return section

    @staticmethod
    def _check_name(name: str) -> str:
        name = (name or "").strip()
        if not name:
            raise AppConfigError("配置名不能为空")
        return name

    @staticmethod
    def _check_fields(fields: dict[str, Any]) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, value in (fields or {}).items():
            if key not in PROFILE_FIELDS:
                raise AppConfigError(f"不支持的配置字段: {key}")
            if value is not None:
                out[key] = str(value)
        return out

    @staticmethod
    def _profile_view(name: str, profile: dict[str, Any]) -> dict[str, str]:
        return {"name": name, **{k: str(profile.get(k, "")) for k in PROFILE_FIELDS}}

    @staticmethod
    def _check_complete(profile: dict[str, Any]) -> None:
        """启用前校验完整性:base_url 与 model 必填(api_key 允许为空,部分服务无需密钥)。

        空 base_url/model 的 profile 一旦被启用,会被热替换构造成无意义的 Provider
        (相对 URL 请求、提问必失败),故在启用这一唯一入口拦截。
        """
        if not str(profile.get("base_url", "")).strip():
            raise AppConfigError("配置不完整:缺少 base_url")
        if not str(profile.get("model", "")).strip():
            raise AppConfigError("配置不完整:缺少 model")

    # ---------- 模型配置 ----------
    def get_active_profile(self, model_type: str) -> dict[str, str] | None:
        """返回启用配置 {name, base_url, api_key, model};未启用返回 None。"""
        with self._lock:
            section = self._type_section(self._read(), model_type)
            name = section.get("active")
            profile = section["profiles"].get(name) if name else None
            if not profile:
                return None
            return self._profile_view(name, profile)

    def get_profile(self, model_type: str, name: str) -> dict[str, str]:
        name = self._check_name(name)
        with self._lock:
            section = self._type_section(self._read(), model_type)
            profile = section["profiles"].get(name)
            if not profile:
                raise AppConfigError(f"配置不存在: {name}")
            return self._profile_view(name, profile)

    def list_profiles(self, model_type: str) -> dict[str, Any]:
        with self._lock:
            section = self._type_section(self._read(), model_type)
            return {"active": section.get("active"), "profiles": dict(section["profiles"])}

    def add_profile(self, model_type: str, name: str, fields: dict[str, Any]) -> dict[str, str]:
        name = self._check_name(name)
        clean = self._check_fields(fields)
        with self._lock:
            data = self._read()
            section = self._type_section(data, model_type)
            if name in section["profiles"]:
                raise AppConfigError(f"配置名已存在: {name}")
            profile = {k: clean.get(k, "") for k in PROFILE_FIELDS}
            section["profiles"][name] = profile
            self._write(data)
            return self._profile_view(name, profile)

    def update_profile(self, model_type: str, name: str, fields: dict[str, Any]) -> dict[str, str]:
        name = self._check_name(name)
        clean = self._check_fields(fields)
        with self._lock:
            data = self._read()
            section = self._type_section(data, model_type)
            profile = section["profiles"].get(name)
            if not profile:
                raise AppConfigError(f"配置不存在: {name}")
            profile.update(clean)
            self._write(data)
            return self._profile_view(name, profile)

    def delete_profile(self, model_type: str, name: str) -> None:
        name = self._check_name(name)
        with self._lock:
            data = self._read()
            section = self._type_section(data, model_type)
            if name not in section["profiles"]:
                raise AppConfigError(f"配置不存在: {name}")
            if section.get("active") == name:
                raise AppConfigError("不能删除当前启用的配置,请先切换到其他配置")
            del section["profiles"][name]
            self._write(data)

    def set_active(self, model_type: str, name: str | None) -> dict[str, str] | None:
        """切换启用配置;name 为 None 表示停用。返回切换后的启用配置。"""
        with self._lock:
            data = self._read()
            section = self._type_section(data, model_type)
            if name is None:
                section["active"] = None
                self._write(data)
                return None
            name = self._check_name(name)
            profile = section["profiles"].get(name)
            if not profile:
                raise AppConfigError(f"配置不存在: {name}")
            self._check_complete(profile)
            section["active"] = name
            self._write(data)
            return self._profile_view(name, profile)

    # ---------- RAG 参数 ----------
    def get_rag(self) -> dict[str, int | float]:
        with self._lock:
            data = self._read()
            rag = data["rag"] if isinstance(data["rag"], dict) else {}
            out = dict(RAG_DEFAULTS)
            for key in RAG_DEFAULTS:
                if rag.get(key) is not None:
                    out[key] = _coerce_rag_value(key, rag[key])
            return out

    def save_rag(self, updates: dict[str, int | float]) -> dict[str, int | float]:
        with self._lock:
            if not updates:
                # 空更新直接返回:不重写文件,避免手编注释/格式被无谓覆盖
                return self.get_rag()
            data = self._read()
            rag = data["rag"] if isinstance(data["rag"], dict) else {}
            for key, value in updates.items():
                if key not in RAG_DEFAULTS:
                    raise AppConfigError(f"不支持的 RAG 参数: {key}")
                rag[key] = _coerce_rag_value(key, value)
            data["rag"] = rag
            self._write(data)
            return self.get_rag()


def build_config_from_rows(rows: list[tuple[str, str | None, str]]) -> dict[str, Any]:
    """把 system_configs 的 (config_key, config_value, value_type) 行集转成 app-config.yaml 结构。

    model.{type}.base_url/api_key/model → profiles.default;
    model.{type}.enabled=false 时 active 置 null;rag.* 仅收 RAG_DEFAULTS 白名单键。
    """
    config: dict[str, Any] = {"models": {}, "rag": {}}
    model_vals: dict[str, dict[str, str]] = {t: {} for t in MODEL_TYPES}
    enabled: dict[str, bool] = {t: True for t in MODEL_TYPES}
    for key, value, _value_type in rows:
        if value is None:
            # NULL config_value 直接跳过:否则 str(None) 会写成 "None" 污染 profile
            continue
        if key.startswith("model."):
            parts = key.split(".")
            if len(parts) != 3:
                continue
            _, mtype, field = parts
            if mtype not in model_vals or field not in (*PROFILE_FIELDS, "enabled"):
                continue
            if field == "enabled":
                enabled[mtype] = str(value).lower() == "true"
            else:
                model_vals[mtype][field] = str(value)
        elif key.startswith("rag."):
            rkey = key[len("rag."):]
            if rkey in RAG_DEFAULTS:
                # 走 _coerce_rag_value 统一强转:坏值抛 AppConfigError 而非裸 ValueError
                config["rag"][rkey] = _coerce_rag_value(rkey, value)
    for mtype in MODEL_TYPES:
        vals = model_vals[mtype]
        if not vals:
            continue
        config["models"][mtype] = {
            "active": "default" if enabled[mtype] else None,
            "profiles": {"default": {f: vals.get(f, "") for f in PROFILE_FIELDS}},
        }
    return config


_store: AppConfigStore | None = None
_store_lock = threading.Lock()


def get_app_config() -> AppConfigStore:
    """FastAPI 依赖:进程级单例(路径取 Settings.APP_CONFIG_PATH),双重检查加锁防并发建两个实例。"""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                from app.core.config import get_settings
                _store = AppConfigStore(get_settings().APP_CONFIG_PATH)
    return _store

"""模型配置热替换:把 app-config.yaml 当前启用配置构建为 Provider 实例,
就地替换 RAGPipeline / DocumentWorker 上的属性——切换即生效,无需重启。

背景:lifespan 启动时构建 Provider 一次;设置页切换/修改配置后调用本模块同步运行时。
对象属性赋值在 asyncio 单线程内安全;worker 下一轮处理自然用到新实例。
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_config import MODEL_TYPES, AppConfigError, AppConfigStore
from app.rag.embedding.openai_compatible import OpenAICompatibleEmbedding
from app.rag.llm.openai_compatible import OpenAICompatibleLLM
from app.rag.rerank.openai_compatible import OpenAICompatibleRerank

# 可停用的类型;embedding/llm 是管线/worker 必需项
OPTIONAL_TYPES = ("vision", "rerank")

logger = logging.getLogger(__name__)


def apply_model_change(app: FastAPI, model_type: str, store: AppConfigStore) -> None:
    if model_type not in MODEL_TYPES:
        raise AppConfigError(f"无效的模型类型: {model_type}")
    profile = store.get_active_profile(model_type)
    if profile is None and model_type not in OPTIONAL_TYPES:
        # embedding/llm 是管线/worker 必需项,必须启用一个配置;vision/rerank 可停用
        raise AppConfigError(f"{model_type} 必须启用一个配置")
    # 来源整体取用:app.state 优先,缺失则整体回退 main.py 模块全局;
    # 两者都不可达则告警返回——不与另一来源混搭(避免 pipeline 新实例、worker 旧实例的错配)
    state_pipeline = getattr(app.state, "rag_pipeline", None)
    state_worker = getattr(app.state, "document_worker", None)
    if state_pipeline is not None and state_worker is not None:
        pipeline, worker = state_pipeline, state_worker
    else:
        # 兼容回退:main.py 已把实例挂到 app.state(优先走上面分支);此分支保留给
        # 未挂载 app.state 的场景(如独立单测),不要删除——删了会破坏回退用例
        import app.main as main_module
        main_pipeline = getattr(main_module, "rag_pipeline", None)
        main_worker = getattr(main_module, "document_worker", None)
        if main_pipeline is None or main_worker is None:
            logger.warning("未找到运行中的管线/worker,模型切换未实际生效")
            return
        pipeline, worker = main_pipeline, main_worker
    rag_config = getattr(app.state, "rag_config", None)

    if model_type == "embedding":
        embedding = OpenAICompatibleEmbedding(
            base_url=profile["base_url"],
            api_key=profile["api_key"],
            model=profile["model"],
            batch_size=getattr(rag_config, "embedding_batch_size", 32),
        )
        if pipeline is not None:
            pipeline.embedding = embedding
        if worker is not None:
            worker.embedding = embedding
    elif model_type == "llm":
        llm = OpenAICompatibleLLM(
            base_url=profile["base_url"],
            api_key=profile["api_key"],
            model=profile["model"],
        )
        if pipeline is not None:
            pipeline.llm = llm
        if worker is not None:
            worker.llm = llm
    elif model_type == "rerank":
        provider = None
        if profile is not None:
            provider = OpenAICompatibleRerank(
                base_url=profile["base_url"],
                api_key=profile["api_key"],
                model=profile["model"],
            )
        if pipeline is not None:
            pipeline.rerank = provider
    elif model_type == "vision":
        vision_config = None
        if profile is not None:
            vision_config = {
                "base_url": profile["base_url"],
                "api_key": profile["api_key"],
                "model": profile["model"],
            }
        if worker is not None:
            worker.vision_config = vision_config

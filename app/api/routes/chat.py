from __future__ import annotations

import json
import uuid
import logging

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import Conversation
from app.rag.errors import RAGStageError
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_rag_pipeline():
    from app.main import rag_pipeline
    return rag_pipeline


def _short(exc: BaseException, limit: int = 160) -> str:
    """异常压成单行短文案(SSE 单事件内可读)。"""
    text = " ".join(str(exc).split()) or exc.__class__.__name__
    return text[:limit]


def _classify_chat_error(exc: Exception) -> tuple[str, str]:
    """把底层异常翻译成错误码 + 细化文案,定位到具体模型配置项。

    阶段(embedding / llm)由 RAGStageError 提供,原因由 httpx 异常类型判定:
    连接失败 → base_url,401/403 → API Key,404 → 模型名。
    """
    stage = "模型"
    cause: BaseException = exc
    if isinstance(exc, RAGStageError):
        stage = {"embedding": "Embedding", "llm": "对话 LLM"}.get(exc.stage, "模型")
        cause = exc.cause

    if isinstance(cause, httpx.HTTPStatusError):
        status = cause.response.status_code
        if status in (401, 403):
            return (
                "MODEL_AUTH_ERROR",
                f"{stage} 服务鉴权失败(HTTP {status}):API Key 无效或无权限,"
                f"请到「设置 → 模型配置」核对该模型的 API Key",
            )
        if status == 404:
            return (
                "MODEL_NOT_FOUND",
                f"{stage} 模型名不存在(HTTP 404):请到「设置 → 模型配置」核对模型名拼写,"
                f"或确认服务商已提供该模型",
            )
        if status == 429:
            return "MODEL_RATE_LIMITED", f"{stage} 服务限流(HTTP 429),请稍后重试"
        body = _short(cause, 80)
        return (
            "MODEL_HTTP_ERROR",
            f"{stage} 服务返回 HTTP {status}:{body},请到「设置 → 模型配置」核对 base_url 与模型名",
        )
    if isinstance(cause, (httpx.TimeoutException, httpx.NetworkError, ConnectionError, OSError)):
        return (
            "MODEL_CONNECT_ERROR",
            f"无法连接 {stage} 服务:{_short(cause)},请到「设置 → 模型配置」核对 base_url 是否正确、"
            f"对应模型服务是否已启动",
        )
    return "LLM_ERROR", f"{stage} 调用失败:{_short(cause)}"


@router.get("/session")
async def get_session():
    """Generate anonymous client session ID."""
    return success_response(data={"client_id": str(uuid.uuid4())})


@router.post("")
async def chat(
    req: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public chat endpoint with SSE streaming support."""
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        return error_response("缺少 X-Client-ID 头", status_code=401, code="MISSING_CLIENT_ID")

    message = req.message.strip()
    if not message:
        return error_response("消息不能为空", status_code=400, code="EMPTY_MESSAGE")
    if len(message) > 2000:
        return error_response("消息过长，最多2000字符", status_code=422, code="MESSAGE_TOO_LONG")

    chat_service = ChatService()

    # Validate knowledge base
    valid, err_msg = await chat_service.validate_knowledge_base(db, req.knowledge_base_id)
    if not valid:
        return error_response(err_msg, status_code=400, code="INVALID_KNOWLEDGE_BASE")

    # Handle conversation
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        conv = Conversation(
            id=conversation_id,
            client_id=client_id,
            knowledge_base_id=req.knowledge_base_id,
            title=message[:50],
        )
        db.add(conv)
        await db.flush()
    else:
        conv = await db.get(Conversation, conversation_id)
        if not conv or conv.client_id != client_id:
            return error_response("会话不存在或无权访问", status_code=404, code="CONVERSATION_NOT_FOUND")

    # Get history for multi-turn
    history = await chat_service.get_conversation_history(db, conversation_id)
    turn_index = await chat_service.get_conversation_turn_index(db, conversation_id)

    rag_pipeline = _get_rag_pipeline()
    if not rag_pipeline:
        return error_response(
            "RAG 管道未就绪:app-config.yaml 缺少可用的 embedding/llm 启用配置,"
            "或启动时配置校验失败,请到「设置 → 模型配置」启用完整配置后重启服务",
            status_code=503,
            code="RAG_NOT_READY",
        )

    message_id = str(uuid.uuid4())

    if req.stream:
        async def event_stream():
            yield f"event: start\ndata: {json.dumps({'message_id': message_id, 'conversation_id': conversation_id})}\n\n"

            try:
                rag_answer, stream_iter = await rag_pipeline.answer(
                    question=message,
                    knowledge_base_id=req.knowledge_base_id,
                    db=db,
                    history=history,
                    stream=True,
                )

                full_answer = []
                async for token in stream_iter:
                    full_answer.append(token)
                    yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

                rag_answer.answer = "".join(full_answer)

                # Build citations for sources event
                sources = []
                for i, c in enumerate(rag_answer.citations):
                    sources.append({
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "filename": c.filename,
                        "page_number": c.page_start,
                        "section_title": c.section_title,
                        "content": c.content,
                        "similarity_score": round(c.score, 4),
                        "source_order": i + 1,
                    })

                yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"

                # Save QA record
                qa_record = await chat_service.save_qa_record(
                    db=db,
                    conversation_id=conversation_id,
                    turn_index=turn_index,
                    knowledge_base_id=req.knowledge_base_id,
                    question=message,
                    rag_answer=rag_answer,
                    message_id=message_id,
                )
                await db.commit()

                yield f"event: done\ndata: {json.dumps({'qa_record_id': qa_record.id, 'conversation_id': conversation_id, 'message_id': message_id})}\n\n"

            except Exception as e:
                logger.exception("Chat SSE error")
                err_code, err_msg = _classify_chat_error(e)
                yield f"event: error\ndata: {json.dumps({'code': err_code, 'message': err_msg}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming
        try:
            rag_answer = await rag_pipeline.answer(
                question=message,
                knowledge_base_id=req.knowledge_base_id,
                db=db,
                history=history,
                stream=False,
            )

            sources = []
            for i, c in enumerate(rag_answer.citations):
                sources.append({
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "filename": c.filename,
                    "page_number": c.page_start,
                    "section_title": c.section_title,
                    "content": c.content,
                    "similarity_score": round(c.score, 4),
                    "source_order": i + 1,
                })

            qa_record = await chat_service.save_qa_record(
                db=db,
                conversation_id=conversation_id,
                turn_index=turn_index,
                knowledge_base_id=req.knowledge_base_id,
                question=message,
                rag_answer=rag_answer,
                message_id=message_id,
            )
            await db.commit()

            return success_response(data={
                "message_id": message_id,
                "conversation_id": conversation_id,
                "answer": rag_answer.answer,
                "sources": sources,
                "qa_record_id": qa_record.id,
                "model": rag_answer.model_name,
            })

        except Exception as e:
            logger.exception("Chat error")
            err_code, err_msg = _classify_chat_error(e)
            return error_response(err_msg, status_code=500, code=err_code)

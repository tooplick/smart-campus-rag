from __future__ import annotations

import json
import uuid
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.chat_service import ChatService
from app.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_rag_pipeline():
    """Lazy import to avoid circular dependency."""
    from app.main import rag_pipeline
    return rag_pipeline


@router.post("")
async def chat(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    question = body.get("message", "").strip()
    if not question:
        return error_response("消息不能为空")

    if len(question) > 2000:
        return error_response("消息过长，最多 2000 字符")

    knowledge_base_id = body.get("knowledge_base_id")
    conversation_id = body.get("conversation_id") or uuid.uuid4().hex
    stream = body.get("stream", False)

    chat_service = ChatService()

    # Validate knowledge base
    valid, err_msg = await chat_service.validate_knowledge_base(db, knowledge_base_id)
    if not valid:
        return error_response(err_msg)

    # Get history
    history = await chat_service.get_conversation_history(db, conversation_id)
    turn_index = await chat_service.get_conversation_turn_index(db, conversation_id)

    rag_pipeline = _get_rag_pipeline()

    if stream:
        async def event_stream():
            # Start event
            yield f"event: start\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"

            try:
                rag_answer, token_iter = await rag_pipeline.answer(
                    question,
                    knowledge_base_id,
                    db,
                    history=history,
                    stream=True,
                )

                # Stream tokens
                async for token in token_iter:
                    yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

                # Sources event
                sources = [
                    {
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "filename": c.filename,
                        "page_start": c.page_start,
                        "page_end": c.page_end,
                        "section_title": c.section_title,
                        "content": c.content,
                        "score": round(c.score, 4),
                    }
                    for c in rag_answer.citations
                ]
                yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"

                # Save QA record
                await chat_service.save_qa_record(
                    db, conversation_id, turn_index, knowledge_base_id or 0, question, rag_answer
                )

                # Done event
                yield f"event: done\ndata: {json.dumps({'latency_ms': rag_answer.latency_ms})}\n\n"

            except Exception as e:
                logger.exception("Chat stream error")
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-streaming
    try:
        rag_answer = await rag_pipeline.answer(
            question,
            knowledge_base_id,
            db,
            history=history,
            stream=False,
        )

        await chat_service.save_qa_record(
            db, conversation_id, turn_index, knowledge_base_id or 0, question, rag_answer
        )

        return success_response({
            "conversation_id": conversation_id,
            "answer": rag_answer.answer,
            "sources": [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "filename": c.filename,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "section_title": c.section_title,
                    "content": c.content,
                    "score": round(c.score, 4),
                }
                for c in rag_answer.citations
            ],
            "model_name": rag_answer.model_name,
            "latency_ms": rag_answer.latency_ms,
        })

    except Exception as e:
        logger.exception("Chat error")
        return error_response(f"问答失败: {str(e)}", status_code=500)

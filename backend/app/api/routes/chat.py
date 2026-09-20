from __future__ import annotations

import json
import uuid
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import Conversation
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_rag_pipeline():
    from app.main import rag_pipeline
    return rag_pipeline


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
        return error_response("RAG 管道未就绪", status_code=503, code="RAG_NOT_READY")

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
                yield f"event: error\ndata: {json.dumps({'code': 'LLM_ERROR', 'message': str(e)[:200]})}\n\n"

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
            return error_response("回答生成失败", status_code=500, code="LLM_ERROR")

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.qa_record import QaRecord
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.utils.response import success_response, error_response, paginated_response

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        return error_response("缺少 X-Client-ID 头", status_code=401, code="MISSING_CLIENT_ID")

    page = max(1, page)
    page_size = max(1, min(100, page_size))

    base = Conversation.client_id == client_id
    count_stmt = select(func.count(Conversation.id)).where(base, Conversation.is_deleted == False)
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = (
        select(Conversation)
        .where(base, Conversation.is_deleted == False)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    convs = result.scalars().all()

    items = []
    for c in convs:
        items.append({
            "id": c.id,
            "knowledge_base_id": c.knowledge_base_id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return paginated_response(items, page, page_size, total)


@router.post("")
async def create_conversation(
    req: ConversationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        return error_response("缺少 X-Client-ID 头", status_code=401, code="MISSING_CLIENT_ID")

    conv = Conversation(
        id=str(uuid.uuid4()),
        client_id=client_id,
        knowledge_base_id=req.knowledge_base_id,
        title=req.title,
    )
    db.add(conv)
    await db.flush()
    await db.commit()

    return success_response(
        data={
            "id": conv.id,
            "knowledge_base_id": conv.knowledge_base_id,
            "title": conv.title,
        },
        message="created",
        status_code=201,
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        return error_response("缺少 X-Client-ID 头", status_code=401, code="MISSING_CLIENT_ID")

    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.is_deleted or conv.client_id != client_id:
        return error_response("会话不存在", status_code=404, code="CONVERSATION_NOT_FOUND")

    # Get messages
    stmt = (
        select(QaRecord)
        .where(QaRecord.conversation_id == conversation_id)
        .order_by(QaRecord.turn_index.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages = []
    for r in records:
        messages.append({
            "role": "user",
            "content": r.question,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
        messages.append({
            "role": "assistant",
            "content": r.answer,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return success_response(data={
        "id": conv.id,
        "knowledge_base_id": conv.knowledge_base_id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "messages": messages,
    })


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        return error_response("缺少 X-Client-ID 头", status_code=401, code="MISSING_CLIENT_ID")

    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.is_deleted or conv.client_id != client_id:
        return error_response("会话不存在", status_code=404, code="CONVERSATION_NOT_FOUND")

    if req.title is not None:
        conv.title = req.title

    await db.commit()

    return success_response(data={
        "id": conv.id,
        "knowledge_base_id": conv.knowledge_base_id,
        "title": conv.title,
    })


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_id = request.headers.get("X-Client-ID")
    if not client_id:
        return error_response("缺少 X-Client-ID 头", status_code=401, code="MISSING_CLIENT_ID")

    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.is_deleted or conv.client_id != client_id:
        return error_response("会话不存在", status_code=404, code="CONVERSATION_NOT_FOUND")

    conv.is_deleted = True
    await db.commit()

    return success_response(message="会话已删除")

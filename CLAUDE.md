# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

You must use Chinese (Simplified) for all responses, including code commdocumentation. Do not use English.

## Project Overview

Smart Campus RAG — a campus knowledge base Q&A system using RAG (Retrieval-Augmented Generation). Admins upload documents (PDF/DOCX/TXT), the system parses, chunks, embeds them into Qdrant, and users ask questions answered by LLM with source citations.

## Tech Stack

- **Frontend:** Vue 3 + TypeScript + Vite + Tailwind CSS v4 + shadcn-vue + Pinia + Vue Router + Lucide Icons + markdown-it
- **Backend:** FastAPI + SQLAlchemy (async) + Pydantic v2
- **Database:** PostgreSQL (business data), Qdrant (vector embeddings)
- **Models:** OpenAI-compatible API for Embedding, LLM, and Vision
- **Auth:** JWT (admin-only, single admin, no user registration)

## Common Commands

### Backend (run from project root)

```bash
# Install dependencies (uv manages .venv automatically)
uv sync

# Run dev server (port 8000 is occupied on Windows; use 8001)
uv run uvicorn app.main:app --reload --port 8001

# Seed initial admin (admin/admin)
uv run python scripts/create-admin.py

# Initialize Qdrant collection (run once after starting Qdrant)
uv run python scripts/init-qdrant.py

# Run database migrations
psql -U postgres -d campus_rag -f scripts/migrate-001-add-conversations-and-qa-fields.sql
```

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev        # dev server on :5173
npm run build      # production build
```

### Docker (from project root)

```bash
docker compose up -d                          # start all services
docker compose up -d postgres qdrant          # start only databases
docker compose exec postgres psql -U postgres -d campus_rag  # connect to DB
docker compose ps                             # check status
```

## Architecture

### API Response Format

All business APIs (`/api/*`) wrap responses in:
```json
{"success": true, "data": {}, "message": "success"}
```
OpenAI-compatible APIs (`/v1/*`) use standard OpenAI response format.

### Backend Layers

```
API Route (app/api/routes/)
    ↓
Service (app/services/) — business logic
    ↓
RAG Pipeline (app/rag/) — parsing, chunking, embedding, retrieval, LLM
    ↓
External: PostgreSQL / Qdrant / OpenAI-compatible models
```

Backend code is at project root: `app/`, `scripts/`, `tests/`, `uploads/`, `requirements.txt`

### RAG Module Structure (`app/rag/`)

The RAG core is modular with Provider abstraction — all external AI calls go through OpenAI-compatible protocol:

```
app/rag/
├── pipeline.py          # RAGPipeline — main entry point
├── config.py            # RAGConfig dataclass (chunk_size, top_k, threshold, etc.)
├── models/blocks.py     # ContentBlock, DocumentChunkData, RetrievalResult, Citation, RagAnswer
├── parser/              # BaseParser → TxtParser, PdfParser
├── chunker/             # chunk_blocks() — sentence-level splitting with overlap
├── embedding/           # EmbeddingProvider protocol → OpenAICompatibleEmbedding
├── llm/                 # LLMProvider protocol → OpenAICompatibleLLM (supports streaming)
├── retriever/           # Retriever protocol → QdrantRetriever (with knowledge_base_id filter)
├── context/builder.py   # build_context() — formats retrieval results as [来源 N] blocks
├── prompt/campus_qa.py  # System prompt + build_messages()
└── citation/            # build_citations() — fetches document filenames from DB
```

**Ingestion path:** Parser → ContentBlock → Chunker → DocumentChunk[] → PostgreSQL → Embedding → Qdrant

**Query path:** Question → Embedding → Qdrant search (knowledge_base_id filter) → Top-K → Context → LLM → Answer + Citation

### Document Worker

Background worker (`app/services/worker_service.py`) processes uploaded documents:
- Polls for `pending` documents using `FOR UPDATE SKIP LOCKED`
- Pipeline: parse → chunk → save to PostgreSQL → embed → upsert to Qdrant
- Updates document status/progress (10/30/40/60/80/100)
- Max 3 retry attempts; failed documents marked as `failed`

### Chat & Conversation API

`POST /api/chat` supports both streaming (SSE) and non-streaming. Requires `X-Client-ID` header for anonymous session tracking.
- `GET /api/chat/session` — generates anonymous client_id
- SSE events: `start` (with message_id + conversation_id), `token`, `sources`, `done`, `error`
- Auto-creates conversation on first message; subsequent messages use `conversation_id`
- Validates knowledge base has completed documents before querying

`/api/conversations` — CRUD for user conversations (identified by `X-Client-ID`):
- List, create, get (with messages), rename, soft-delete
- No admin auth required; access controlled by client_id ownership

### Admin API

`/api/admin` — admin-only endpoints (JWT required):
- `GET /dashboard` — statistics, QA trends, document status distribution
- `GET/PUT /rag-config` — RAG pipeline parameters (chunk_size, top_k, threshold, etc.)
- `GET/PUT /models/{type}` — model config (llm/embedding/vision) with `POST /test` endpoint
- `GET /qa-logs`, `GET /qa-logs/{id}` — QA history with retrieval details and sources

### Health API

- `GET /api/health` — basic liveness check
- `GET /api/ready` — readiness check (PostgreSQL, Qdrant, LLM, Embedding status)

### Key Patterns

- **Async everywhere:** SQLAlchemy uses `AsyncSession` with `asyncpg`. All DB operations are `async/await`.
- **Pydantic schemas separate from models:** `app/schemas/` for API request/response, `app/models/` for SQLAlchemy ORM.
- **Config via environment:** `app/core/config.py` reads from `.env` using `pydantic-settings`. Model configs (embedding/LLM base_url, api_key, model) stored in `system_configs` table.
- **Chunk ID = Qdrant Point ID:** `document_chunks.id` is the single source of truth for vector identity. Chunks are immutable; reprocessing creates new IDs.
- **Single admin:** Only one admin user (id=1). First login forces password change.
- **bcrypt direct:** Uses `bcrypt` library directly (not `passlib`) for password hashing due to passlib/bcrypt compatibility issues.
- **Provider abstraction:** Embedding, LLM, Vision all use OpenAI-compatible protocol via httpx. Replaceable by changing `system_configs` DB entries.
- **Timezone-aware datetimes:** All models use `datetime.now(timezone.utc)` with `DateTime(timezone=True)`. Never use `datetime.utcnow` (deprecated in Python 3.12+).
- **Soft delete:** Conversations use `is_deleted` flag. Hard delete for documents/knowledge bases.

### Database Tables

`admin`, `knowledge_bases`, `documents`, `document_chunks`, `conversations`, `qa_records`, `qa_sources`, `system_configs`

- `conversations` — multi-turn chat sessions, identified by UUID `id`, scoped by `client_id`
- `qa_records` — stores each Q&A turn with RAG params, latency breakdown, and token counts
- Documents table includes worker fields: `locked_at`, `locked_by`, `attempt_count`

### RAG Pipeline Flow

```
Upload → Parser → Content Blocks → (Vision+OCR for images) → Chunker
→ document_chunks → Embedding (/v1/embeddings) → Qdrant upsert
```

Retrieval: `Question → Embedding → Qdrant filter by knowledge_base_id → Top-K → Similarity threshold → Context Builder → LLM → Citation`

Default params: candidate_top_k=8, final_top_k=5, similarity_threshold=0.60, chunk_size=600, overlap=80

### SSE Streaming

Chat API uses Server-Sent Events with event types: `start`, `token`, `sources`, `done`, `error`.

### Frontend Architecture

```
frontend/src/
├── api/            # HTTP clients (one file per domain)
│   ├── client.js   # Axios instance with JWT interceptor (for admin APIs)
│   ├── chat.js     # Raw fetch + ReadableStream for SSE (uses X-Client-ID)
│   └── conversations.js  # Raw fetch with X-Client-ID (public endpoints)
├── config/
│   └── navigation.ts  # Main navigation config (唯一的导航数据源)
├── stores/         # Pinia stores
│   ├── auth.js     # Login/logout, token management, localStorage persistence
│   ├── chat.js     # Conversation state, SSE streaming, message management
│   ├── knowledge.js
│   └── admin.js    # Dashboard, RAG config, model config, QA logs
├── components/
│   ├── navigation/ # AppNavigation (顶部居中胶囊导航)
│   ├── chat/       # ChatShell, ConversationSidebar, WelcomePanel, MessageList,
│   │               # UserMessage, AssistantMessage, MarkdownRenderer, CitationCard,
│   │               # SourceDrawer, ChatComposer, StreamingIndicator
│   ├── documents/  # UploadDialog (文档上传对话框)
│   ├── common/     # AppHeader (admin页面使用)
│   └── ui/         # shadcn-vue components (button, input, dialog, drawer, etc.)
├── layouts/
│   ├── AppLayout.vue    # 全局布局 (AppNavigation + slot)
│   ├── UserLayout.vue   # Header + router-view (admin页面使用)
│   └── AdminLayout.vue  # Sidebar + header + router-view
├── styles/
│   └── transitions.css  # 页面转场动画 (slide-forward/backward)
├── router/index.ts      # 路由配置 + navIndex + 自动转场判断
└── views/
    ├── Home.vue         # 首页 (Hero搜索、快速问题、统计、知识库卡片)
    ├── Console.vue      # 控制台 (统计、图表、活动)
    ├── Chat.vue         # Chat页面
    ├── Documents.vue    # 文档管理 (搜索、筛选、网格、上传)
    ├── DocumentDetail.vue # 文档详情 (概览、切片、RAG流程可视化)
    └── admin/           # 管理后台页面
```

**页面转场系统:**
- 四个一级页面形成连续水平空间: 首页(0) → 控制台(1) → Chat(2) → 文档(3)
- Router beforeEach 根据 `navIndex` 自动判断转场方向 (slide-forward/backward)
- 转场动画: 450ms, cubic-bezier(0.22, 1, 0.36, 1)

**导航系统:**
- 顶部居中悬浮胶囊导航 (AppNavigation)
- 使用 `config/navigation.ts` 作为唯一数据源
- Active indicator 带平滑移动动画 (300ms)

Two auth patterns:
- **Admin APIs** (`/api/admin/*`, `/api/knowledge-bases`, `/api/documents`): JWT via `client.js` axios interceptor, stored in `localStorage.admin_token`
- **Chat APIs** (`/api/chat`, `/api/conversations`): `X-Client-ID` header, stored in `localStorage.client_id`, no JWT required

## Environment

- **Windows 11** + Docker Desktop for databases
- Python 3.11, Node.js v24, npm
- `.env` file in project root (not committed — in `.gitignore`)
- Port 8000 occupied by Windows system process; use 8001 for local dev
- Use `@lucide/vue` for icons (not `lucide-vue-next` which is deprecated)

## Design Documents

- Full spec: `docs/plans/smart-campus-rag-development-design-v1.1.md`
- RAG core spec: `docs/plans/RAG核心技术实现设计文档-v1.0.md`
- Frontend UI/UX spec: `docs/plans/前端重构与 UIUX 完整设计规范 V3.0.md`
- API contract: `docs/plans/智能校园知识库系统_前后端_API_Contract_v1.0.md`
- Implementation plans: `docs/plans/` and `docs/superpowers/plans/`

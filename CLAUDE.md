# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## 语言

所有回复、代码注释、文档一律使用简体中文,不要使用英文。

## 项目概述

Smart Campus RAG — 校园知识库问答系统。管理员上传文档(PDF/DOCX/TXT/MD/CSV/XLSX/PPTX/HTML/图片,单文件 ≤50MB),系统解析、按模板切块、可选 LLM 入库增强后向量化入 Qdrant;用户提问走「向量+关键词混合检索 → 阈值过滤 → 可选重排 → 邻块扩展 → LLM 生成」,回答带来源引用。

- **前端:** Vue 3 + TypeScript + Vite + Tailwind CSS v4 + shadcn-vue + Pinia + markdown-it
- **后端:** FastAPI + SQLAlchemy (async) + Pydantic v2
- **存储:** PostgreSQL(业务数据)+ Qdrant(向量,collection `campus_rag_chunks_v1`,1024 维 COSINE)
- **模型:** OpenAI 兼容协议(Embedding / LLM / Vision / Rerank 四类 Provider)
- **鉴权:** 管理端 JWT(单管理员,无注册);聊天端 `X-Client-ID` 匿名会话

## 常用命令

### 后端(项目根目录)

```bash
uv sync

# 开发服务器(8000 被 Windows 系统进程占用,用 8001)
uv run uvicorn app.main:app --reload --port 8001

# 初始管理员(admin/admin,首次登录强制改密)
uv run python scripts/create-admin.py

# 初始化 Qdrant 集合(一次性)
uv run python scripts/init-qdrant.py

# 建表(Base.metadata.create_all)
uv run python scripts/init-db.py

# 增量迁移
psql -U postgres -d campus_rag -f scripts/migrate-001-add-conversations-and-qa-fields.sql
psql -U postgres -d campus_rag -f scripts/migrate-002-add-chunk-template.sql
```

### 测试(独立脚本,不使用 pytest)

```bash
uv run python tests/test_chunker.py     # 任意单个测试文件直接运行,PASS/FAIL 汇总
```

- 每个 `tests/test_*.py` 自带 `__main__` 入口;HTTP 一律 `httpx.MockTransport`,不发真实请求
- 部分测试通过 `async_session` 连本地 PostgreSQL,运行前先 `docker compose up -d postgres qdrant`

### 前端(`frontend/`)

```bash
npm install
npm run dev      # :5173,vite 代理 /api → :8001
npm run build    # vue-tsc -b && vite build
npm run test     # vitest
```

### Docker

```bash
# 仅依赖容器(开发:后端/前端本机跑)
docker compose up -d postgres qdrant
docker compose exec postgres psql -U postgres -d campus_rag

# 全栈容器(生产形态:backend:8000 / frontend:5173 / nginx:80,nginx 反代见 deploy/nginx/nginx.conf)
docker compose up -d --build
```

### 配置文件

模型与 RAG 参数配置在项目根 `app-config.yaml`(模板 `app-config.yaml.example`);从旧 system_configs 迁移:

```bash
uv run python scripts/migrate-config-to-file.py
```

### 本地 Embedding 服务(必须先启动)

聊天与文档入库都依赖本机 llama.cpp 提供的 bge-m3 向量服务,未启动时全部 Embedding 调用报 `All connection attempts failed`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-embedding-server.ps1
```

- 监听 `http://127.0.0.1:8080`,对应 `app-config.yaml` 中 `models.embedding` 启用 profile 的 `base_url`;API key 随意填
- 模型文件 `%USERPROFILE%\models\bge-m3-Q8_0.gguf`,输出 1024 维,必须与 Qdrant 集合维度一致
- 服务端 `--ubatch-size` 必须 ≥ 最长输入 token 数,否则长切片报 input too large(见脚本内注释)

## 架构

### API 响应格式

所有 `/api/*` 业务接口统一包装 `{"success": true, "data": {}, "message": "success"}`(`app/utils/response.py`)。

### 后端分层

```
API Route (app/api/routes/)
    ↓
Service (app/services/) — 业务逻辑
    ↓
RAG Pipeline (app/rag/) — 解析/切块/嵌入/检索/重排/LLM
    ↓
外部: PostgreSQL / Qdrant / OpenAI 兼容模型
```

横切模块:`app/core/app_config.py`(app-config.yaml 存储:模型 profile / RAG 参数)、`app/services/model_swap.py`(切换启用配置时热替换 Provider)。

### RAG 模块结构(`app/rag/`)

```
pipeline.py          RAGPipeline — 查询主入口(同步 + SSE 流式)
config.py            RAGConfig(纯量参数,保存即热更新)
models/blocks.py     ContentBlock / DocumentChunkData / RetrievalResult / Citation / RagAnswer
parser/              dispatch.get_parser() 按扩展名分派:
                     txt·md / pdf(标题检测)/ docx / xlsx / pptx / csv / html / 图片(Vision OCR,需 vision 配置)
chunker/             chunk_blocks() — 按知识库模板切块(见下)
embedding|llm|rerank/ OpenAI 兼容 Provider(base_url 可不带 /v1,调用前统一补齐)
retriever/           qdrant(向量) + keyword(jieba+bigram → ILIKE) + fuse(加权融合) + expand(邻块)
enrichment.py        入库增强:auto-keywords / auto-questions
context|prompt|citation/ [来源 N] 上下文、校园 QA 提示词、回查文档名构建引用
```

### 查询链路(混合检索,对齐 RAGFlow)

```
问题 → 向量化
→ 向量检索 + 关键词检索(各取 candidate_top_k;向量路不设阈值)
→ 融合排序(vector_weight=0.7,单路命中保持原分)→ 按 similarity_threshold 过滤
→ 可选重排(app-config.yaml 启用 rerank 配置时,失败回退融合序)→ 截断 final_top_k
→ 邻块扩展(同文档前后各 1 块,补跨 chunk 断文)→ [来源 N] 上下文(≤4000 token)
→ LLM → 回答 + 引用;无证据则拒答
```

阈值统一在融合后过滤,保留关键词独有命中——不要改回向量路内过滤。

### 入库链路

```
上传 → 解析(dispatch)→ 按 kb.chunk_template 切块 → LLM 入库增强(关键词/候选问题)
→ document_chunks(原文纯净)→ 向量化(增强项拼入嵌入文本 embed_text_for)→ Qdrant upsert
```

- 切块模板(`knowledge_bases.chunk_template`): `general` 句级流式带重叠 / `section` 章节独立 / `qa` 问答对 / `one` 整篇(超嵌入上限回退 general)
- 增强内容只进向量文本与 metadata,入库原文保持纯净(引用展示不受污染);增强失败降级纯正文

### Document Worker(`app/services/worker_service.py`)

轮询 pending 文档(`FOR UPDATE SKIP LOCKED`),进度 10/30/40/60/80/100 逐阶段即刻提交(否则前端只见到 0→100 跳变)。MAX_ATTEMPTS=3,超限置 `failed`。「重新处理」= 重建切片:新 chunk 新 id(Chunk ID = Qdrant Point ID,切片不可变),旧切片与旧向量点一并清理。

### Chat 与会话 API

`POST /api/chat` 支持 SSE 流式与非流式,必须带 `X-Client-ID` 头:
- `GET /api/chat/session` — 发匿名 client_id
- SSE 事件: `start`(message_id + conversation_id)/ `token` / `sources` / `done` / `error`
- 首条消息自动建会话,后续带 `conversation_id` 续聊;提问前校验知识库存在、启用且有已完成文档

`/api/conversations` — 按 `X-Client-ID` 归属的会话 CRUD:列表/创建/详情(含消息)/改名/软删(`is_deleted`),无需 JWT。

### 其他路由

- `/api/auth`: login / initialize(首次强制改密)/ me / logout / change-password
- `/api/knowledge-bases` CRUD;`/api/documents` CRUD + `/{id}/status` + `/{id}/reprocess`
- `/api/files/{id}` 下载、`/api/files/{id}/view` 内联预览(公开,聊天来源弹层直出原文件)
- `/api/admin`(JWT): dashboard / rag-config(读写 `app-config.yaml`)/ model-profiles(多套配置 CRUD + 启用切换)/ models/{type}/test(连通性测试,可选 `{name}` 指定配置;旧 GET/PUT `/models` 已下线)/ qa-logs
- `/api/health` 存活、`/api/ready` 就绪(PostgreSQL/Qdrant/LLM/Embedding)

### 关键模式

- **Async 全家桶:** SQLAlchemy `AsyncSession` + asyncpg,所有 DB 操作 `async/await`
- **Schema 与模型分离:** `app/schemas/`(Pydantic)与 `app/models/`(ORM)
- **配置入文件:** 模型配置与 RAG 参数统一存项目根 `app-config.yaml`(`models:` 多套 profile + active 指针 / `rag:` 参数区;`.example` 模板随仓库,真文件在 `.gitignore`);设置页与 API 的增删改/切换全部落盘该文件,切换 active 热替换运行中 Provider,RAG 保存 setattr 热更新 `RAGConfig`,均保存即生效。`system_configs` 表已退役(遗留不删)
- **Chunk ID = Qdrant Point ID:** `document_chunks.id` 是向量唯一标识,切片不可变,重处理换新 id
- **Provider base_url 归一惯例:** 可不带 `/v1`,调用前统一补齐(embedding/llm/vision/rerank 一致)
- **单管理员:** 仅 id=1,首次登录强制改密(`must_change_password`);bcrypt 直用(不用 passlib)
- **时区感知:** 一律 `datetime.now(timezone.utc)` + `DateTime(timezone=True)`,禁用 `datetime.utcnow`
- **删除语义:** 会话软删;文档/知识库硬删(级联清 chunk + Qdrant 点)

### 数据库表

`admin`、`knowledge_bases`(含 `chunk_template`)、`documents`(含 `locked_at`/`locked_by`/`attempt_count`)、`document_chunks`(metadata 为 JSON 列)、`conversations`(`is_deleted`)、`qa_records`(延迟分项/检索参数/token 统计)、`qa_sources`、`system_configs`(已退役,遗留不读写)

## 前端架构(`frontend/src/`)

```
api/         admin.ts auth.ts chat.ts documents.ts knowledge.ts types.ts
utils/       request.ts(axios + jsonFetch 双轨,错误归一化) sse.ts stream-chat.ts format.ts auth.ts
             guard.ts(路由守卫纯函数) docs.ts / markdown.ts(Docs 页) sidebar.ts(侧栏折叠持久化)
stores/      auth.ts chat.ts knowledge.ts admin.ts
views/       Home.vue(/ 介绍) Docs.vue(/docs 文档) Chat.vue(/chat 通栏对话)
             admin/{Login,Initialize,Dashboard,KnowledgeBases,Documents,Settings,QaLogs}
components/  shell/(AppShell 壳层 + TopNav 顶栏 + AppSidebar 全局侧栏 + DashboardShell 管理页二级导航)
             chat/(消息/引用/来源预览/输入框) admin/(模型配置卡/RAG 参数表单/图表)
             common/ document/ knowledge/ ui/(shadcn-vue)
             docs/ 内置 Markdown(frontend/src/docs/*.md,import.meta.glob 静态导入)
router/      `/` Home、`/docs`、`/chat`、`/Login`、`/Initialize` 公开;`/Dashboard` `/KnowledgeBases`
             `/Documents` `/QaLogs` `/Settings` 管理页(DashboardShell 包裹);兜底重定向 `/`
```

**统一壳层:** 所有页面共享 `AppShell`(TopNav 全宽顶栏 + AppSidebar 会话侧栏 + 内容区);顶栏四项导航 Home/Docs/Chat/Dashboard(未登录隐藏 Dashboard),管理页在内容区顶部另有 5 项二级标签。守卫逻辑在 `utils/guard.ts`(纯函数 + vitest)。

**两种鉴权模式:**
- 管理端(`/api/admin`、`/api/knowledge-bases`、`/api/documents`):JWT Bearer,axios 拦截器(`utils/request.ts`),token 存 `localStorage.admin_token`
- 聊天端(`/api/chat`、`/api/conversations`、`/api/files`):`X-Client-ID`,`localStorage.client_id`,无需 JWT

测试用 vitest(`npm run test`),覆盖 utils/ 与 api/ 层;图标用 `@lucide/vue`(不用已弃用的 `lucide-vue-next`)。

> **当前约定:** 前端已按统一壳层设计(`docs/superpowers/specs/2026-10-02-unified-shell-4pages-design.md`)重写;`frontend/` 的改动默认不提交,待用户确认后统一提交。

## 环境

- **Windows 11** + Docker Desktop(postgres/qdrant 容器);Python 3.11,Node.js v24,npm,uv
- 端口:后端 8001(8000 被系统占用)、前端 5173、Embedding 8080、Qdrant 6333、Postgres 5432
- `.env` 在项目根目录(不提交,模板见 `.env.example`):DATABASE_URL / QDRANT_URL / JWT_SECRET_KEY / FILE_STORAGE_PATH / APP_CONFIG_PATH(模型与 RAG 配置文件路径,默认 `./app-config.yaml`)等
- 依赖以 `pyproject.toml` 为准(uv 管理);根目录 `requirements.txt` 为旧钉版遗留

## 设计文档

`docs/` 在 `.gitignore` 中(仅本机可读):
- `docs/design/` — 总体开发设计 v1.1
- `docs/plans/` — RAG 核心技术实现设计、分阶段实施计划
- `docs/superpowers/specs|plans/` — 多格式解析、混合检索、重排、邻块扩展、来源预览等专项设计

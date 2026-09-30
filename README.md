# Smart Campus RAG

基于 RAG（检索增强生成）的智能校园知识库问答系统。管理员上传文档，系统解析、分块、向量化后存入 Qdrant，用户提问时检索相关片段并由 LLM 生成带来源引用的回答。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS v4 + shadcn-vue + Pinia |
| 后端 | FastAPI + SQLAlchemy (async) + Pydantic v2 |
| 数据库 | PostgreSQL（业务数据）+ Qdrant（向量检索） |
| AI | OpenAI-compatible API（Embedding / LLM / Vision） |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js v24+
- Docker Desktop

### 启动数据库

```bash
docker compose up -d postgres qdrant
```

### 后端

```bash
# 安装依赖（uv 自动管理 .venv）
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接和模型 API 信息

# 初始化管理员账号（admin/admin）
uv run python scripts/create-admin.py

# 初始化 Qdrant 集合
uv run python scripts/init-qdrant.py

# 运行数据库迁移
psql -U postgres -d campus_rag -f scripts/migrate-001-add-conversations-and-qa-fields.sql

# 启动开发服务器（端口 8001）
uv run uvicorn app.main:app --reload --port 8001
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173


## 核心流程

**文档摄入：** 上传 → 解析 → 分块 → PostgreSQL → 向量化 → Qdrant

**问答检索：** 提问 → 向量化 → Qdrant 检索（按知识库过滤）→ Top-K → 上下文构建 → LLM → 回答 + 来源引用



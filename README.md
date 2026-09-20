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
# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接和模型 API 信息

# 初始化管理员账号（admin/admin）
python scripts/create-admin.py

# 初始化 Qdrant 集合
python scripts/init-qdrant.py

# 运行数据库迁移
psql -U postgres -d campus_rag -f scripts/migrate-001-add-conversations-and-qa-fields.sql

# 启动开发服务器（端口 8001）
uvicorn app.main:app --reload --port 8001
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 项目结构

```
├── app/                    # 后端应用
│   ├── api/routes/         # API 路由
│   ├── core/               # 配置、数据库、安全
│   ├── models/             # SQLAlchemy 模型
│   ├── schemas/            # Pydantic 请求/响应
│   ├── services/           # 业务逻辑
│   └── rag/                # RAG 核心管线
│       ├── parser/         # 文档解析（PDF/TXT）
│       ├── chunker/        # 文本分块
│       ├── embedding/      # 向量化
│       ├── retriever/      # 向量检索（Qdrant）
│       ├── llm/            # 大模型调用
│       ├── context/        # 上下文构建
│       ├── prompt/         # 提示词模板
│       └── citation/       # 来源引用
├── frontend/               # 前端应用
│   └── src/
│       ├── api/            # HTTP 客户端
│       ├── stores/         # Pinia 状态管理
│       ├── components/     # 组件（chat/、common/、ui/）
│       ├── layouts/        # 布局
│       └── views/          # 页面
├── scripts/                # 工具脚本
├── docs/                   # 设计文档
└── docker-compose.yml
```

## 核心流程

**文档摄入：** 上传 → 解析 → 分块 → PostgreSQL → 向量化 → Qdrant

**问答检索：** 提问 → 向量化 → Qdrant 检索（按知识库过滤）→ Top-K → 上下文构建 → LLM → 回答 + 来源引用

## API

| 路径 | 说明 | 认证 |
|------|------|------|
| `POST /api/chat` | 问答（SSE 流式） | X-Client-ID |
| `/api/conversations` | 会话 CRUD | X-Client-ID |
| `/api/knowledge-bases` | 知识库管理 | JWT |
| `/api/documents` | 文档管理 | JWT |
| `/api/admin/*` | 管理后台 | JWT |
| `/api/health` | 健康检查 | 无 |
| `/api/ready` | 就绪检查 | 无 |

## 设计文档

- [系统设计文档 v1.1](docs/plans/smart-campus-rag-development-design-v1.1.md)
- [RAG 核心技术设计](docs/plans/RAG核心技术实现设计文档-v1.0.md)
- [前端设计文档 v1.0](docs/design/smart-campus-rag-frontend-design-v1.0.md)

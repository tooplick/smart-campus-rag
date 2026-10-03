# Smart Campus RAG

基于 RAG(检索增强生成)的智能校园知识库问答系统。管理员上传文档,系统解析、切块、向量化入库;用户用自然语言提问,系统经混合检索召回相关切片,由 LLM 生成**带来源引用**的回答。

## 功能特性

- **多格式解析** — PDF / DOCX / PPTX / XLSX / CSV / TXT / MD / HTML / 图片(Vision OCR),单文件 ≤50MB
- **模板化切块** — 每个知识库可选 4 种切块模板:`general` 句级流式 / `section` 章节 / `qa` 问答对 / `one` 整篇
- **混合检索** — 向量 + 关键词双路召回 → 加权融合 → 相似度过滤 → 可选重排 → 邻块扩展,对齐 RAGFlow
- **来源引用** — 回答中的 `[来源 N]` 角标可点击预览文档原文与页码
- **流式问答** — SSE 实时输出;匿名 `X-Client-ID` 会话(续聊/改名/软删),无需注册
- **入库增强** — 可选 LLM 自动生成关键词与候选问题(只进向量文本,不污染引用原文)
- **统一壳层** — 4 个一级页面(Home / Docs / Chat / Dashboard)共享顶栏与会话侧栏,管理后台 5 项二级导航
- **配置即文件** — 模型配置(四类 Provider 多套 profile)与 RAG 参数统一存 `app-config.yaml`,设置页增删改/切换全部落盘并**热生效**

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS v4 + shadcn-vue + Pinia + markdown-it |
| 后端 | FastAPI + SQLAlchemy (async) + Pydantic v2 |
| 存储 | PostgreSQL(业务数据)+ Qdrant(向量,1024 维 COSINE) |
| 模型 | OpenAI 兼容协议(Embedding / LLM / Vision / Rerank) |
| 鉴权 | 管理端 JWT(单管理员)· 聊天端 `X-Client-ID` 匿名会话 |

## 快速开始

### 方式一:Docker 一键部署

```bash
cp .env.example .env                              # 首次
cp app-config.yaml.example app-config.yaml        # 首次,填入模型配置
docker compose up -d
```

打开 <http://localhost>,初始账号 `admin / admin`(首次登录强制改密)。
建表、Qdrant 集合、初始管理员均由后端启动时的 `scripts/bootstrap.py` 自动完成。
详见 [INSTALL.md](INSTALL.md#7-部署)。

### 方式二:本地开发

```bash
# 1. 依赖容器
docker compose up -d postgres qdrant

# 2. 后端
uv sync
cp .env.example .env                              # 按需修改连接串
cp app-config.yaml.example app-config.yaml        # 配置模型
uv run python scripts/create-admin.py             # 初始管理员 admin/admin
uv run python scripts/init-db.py                  # 建表
uv run python scripts/init-qdrant.py              # 初始化向量集合
uv run uvicorn app.main:app --reload --port 8001

# 3. 前端(另开终端)
cd frontend && npm install && npm run dev         # http://localhost:5173
```

> 本地开发时若用本机 llama.cpp 提供 Embedding,需先运行 `scripts/start-embedding-server.ps1`(可选,取决于你的 `app-config.yaml` 配置)。

**完整的环境要求、配置说明、部署方式与故障排查见 [INSTALL.md](INSTALL.md)。**
**架构分层、开发约定、测试与调试方法见 [DEVELOPMENT.md](DEVELOPMENT.md)。**

## 页面结构

| 路由 | 页面 | 权限 |
|------|------|------|
| `/` | 首页介绍 | 公开 |
| `/docs` | 技术文档(前端内置 Markdown) | 公开 |
| `/chat` | 问答(通栏对话 + SSE 流式) | 公开 |
| `/Dashboard` `/KnowledgeBases` `/Documents` `/QaLogs` `/Settings` | 管理后台 | JWT |
| `/Login` `/Initialize` | 登录 / 首次强制改密 | 公开 |

## 核心链路

**文档入库**

```
上传 → 按扩展名解析 → 按知识库模板切块 → LLM 入库增强(可选)
→ document_chunks 落库(原文纯净)→ 向量化 → Qdrant upsert
```

**问答检索**

```
问题 → 向量化
→ 向量检索 + 关键词检索(各取 candidate_top_k)
→ 加权融合(vector_weight)→ 相似度阈值过滤
→ 可选重排 → 截断 final_top_k → 邻块扩展
→ [来源 N] 上下文(≤4000 token)→ LLM → 回答 + 引用;无证据则拒答
```

## 项目结构

```
app/                  后端(FastAPI 分层:api → services → rag)
  api/routes/         路由:auth / chat / conversations / knowledge / documents / admin / files / health
  core/               配置(app_config 读写 app-config.yaml)、数据库、安全
  rag/                解析 / 切块 / 嵌入 / 检索 / 重排 / 提示词 / 引用
  services/           文档 worker、模型热替换
frontend/src/         前端
  components/shell/   AppShell 壳层(TopNav / AppSidebar / DashboardShell)
  views/              Home / Docs / Chat + admin 页
  utils/              双请求层、SSE、守卫(纯函数)
  docs/               内置技术文档 Markdown(Docs 页内容源)
scripts/              初始化与迁移脚本
tests/                后端测试(独立脚本,非 pytest)
deploy/nginx/         反向代理配置(SSE 专用 location)
docs/                 设计与计划文档(本机可读,不入库)
```

## 测试

```bash
# 后端:独立脚本,直接运行
uv run python tests/test_chunker.py    # 每个文件自带 __main__,输出 PASS/FAIL 汇总
# 部分测试需先起容器:docker compose up -d postgres qdrant

# 前端:vitest
cd frontend
npm run test                           # 纯逻辑(utils/api)TDD
npm run build                          # vue-tsc 类型检查 + 打包
```

## 端口一览

| 服务 | 端口 |
|------|------|
| 前端 dev | 5173 |
| 后端 dev | 8001(8000 被 Windows 系统进程占用) |
| Embedding(本地 llama.cpp) | 8080 |
| Qdrant | 6333 |
| PostgreSQL | 5432 |

## 相关文档

- [INSTALL.md](INSTALL.md) — 环境准备、安装配置、部署与故障排查
- [DEVELOPMENT.md](DEVELOPMENT.md) — 开发指南(架构、约定、测试、调试)
- `CLAUDE.md` — 面向 AI 协作的仓库约定速查

## 许可证

[MIT](LICENSE)



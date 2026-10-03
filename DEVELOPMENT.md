# DEVELOPMENT.md — 开发指南

面向本仓库的开发者:讲清架构分层、关键约定、日常开发流程与测试方法。
环境搭建与部署见 [INSTALL.md](INSTALL.md),功能清单见 [README.md](README.md)。

---

## 1. 技术栈与仓库布局

```
app/                    后端 FastAPI
  main.py               应用装配(路由注册、生命周期、静态文件)
  api/routes/           路由层(薄,只做参数校验与调用 service)
  api/deps.py           依赖注入(JWT 校验等)
  services/             业务层(文档 worker、会话、模型热替换)
  rag/                  RAG 管线(解析/切块/嵌入/检索/重排/提示词/引用)
  core/                 配置、数据库连接、安全工具
  models/  schemas/     ORM 模型 / Pydantic 请求响应(两层分离)
frontend/src/           前端 Vue 3 + TS
  api/  utils/  stores/ 请求层 / 纯函数工具 / Pinia 状态
  components/shell/     统一壳层;components/{chat,admin,common,...} 业务组件
  views/                页面(Home/Docs/Chat + admin 页)
  docs/                 Docs 页内置 Markdown 内容源
scripts/                一次性脚本(初始化、迁移)
tests/                  后端测试(独立脚本,非 pytest)
docs/                   设计与计划文档(本机可读,不入库)
```

**后端依赖管理用 `uv`**,依赖唯一事实源是 `pyproject.toml` + `uv.lock`(`uv lock --check` 可校验一致性),Docker 构建同样走 `uv sync --locked`。
**前端** `frontend/`,npm 管理。

---

## 2. 后端架构与约定

### 2.1 分层调用链

```
API Route (app/api/routes/)  →  Service (app/services/)  →  RAG Pipeline (app/rag/)
                                                          ↘  外部:PostgreSQL / Qdrant / OpenAI 兼容模型
```

- **路由层保持薄**:参数校验靠 Pydantic schema,业务逻辑下沉 service
- **横切模块**:`app/core/app_config.py`(app-config.yaml 读写)、`app/services/model_swap.py`(切换启用配置时热替换 Provider)

### 2.2 关键约定(违反会直接踩坑)

| 约定 | 说明 |
|------|------|
| **API 响应统一包装** | 所有 `/api/*` 返回 `{"success": true, "data": ..., "message": "success"}`(`app/utils/response.py`);业务错误 `success: false` + `error.code` |
| **Async 全家桶** | SQLAlchemy `AsyncSession` + asyncpg,所有 DB 操作 `async/await`,不要混用同步 session |
| **Schema 与模型分离** | `app/schemas/`(Pydantic 对外)与 `app/models/`(ORM 对内)不混用 |
| **时区感知** | 一律 `datetime.now(timezone.utc)` + `DateTime(timezone=True)`,**禁用** `datetime.utcnow` |
| **单管理员** | 仅 id=1,首次登录强制改密(`must_change_password`);bcrypt 直用,不用 passlib |
| **Chunk ID = Qdrant Point ID** | `document_chunks.id` 即向量唯一标识;切片不可变,重处理会换新 id 并清理旧点 |
| **配置入文件** | 模型与 RAG 参数只读写 `app-config.yaml`,`system_configs` 表已退役(遗留不删) |
| **删除语义** | 会话软删(`is_deleted`);文档/知识库硬删(级联清 chunk + Qdrant 点) |
| **Provider base_url** | 可不带 `/v1`,调用前统一补齐(embedding/llm/vision/rerank 一致) |

### 2.3 两条核心链路(改 RAG 前必读)

**查询链路**(`app/rag/pipeline.py`):

```
问题 → 向量化
→ 向量检索 + 关键词检索(各取 candidate_top_k;向量路不设阈值)
→ 融合排序(vector_weight 加权)→ 按 similarity_threshold 过滤
→ 可选重排(失败回退融合序)→ 截断 final_top_k
→ 邻块扩展(同文档前后各 1 块)→ [来源 N] 上下文(≤4000 token)
→ LLM → 回答 + 引用;无证据则拒答
```

> 阈值**统一在融合后过滤**,以保留关键词独有命中——不要改回向量路内过滤。

**入库链路**:

```
上传 → 解析(dispatch 按扩展名)→ 按 kb.chunk_template 切块
→ LLM 入库增强(关键词/候选问题,可选)→ document_chunks(原文纯净)
→ 向量化(增强项拼入 embed_text_for)→ Qdrant upsert
```

增强内容**只进向量文本与 metadata**,入库原文保持纯净,避免污染引用展示。

### 2.4 配置与热更新

- `app-config.yaml`:`models:`(四类 profile + `active` 指针)+ `rag:` 参数区
- 切换 `active` → `model_swap.apply_model_change` 替换运行中 Provider(管线/worker 实例)
- 保存 RAG 参数 → `setattr` 到运行中 `RAGConfig`
- **均保存即生效,无需重启**;文件是唯一事实源,手编后重新加载同样有效

---

## 3. 前端架构与约定

### 3.1 统一壳层

所有页面(含 Login/Initialize)共享 `AppShell`:

```
App.vue ─ Toaster + AppShell
            ├─ TopNav      全宽顶栏:Home/Docs/Chat/Dashboard 四项导航(Dashboard 未登录隐藏)+ 账号入口
            ├─ AppSidebar  全局会话侧栏:新对话 + 会话列表(重命名/删除)+ 底部账号区;折叠偏好存 localStorage,窄屏变抽屉
            └─ 内容区 <router-view>
                  ├─ Home / Docs / Chat
                  └─ DashboardShell → 5 个管理页(二级标签导航)
```

### 3.2 路由与守卫

| 类别 | 路由 |
|------|------|
| 公开 | `/`、`/docs`、`/chat`、`/Login`、`/Initialize` |
| 管理(JWT) | `/Dashboard`、`/KnowledgeBases`、`/Documents`、`/QaLogs`、`/Settings` |
| 兜底 | 未知路径 → `/` |

守卫逻辑在 **`src/utils/guard.ts`** —— 纯函数 `resolveGuard(to, auth)`,便于 vitest 覆盖:

- 管理页无 token → `/Login?redirect=<当前页>`;强制改密期间 → `/Initialize`
- `safeRedirect` 校验 redirect 仅限站内路径(防开放重定向)
- 401 拦截(`utils/request.ts`)清 token 并跳 `/Login?redirect=…`,公开页不受影响

### 3.3 双请求层(不要混用)

| 场景 | 封装 | 鉴权头 |
|------|------|--------|
| 管理端 `/api/admin`、`/api/knowledge-bases`、`/api/documents` | axios(`utils/request.ts`) | `Authorization: Bearer <JWT>` |
| 聊天端 `/api/chat`、`/api/conversations`、`/api/files` | `jsonFetch`(同文件)| `X-Client-ID`(匿名,`localStorage.client_id`) |

两者共享 `normalizeError` 错误归一化:同时识别业务包装 `{success:false, error:{code}}` 与 FastAPI 默认 `{detail}`。

**SSE**:手写解析在 `utils/sse.ts` + `utils/stream-chat.ts`,事件为 `start / token / sources / done / error`(`error` 时 HTTP 仍为 200)。历史消息接口不返回 `sources`,仅当次回答显示引用卡片。

### 3.4 Pinia 四域

`stores/auth.ts`、`chat.ts`、`knowledge.ts`、`admin.ts` —— 按领域拆,不建大而全的 store。
AppSidebar 与 ChatView 共享 `chat.conversations`,切换会话即时同步。

### 3.5 组件与样式

- UI 基座:shadcn-vue(`components/ui/`,由 `components.json` 管理),新组件用 `npx shadcn-vue add <name>`
- 图标一律 **`@lucide/vue`**(不要用已弃用的 `lucide-vue-next`)
- 样式 Tailwind CSS v4;状态覆盖三件套:加载骨架(`Skeleton` / `TableSkeleton`)→ 页面内错误态(`EmptyState` + 重试)→ 空态
- 表单校验**内联到字段**(失焦后才显示错误,避免一进页面就标红),提交时兜底拦截
- 文案与注释一律**简体中文**

### 3.6 Docs 页内容源

`frontend/src/docs/*.md`,文件名 `NN-slug.md`(序号控顺序),标题取首个一级标题。
经 `import.meta.glob` 静态导入,由 `utils/docs.ts` 的 `buildDocCatalog` 生成目录 —— **改文档需重新构建**。

---

## 4. 日常开发流程

### 4.1 启动

```powershell
# 终端 1:依赖容器
docker compose up -d postgres qdrant

# 终端 2:Embedding 服务(必开)
powershell -ExecutionPolicy Bypass -File scripts\start-embedding-server.ps1

# 终端 3:后端
uv run uvicorn app.main:app --reload --port 8001

# 终端 4:前端
cd frontend; npm run dev
```

### 4.2 典型任务的改动面

| 需求 | 主要改动位置 |
|------|-------------|
| 新增/修改文档格式支持 | `app/rag/parser/` 加解析器 + `dispatch.py` 注册;`tests/test_parsers.py` |
| 调整切块行为 | `app/rag/chunker/` + `tests/test_chunker.py`、`test_chunk_templates.py` |
| 改检索/融合/重排 | `app/rag/retriever/`、`pipeline.py` + `tests/test_hybrid_retrieval.py` 等 |
| 新增管理端 API | `app/api/routes/`(薄)+ service;响应走 `success_response` |
| 新增/调整页面 | `frontend/src/views/` + `router/index.ts`;管理页挂 `adminRoute` |
| 改问答展示 | `components/chat/`(MessageList / AssistantMessage / CitationCard) |
| 模型配置相关 | 前端 `components/admin/ModelProfilesCard.vue` ↔ 后端 `routes/model_profiles.py` ↔ `core/app_config.py` |

### 4.3 数据库变更

1. 改 `app/models/` 的 ORM 模型
2. **全新库**:`uv run python scripts/init-db.py` 直接建表
3. **存量库**:在 `scripts/` 新增 `migrate-00X-*.sql` 并用 psql 执行(增量脚本与建表脚本并存,不重复执行)

---

## 5. 测试

### 5.1 后端:独立脚本(不使用 pytest)

```powershell
uv run python tests/test_chunker.py        # 任意单文件直接运行
uv run python tests/test_parsers.py
```

- 每个 `tests/test_*.py` 自带 `__main__` 入口,输出 `PASS/FAIL` 汇总
- HTTP 一律 `httpx.MockTransport` 打桩,**不发真实请求**
- 依赖数据库的测试(如 delete、worker 类)先起容器:`docker compose up -d postgres qdrant`

覆盖示例:`test_hybrid_retrieval`(融合/阈值)、`test_neighbor_expansion`(邻块扩展)、`test_rerank`、`test_rag_config_file`(配置读写)、`test_model_profiles_api`(配置 CRUD 与热切换)、`test_llm_stream`(流式)、`test_worker_reprocess`(重处理)。

### 5.2 前端:vitest

```powershell
cd frontend
npm run test          # 运行全部
npm run build         # vue-tsc 类型检查 + 打包(UI 层验收靠这个)
```

- **纯逻辑(utils / api 层)用 TDD**:守卫判定 `guard.test.ts`、文档目录 `docs.test.ts`、markdown 渲染 `markdown.test.ts`、侧栏持久化 `sidebar.test.ts`、SSE/流式 `sse.test.ts` / `stream-chat.test.ts`
- **UI 组件不做单测**:以 `npm run build` 类型检查 + 手动走查验收

### 5.3 提交前自检清单

```powershell
# 后端
uv run python tests/test_chunker.py; uv run python tests/test_model_profiles_api.py   # 按改动面选测

# 前端
cd frontend; npm run test; npm run build
```

- [ ] 新接口返回是否走了统一包装(`success_response` / `error_response`)
- [ ] 异步代码没有混用同步 session;时间用 `datetime.now(timezone.utc)`
- [ ] 页面有加载/错误/空态三态;表单错误内联
- [ ] 控制台无报错;窄屏(<768px)不横向溢出

---

## 6. 调试技巧

| 场景 | 做法 |
|------|------|
| 就绪状态一览 | `curl http://localhost:8001/api/ready` —— PostgreSQL/Qdrant/LLM/Embedding 逐项探测 |
| 看检索命中了什么 | Dashboard → 问答日志 → 点开单条,含 RAG 参数、检索详情、来源切片与相似度 |
| SSE 不出字 | 后端日志看 `/api/chat`;nginx 部署时确认 `/api/chat` location 关闭了缓冲(`deploy/nginx/nginx.conf`) |
| 向量维度/集合 | `scripts/init-qdrant.py` 幂等重建;换 Embedding 模型后需重建集合并重新处理文档 |
| 配置改了没生效 | 设置页保存即热更新;手编文件后需重启后端(或触发重新加载),YAML 错误会报 `APP_CONFIG_ERROR` |
| 前端代理不通 | `frontend/vite.config.ts` 的 proxy 应指向 `http://localhost:8001`(不是 8000) |
| 登录态问题 | token 在 `localStorage.admin_token`;401 会自动清并带 redirect 跳登录 |

---

## 7. 常见坑

1. **Embedding 服务没开** —— 聊天与上传全部失败,报 `All connection attempts failed`;这是最常见的一类"莫名其妙全挂"。
2. **端口 8000 被 Windows 占用** —— 后端一律用 8001。
3. **`frontend/` 改动默认不提交** —— 待用户确认后统一提交(见 `CLAUDE.md`)。
4. **`docs/` 目录不入库** —— 设计与计划文档仅本机可读;根目录 `docs/` 已在 `.gitignore`(注意不要误伤 `frontend/src/docs/`,那是要入库的)。
5. **Chunk ID 不可复用** —— 重处理生成新 id,不要假设 id 跨处理稳定。
6. **`PUT /api/admin/rag-config` 只接受白名单字段** —— `temperature` / `max_tokens` 等有独立校验范围,前端已做内联校验。
7. **旧模型端点已下线** —— `GET/PUT /api/admin/models(/{type})` 已移除,统一用 `/api/admin/model-profiles` CRUD + `/models/{type}/test`。

---

## 8. 相关文档

- [README.md](README.md) — 项目概览与快速开始
- [INSTALL.md](INSTALL.md) — 安装、配置、部署、故障排查
- `CLAUDE.md` — 仓库约定速查(面向 AI 协作,但对人类同样有用)
- `docs/design/`、`docs/plans/`、`docs/superpowers/` — 详细设计与分阶段计划(本机)
- `frontend/src/docs/*.md` — 站内技术文档(Docs 页展示的内容源)

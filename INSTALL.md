# INSTALL.md — 安装与部署指南

本文覆盖从零搭建环境到生产部署的完整步骤。开发环境基于 **Windows 11 + Docker Desktop** 验证,Linux / macOS 命令基本一致(仅 Embedding 启动脚本为 PowerShell)。

- 只想本地跑起来看效果 → 按 [1~6](#1-环境要求) 顺序执行即可
- 排查启动失败 → 直接看 [故障排查](#故障排查)

---

## 1. 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Docker Desktop | 任意近期版本 | PostgreSQL / Qdrant 容器 |
| Python | 3.11+ | 后端 |
| [uv](https://docs.astral.sh/uv/) | 最新 | 后端依赖与虚拟环境管理 |
| Node.js | v24+(含 npm) | 前端构建 |
| llama.cpp 服务器 | 自带 `start-embedding-server.ps1` | 本地 Embedding(bge-m3) |

验证:

```powershell
docker --version; python --version; uv --version; node --version
```

---

## 2. 获取代码与依赖容器

```bash
git clone <repo-url> smart-campus-rag
cd smart-campus-rag

# 仅启动依赖(开发模式:后端/前端在宿主机跑)
docker compose up -d postgres qdrant
```

容器健康检查通过后(约 10 秒),PostgreSQL 监听 `5432`、Qdrant 监听 `6333`。

```powershell
docker compose ps                 # 应显示 postgres / qdrant 为 healthy
docker compose exec postgres psql -U postgres -d campus_rag   # 可进入数据库
```

---

## 3. 配置文件

项目根目录有两类配置,**都不入库**(`.gitignore` 已排除):

### 3.1 `.env` — 连接与密钥

```powershell
Copy-Item .env.example .env
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/campus_rag` |
| `QDRANT_URL` | Qdrant 地址 | `http://localhost:6333` |
| `JWT_SECRET_KEY` | 管理端 JWT 签名密钥 | 必须改 |
| `FILE_STORAGE_PATH` | 上传文件落盘目录 | `./uploads` |
| `APP_CONFIG_PATH` | 模型/RAG 配置文件路径 | `./app-config.yaml` |
| `BACKEND_PORT` | 后端端口 | `8000`(容器内) |

### 3.2 `app-config.yaml` — 模型与 RAG 参数

```powershell
Copy-Item app-config.yaml.example app-config.yaml
```

结构(`models:` 按四类 Provider 各有一个 `active` 指针 + `profiles` 映射;`rag:` 为检索/生成参数):

```yaml
models:
  llm:
    active: default
    profiles:
      default: { base_url: ..., api_key: ..., model: ... }
  embedding:
    active: default
    profiles:
      default: { base_url: ..., api_key: ..., model: ... }   # 需 1024 维
  rerank:  { active: null, profiles: {} }   # 可停用
  vision:  { active: null, profiles: {} }   # 可停用
rag:
  chunk_size: 600
  chunk_overlap: 80
  candidate_top_k: 8
  final_top_k: 5
  similarity_threshold: 0.6
  vector_weight: 0.7
  auto_keywords: 5
  auto_questions: 2
  temperature: 0.2
  max_tokens: 2048
  # 可选项(不填用默认值;设置页「运行参数」区可改)
  embedding_batch_size: 32    # 单批向量化条数
  embedding_max_retries: 3
  llm_max_retries: 3
  request_timeout: 120.0      # LLM/Embedding 请求超时秒数
```

> **api_key 明文落盘**,注意文件权限。该文件是**唯一事实源**:在设置页增删改、切换或直接手编后,重新加载即生效(切换热替换运行中的 Provider,RAG 保存热更新 `RAGConfig`,均无需重启)。

---

## 4. 初始化后端(一次性)

```powershell
# 4.1 安装依赖(自动创建 .venv)
uv sync

# 4.2 建表(Base.metadata.create_all)
uv run python scripts/init-db.py

# 4.3 初始化 Qdrant 集合(campus_rag_chunks_v1,1024 维 COSINE)
uv run python scripts/init-qdrant.py

# 4.4 创建初始管理员(admin/admin,首次登录强制改密)
uv run python scripts/create-admin.py
```

**已有数据库的增量迁移**(建表脚本只管全新库):

```bash
psql -U postgres -d campus_rag -f scripts/migrate-001-add-conversations-and-qa-fields.sql
psql -U postgres -d campus_rag -f scripts/migrate-002-add-chunk-template.sql
```

从旧 `system_configs` 表迁配置到文件(仅老库需要):

```powershell
uv run python scripts/migrate-config-to-file.py
```

---

## 5. 配置模型服务(Embedding 必需,其余可选)

问答与入库都依赖 `app-config.yaml` 中**启用的 embedding 配置**;llm 同理必需(否则服务可启动但问答不可用)。`base_url` 指向**任意 OpenAI 兼容端点**即可,常见两类:

- **远程/自建 API 服务**:直接填服务地址(如 `https://api.example.com/v1`)
- **本机 llama.cpp**(可选,仅本机跑模型时):运行仓库自带脚本

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-embedding-server.ps1
```

  - 监听 `http://127.0.0.1:8080`,对应 `app-config.yaml` 中 `models.embedding` 启用 profile 的 `base_url`
  - 模型文件 `%USERPROFILE%\models\bge-m3-Q8_0.gguf`,输出 **1024 维**,必须与 Qdrant 集合维度一致
  - 服务端 `--ubatch-size` 必须 ≥ 最长输入 token 数,否则长切片报 input too large
  - **Docker 部署时**容器内 `localhost` 不是宿主机,需把 base_url 改为 `http://host.docker.internal:8080`(compose 已配 `extra_hosts`)

未启动/未配置时的现象:聊天与上传报 `All connection attempts failed` 或 `/api/ready` 中对应项 `unavailable`。

---

## 6. 启动开发服务器

### 后端(端口 8001)

```powershell
uv run uvicorn app.main:app --reload --port 8001
```

> 8000 被 Windows 系统进程占用,故开发固定用 **8001**;前端 Vite 代理已指向 8001。

### 前端(端口 5173)

```powershell
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>:

1. 顶栏「登录」→ `admin / admin`(首次进入会被强制跳转改密页)
2. Dashboard → 知识库:新建知识库并选择切块模板
3. 文档:上传文件,等待进度到 `completed`(需 Embedding 服务在线)
4. Chat:提问验证回答与来源引用

---

## 7. 部署

### 7.1 一键部署(Docker 全栈)

前置条件仅两个配置文件(命令在**项目根目录**执行):

```powershell
Copy-Item .env.example .env                 # 已有可跳过
Copy-Item app-config.yaml.example app-config.yaml   # 已有可跳过
docker compose up -d --build
```

首次约需 2~5 分钟(构建前后端镜像)。完成后:

| 入口 | 地址 |
|------|------|
| 站点(经 nginx) | <http://localhost> |
| 初始管理员 | `admin / admin`(首次登录强制改密) |
| 就绪探测 | `curl http://localhost/api/ready` |

**自动完成的初始化(幂等,可重复执行)**:后端容器启动时先跑 `scripts/bootstrap.py` —— 建表 → 初始化 Qdrant 集合 → **仅当 admin 表为空时**创建初始管理员(绝不重置已有密码),随后拉起 uvicorn。

5 个服务一览:

| 服务 | 构建/镜像 | 端口 | 说明 |
|------|-----------|------|------|
| postgres | `postgres:16-alpine` | 5432 | 数据卷 `postgres_data` |
| qdrant | `qdrant/qdrant` | 6333/6334 | 数据卷 `qdrant_data` |
| backend | 根目录 `Dockerfile`(`uv sync --locked`) | 8000(仅容器内) | 启动即 bootstrap;健康检查 `/api/health` |
| frontend | `frontend/Dockerfile`(node 构建 → nginx 托管 SPA) | 5173(仅容器内) | 含 SPA 路由回退 |
| nginx | `nginx:alpine` | **80**(`WEB_PORT` 可改) | 对外唯一入口,反代 `/api/` → backend、`/` → frontend |

常用操作:

```powershell
docker compose ps                          # 状态(backend/qdrant 应为 healthy)
docker compose logs -f backend             # 看后端日志
docker compose down                        # 停止(数据卷保留)
docker compose down -v                     # 停止并清空数据(慎用)
WEB_PORT=8080 docker compose up -d         # 80 被占时换端口
```

**配置说明:**

1. **容器内地址已在 compose 覆盖**:`.env` 里的 `localhost` 只对本机开发有效,compose 的 `environment:` 会改用服务名(`postgres:5432`、`qdrant:6333`),两者互不干扰。
2. **`app-config.yaml` 是挂载进容器的**(不打进镜像),宿主机上改完 `docker compose restart backend` 生效;也可直接用设置页。
3. **模型服务地址按你的实际情况填**:`models.*.base_url` 指向任意 OpenAI 兼容端点。容器内访问**宿主机**上的服务(如本机 llama.cpp)用 `http://host.docker.internal:8080`(compose 已配 `extra_hosts`);若 llm/embedding 未配置或不可用,服务照常启动,仅问答/入库功能不可用(`/api/ready` 中对应项显示 `unavailable`)。
4. 上传文件存于卷 `backend_uploads`,不随容器重建丢失。

### 7.2 仅依赖容器(后端/前端本机跑)

```bash
docker compose up -d postgres qdrant
```

适合开发,见 [DEVELOPMENT.md](DEVELOPMENT.md)。

### 7.3 部署注意事项

1. 根 `Dockerfile` 用 `uv sync --locked --no-dev` 按 **`pyproject.toml` + `uv.lock`** 安装依赖(唯一事实源,已无 `requirements.txt`);改动依赖后提交新的 `uv.lock` 即可,镜像构建自动同步。
2. 容器内后端端口为 **8000**(与开发的 8001 不同),由 nginx 在容器网络内转发,不对外发布。

---

## 故障排查

| 现象 | 原因与解决 |
|------|-----------|
| 聊天/上传全部报 `All connection attempts failed` | Embedding 服务未启动或未配置 → 见第 5 节「配置模型服务」 |
| 后端启动报连接数据库失败 | `docker compose ps` 看 postgres 是否 healthy;核对 `.env` 的 `DATABASE_URL` |
| 长文档切片报 `input too large` | llama.cpp `--ubatch-size` 过小,调大后重启 |
| 向量维度不匹配 | Embedding 输出需 1024 维;若换了模型,删集合后重跑 `scripts/init-qdrant.py` 并重新处理文档 |
| 管理端 401 | JWT 过期,重新登录;`JWT_SECRET_KEY` 变更会使旧 token 全部失效 |
| 前端改了配置不生效 | `app-config.yaml` YAML 语法错误 → 后端启动时报 `APP_CONFIG_ERROR`,对照 `app-config.yaml.example` 修正 |
| 端口冲突 | 8000(系统占用)→ 用 8001;5432/6333 被占 → 调整 `docker-compose.yml` 端口映射 |
| Windows 下 `npm run dev` 代理不通 | 确认后端在 8001,`frontend/vite.config.ts` 的 proxy 指向 `http://localhost:8001` |

**健康检查接口:**

```bash
curl http://localhost:8001/api/health   # 存活
curl http://localhost:8001/api/ready    # 就绪:PostgreSQL / Qdrant / LLM / Embedding 逐项探测
```

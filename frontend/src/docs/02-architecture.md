# 系统架构

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS v4 + shadcn-vue + Pinia |
| 后端 | FastAPI + SQLAlchemy(async)+ Pydantic v2 |
| 存储 | PostgreSQL(业务数据)+ Qdrant(向量) |
| 模型 | OpenAI 兼容协议,Embedding / LLM / Vision / Rerank 四类 Provider |

## 请求链路

```text
前端(AppShell 壳层)
  ├─ 管理端 /api/admin/*   → axios + JWT Bearer
  └─ 聊天端 /api/chat/*    → fetch + X-Client-ID(匿名会话)
后端
  API Route → Service → RAG Pipeline → PostgreSQL / Qdrant / 模型服务
```

## 查询链路(混合检索)

```text
问题 → 向量化
→ 向量检索 + 关键词检索(各取 candidate_top_k)
→ 融合排序(vector_weight 加权)→ 相似度阈值过滤
→ 可选重排 → 截断 final_top_k
→ 邻块扩展(同文档前后各 1 块)
→ [来源 N] 上下文 → LLM → 回答 + 引用
```

无证据时模型拒答,不会编造内容。

## 入库链路

```text
上传 → 解析(按扩展名分派)→ 按知识库模板切块
→ LLM 入库增强(关键词/候选问题,可选)
→ document_chunks 落库 → 向量化 → Qdrant upsert
```

增强内容只进向量文本,入库原文保持纯净,引用展示不受污染。

## 前端路由

| 路径 | 页面 | 权限 |
|---|---|---|
| `/` | 首页介绍 | 公开 |
| `/docs` | 技术文档 | 公开 |
| `/chat` | 问答 | 公开 |
| `/Dashboard` `/KnowledgeBases` `/Documents` `/QaLogs` `/Settings` | 管理后台 | JWT |
| `/Login` `/Initialize` | 登录 / 首次改密 | 公开 |

所有页面共享统一壳层(顶栏 + 左侧栏);管理页在内容区顶部另有 5 项二级标签导航。

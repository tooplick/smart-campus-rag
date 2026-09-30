# Smart Campus RAG 前端

Vue 3 + TypeScript + Vite + Tailwind CSS + shadcn-vue。

## 开发

```bash
npm install
npm run dev      # http://localhost:5173,代理 /api → http://localhost:8001
npm run build    # vue-tsc 类型检查 + 生产构建
npm run test     # vitest(utils 层单测)
```

需要后端:`uv run uvicorn app.main:app --reload --port 8001`(项目根目录)

## 结构

- `src/api/` — API 封装(auth/knowledge/documents/chat/admin)与全局类型
- `src/utils/request.ts` — 统一错误归一化(兼容业务包装与 FastAPI detail 两种形态)
- `src/utils/sse.ts` — 手写 SSE 解析(EventSource 无法带 X-Client-ID)
- `src/stores/` — Pinia:auth / chat / knowledge / admin
- `src/views/` — 用户端 Chat + `admin/` 8 个管理页
- `src/components/` — chat/ common/ knowledge/ document/ admin/ + shadcn-vue ui/

## 功能

- 用户端:知识库选择、多轮对话、SSE 流式回答、Markdown 渲染、引用来源卡片、会话管理
- 管理端:登录/首次改密、仪表盘、知识库 CRUD、文档上传与处理进度、RAG 配置、模型配置与连通测试、问答日志

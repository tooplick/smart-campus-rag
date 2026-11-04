# 章节架构(已锁定)

> 全篇初稿按本表执行。缺章、多章、占位符均视为质量门失败。

## Required chapter files

| 文件 | 角色 | 最小正文字数 | 执行者 | 允许占位 |
|---|---|---|---|---|
| chapters/01_绪论.md | 主章 | 2000 | 独立子代理 | 否 |
| chapters/02_相关技术与理论.md | 主章 | 2500 | 独立子代理 | 否 |
| chapters/03_系统需求分析.md | 主章 | 2500 | 独立子代理 | 否 |
| chapters/04_系统设计.md | 主章 | 3000 | 独立子代理 | 否 |
| chapters/05_系统实现.md | 主章 | 3000 | 独立子代理 | 否 |
| chapters/06_系统测试.md | 主章 | 2000 | 独立子代理 | 截图可留 [待补:截图] |
| chapters/07_结论与展望.md | 主章 | 1200 | 独立子代理 | 否 |
| chapters/08_致谢.md | 支撑件 | 400 | 独立子代理 | 否 |
| chapters/09_参考文献.md | 支撑件 | ≥12 条 | 控制器 + 用户核对 | 否(必须可追溯) |
| chapters/00_摘要.md | 支撑件 | 200–300 字 | 最后统一写 | 否 |

## 规则

- 每个主章一个独立子代理,写权互斥,禁止两个代理改同一文件
- 每个子代理只收到:对应任务包、必要源码摘录、证据清单、硬性拒稿检查
- 控制器对子代理产出做 review 后才记进度
- 代理产出与复核记录写入 plan/chapter-agent-provenance.md
- 子代理不可用时,停下询问用户是否降级单代理模式,不得静默降级

## 源码证据基线

- 后端 app/(api/ routes、services/、rag/ pipeline·retriever·chunker·parser)
- 前端 frontend/src/(router、views、components、utils)
- CLAUDE.md(架构与命令权威说明)、README.md、docker-compose.yml

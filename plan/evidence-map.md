# 证据地图(plan/evidence-map.md)

> 全部文献经 arXiv 页面核实(2026-10-03)。中文文献无来源,统一 [待补:中文文献]。

| Source ID | Citation (GB/T 7714) | 类型 | 可用事实 | 支撑主张 | 引用槽位 | 风险 |
|---|---|---|---|---|---|---|
| R1 | LEWIS P, PEREZ E, PIKTUS A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[C]//Advances in Neural Information Processing Systems (NeurIPS 2020). 2020. | 会议 | RAG 将参数化记忆与非参数化记忆(稠密向量索引)结合;在开放域问答上达到当时最优;生成更具体、多样的事实性语言 | RAG 奠基性工作;检索增强可提供证据来源 | 1.1、1.2 RAG 路线 | 低 |
| R2 | GAO Y, XIONG Y, GAO X, et al. Retrieval-augmented generation for large language models: a survey[EB/OL]. arXiv:2312.10997, 2024. | 综述 | LLM 存在幻觉、知识过时、推理不可追溯问题;RAG 经 Naive→Advanced→Modular 演进;检索、增强、生成三要素 | RAG 缓解幻觉与知识更新问题;RAG 发展脉络 | 1.1 问题背景、1.2 综述线 | 低 |
| R3 | KARPUKHIN V, OĞUZ B, MIN S, et al. Dense passage retrieval for open-domain question answering[C]//Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP). 2020. | 会议 | 稠密双编码检索较 Lucene-BM25 在 top-20 召回上绝对提升 9%–19% | 稠密向量检索优于纯稀疏检索 | 1.2 检索路线 | 低 |
| R4 | REIMERS N, GUREVYCH I. Sentence-BERT: sentence embeddings using siamese BERT-networks[C]//Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing (EMNLP). 2019. | 会议 | 句向量经余弦相似度比较,将相似句对检索从 65 小时降至约 5 秒,保持 BERT 精度 | 句向量嵌入使语义检索可行 | 1.2 嵌入路线 | 低 |
| R5 | DEVLIN J, CHANG M W, LEE K, et al. BERT: pre-training of deep bidirectional transformers for language understanding[C]//Proceedings of NAACL-HLT 2019. 2019. | 会议 | 双向预训练,11 项 NLP 任务 SOTA | 预训练语言模型是嵌入与理解的基础 | 1.2 / 第2章 | 低 |
| R6 | VASWANI A, SHAZEER N, PARMAR N, et al. Attention is all you need[C]//Advances in Neural Information Processing Systems 30 (NIPS 2017). 2017. | 会议 | Transformer 仅基于注意力机制,更易并行 | 大模型的架构基础 | 1.2 / 第2章 | 低 |
| R7 | JOHNSON J, DOUZE M, JÉGOU H. Billion-scale similarity search with GPUs[EB/OL]. arXiv:1702.08734, 2017. | 期刊/预印 | GPU 上十亿级最近邻检索、乘积量化 | 向量检索引擎的工程可行性 | 1.2 向量数据库线 | 低(用 arXiv 版本规避页码错引) |
| R8 | QDRANT. Qdrant vector database[EB/OL]. https://qdrant.tech/ | 网站 | 开源向量检索引擎,支持过滤与多种距离度量 | 系统选型依据 | 1.2 / 第2章 | 低(EB/OL) |
| R9 | 马钰, 任世明. 基于大语言模型和RAG的舆情知识交互及推荐研究[J]. 人文与社会科学学刊, 2025, 1(5): 311-314. | 期刊(Crossref DOI 10.70693/rwsk.v1i5.1027 验证) | 构建领域知识库,RAG 检索文档片段+LLM 生成 | 国内 RAG 知识库问答应用 | 1.2 段C | 低 |
| R10 | 陶彦霖, 张宏斌, 宋欢. 面向私有云运营场景的检索增强生成系统设计与实践[J]. 电信科学, 2026, 42: 53-65. | 期刊(DOAJ 收录验证) | 知识库自动化构建+RAG 全流程工程方案 | 国内 RAG 系统工程实践 | 1.2 段C | 低(无 DOI,DOAJ 可查) |
| ~~C1~~ | ~~[待补:中文文献]~~ 已由 R9、R10 替代(2026-10-03) | — | — | — | — | 中文文献问题已关闭 |

## 段落蓝图(chapter-blueprints/01_绪论-blueprint.md)

### 1.1 研究背景与意义
- Role: context → 矛盾 → 承接
- Main claim: 校园资料格式多样且分散,关键词检索难以直接回答自然语言问题;LLM 有幻觉与知识过时问题(R2),RAG 以外部知识库补足(R1),故构建带出处引用的校园知识库问答系统有实际价值
- Evidence IDs: R1, R2
- Transition: 技术可行性依赖检索与嵌入技术进展,引出 1.2
- Forbidden: 列表堆砌、空壳强调句

### 1.2 国内外研究现状
- Role: 文献段三组,按方法族
- Paragraph A(RAG 演进): R1 → R2(Naive/Advanced/Modular),边界:落地到垂直领域仍需工程化设计
- Paragraph B(检索与嵌入): R5、R6(Transformer/BERT 基础)→ R4(句向量)→ R3(稠密优于稀疏)→ R7/R8(向量引擎),边界:单一向量检索对专有名词/编号类查询不稳,故需混合检索
- Paragraph C(国内与应用现状): [待补:中文文献] 为主,校园知识库问答应用现状;边界:多格式文档解析、带出处引用、匿名轻量问答结合的完整系统仍少
- Forbidden: 按论文逐条罗列;每段须综合 ≥2 个来源

### 1.3 研究内容与目标
- Role: gap → 本文定位
- Main claim: 三项目标:自然语言问答并给出带出处引用、多格式文档全流程入库、系统全流程可运行演示;不夸大为创新点,表述为工程目标
- Evidence IDs: 无文献,基于 CLAUDE.md 项目事实
- Forbidden: 贡献点列表超过 3 条

### 1.4 论文组织结构
- Role: 承接
- Main claim: 一段式顺叙六章安排
- Forbidden: bullet 堆砌、章节简介罗列过长

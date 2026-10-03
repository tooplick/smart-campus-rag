# 模型与参数配置

模型配置与 RAG 参数统一存放在项目根目录的 `app-config.yaml` 文件中(含 API Key,已加入 `.gitignore`),
模板见 `app-config.yaml.example`。**文件是唯一事实源**:设置页的所有增删改都会落盘,手工编辑文件后重新加载同样有效。

## 模型配置区

四类模型各自维护一组命名配置(profile):

- **对话 LLM**:生成回答所用模型。
- **Embedding**:文档与问题向量化,输出维度需与 Qdrant 集合一致(1024)。
- **Vision**:图片文档 OCR 识别,可不配置。
- **Rerank**:检索结果重排,可不配置。

操作说明:

1. 每张卡片顶部显示当前**启用配置**(名称、Base URL、模型)。
2. 下拉框切换启用配置,**保存即热替换**运行中的 Provider,无需重启。
3. 「测试」按钮验证当前配置的连通性,返回延迟与向量维度。
4. 「添加 / 编辑 / 删除」管理配置清单;API Key 只写不回显,编辑时留空表示不修改。
5. 启用中的配置不可删除,需先切换到其他配置。

## RAG 参数区

| 参数 | 含义 |
|---|---|
| Chunk Size / Overlap | 切块最大长度与相邻块重叠 |
| Candidate / Final Top-K | 召回候选数与送入模型的最终切片数 |
| Similarity Threshold | 融合分阈值,低于该值的切片被过滤 |
| Vector Weight | 混合检索中向量路权重,调低偏关键词、调高偏语义 |
| Auto Keywords / Questions | 入库增强生成的关键词与候选问题数,0 = 关闭 |
| Temperature / Max Tokens | 生成随机性与最大长度 |
| Embedding Batch Size / 重试 / 超时(可选) | 运行参数:`embedding_batch_size`(默认 32)、`embedding_max_retries`、`llm_max_retries`(默认 3)、`request_timeout`(默认 120 秒);设置页「运行参数」区可改,保存即生效 |

所有参数保存即热更新到运行中的管线,无需重启。

## 常见问题

- **Embedding 服务连接失败**:本地向量服务未启动,运行 `scripts/start-embedding-server.ps1`。
- **切换配置后回答异常**:先用「测试」确认新配置连通,再检查维度是否为 1024。
- **配置文件改坏了**:参照 `.example` 模板修正 YAML 语法,重启后端即可。

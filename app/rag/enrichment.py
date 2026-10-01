from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_ENRICH_PROMPT = (
    "你是检索索引优化助手。给定一段文档切片,生成检索增强元数据:\n"
    "- keywords: {k} 个关键词(切片中的专有名词/术语/关键概念)\n"
    "- questions: {q} 个候选问题(读者可能用什么口语化、简短的问题问到这段内容)\n"
    "只输出 JSON,格式:{{\"keywords\": [...], \"questions\": [...]}}\n"
    "切片内容:\n{content}"
)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def embed_text_for(content: str, keywords: list[str], questions: list[str]) -> str:
    """嵌入文本 = 正文 + 关键词 + 相关问题;增强项缺失时不占位。

    原文本身保持纯净入库(引用展示不受污染),增强内容只参与向量化。
    """
    parts = [content]
    if keywords:
        parts.append("关键词: " + "、".join(keywords))
    if questions:
        parts.append("相关问题: " + "；".join(questions))
    return "\n".join(parts)


async def enrich_chunk(llm, content: str, *, keywords: int, questions: int) -> dict:
    """LLM 生成切片的关键词/候选问题;任何失败降级为空 dict,不阻塞入库。"""
    if not content.strip() or (keywords <= 0 and questions <= 0):
        return {}
    try:
        prompt = _ENRICH_PROMPT.format(k=max(keywords, 0), q=max(questions, 0), content=content)
        resp = await llm.chat(
            [{"role": "user", "content": prompt}],
            stream=False,
            temperature=0.2,
            max_tokens=256,
        )
        text = resp["choices"][0]["message"]["content"]
        data = json.loads(_FENCE.sub("", text).strip())
        out: dict = {}
        if keywords > 0 and isinstance(data.get("keywords"), list):
            out["keywords"] = [str(x) for x in data["keywords"][:keywords] if str(x).strip()]
        if questions > 0 and isinstance(data.get("questions"), list):
            out["questions"] = [str(x) for x in data["questions"][:questions] if str(x).strip()]
        return out
    except Exception:
        logger.warning("切片增强失败,降级为纯正文嵌入", exc_info=True)
        return {}

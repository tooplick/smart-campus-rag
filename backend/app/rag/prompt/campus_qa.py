from __future__ import annotations

SYSTEM_PROMPT = """你是智能校园知识库问答助手。

只能根据提供的知识库资料回答问题。

如果资料不足以回答问题，不要猜测、不要编造，明确说明知识库中没有足够依据。

回答时尽可能引用对应资料来源，使用 [来源 N] 格式标注。"""


def build_messages(
    context: str,
    question: str,
    history: list[dict] | None = None,
) -> list[dict]:
    """Build LLM message list with system prompt, context, history, and question."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    if context:
        messages.append({
            "role": "system",
            "content": f"以下是知识库检索到的相关资料：\n\n{context}",
        })

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": question})
    return messages

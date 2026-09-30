"""LLM 流式 chunk 解析回归测试。

无需 pytest，可直接运行::

    uv run python tests/test_llm_stream.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.rag.llm.openai_compatible as llm_module
from app.rag.llm.openai_compatible import OpenAICompatibleLLM


class _FakeResponse:
    """模拟 httpx 流式响应对象。"""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        pass

    def aiter_lines(self):
        async def _gen():
            for line in self._lines:
                yield line

        return _gen()


class _FakeStream:
    """client.stream() 返回的异步上下文管理器。"""

    def __init__(self, lines: list[str]) -> None:
        self._resp = _FakeResponse(lines)

    async def __aenter__(self) -> _FakeResponse:
        return self._resp

    async def __aexit__(self, *exc) -> bool:
        return False


class _FakeClient:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    def stream(self, method, url, json=None, headers=None) -> _FakeStream:
        return _FakeStream(self._lines)


def _collect_tokens(lines: list[str]) -> list[str]:
    """用假的 SSE 流驱动 LLM 流式解析，返回产出的 token 列表。"""

    async def _run() -> list[str]:
        llm = OpenAICompatibleLLM(base_url="https://fake.test", api_key="k", model="m")
        original = llm_module.httpx.AsyncClient
        llm_module.httpx.AsyncClient = lambda **kwargs: _FakeClient(lines)
        try:
            stream = await llm.chat(
                messages=[{"role": "user", "content": "hi"}],
                stream=True,
            )
            return [token async for token in stream]
        finally:
            llm_module.httpx.AsyncClient = original

    return asyncio.run(_run())


def test_stream_yields_all_content_tokens():
    """正常内容块应依次产出 token（对照组）。"""
    lines = [
        "",
        'data: {"id": "c1", "choices": [{"delta": {"role": "assistant", "content": ""}}]}',
        "",
        'data: {"id": "c1", "choices": [{"delta": {"content": "你"}}]}',
        'data: {"id": "c1", "choices": [{"delta": {"content": "好"}}]}',
        "data: [DONE]",
    ]
    assert _collect_tokens(lines) == ["你", "好"]


def test_stream_skips_usage_chunk_with_empty_choices():
    """流中的 usage 统计块（choices 为空列表）应跳过，不能中断流。"""
    lines = [
        'data: {"id": "c1", "choices": [{"delta": {"content": "你"}}]}',
        'data: {"id": "c1", "choices": [{"delta": {"content": "好"}}]}',
        'data: {"id": "c1", "choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 2, "total_tokens": 14}}',
        "data: [DONE]",
    ]
    assert _collect_tokens(lines) == ["你", "好"]


def test_stream_skips_chunk_with_null_delta():
    """delta 为 null 的块应跳过，不能中断流。"""
    lines = [
        'data: {"id": "c1", "choices": [{"delta": null}]}',
        'data: {"id": "c1", "choices": [{"delta": {"content": "好"}}]}',
        "data: [DONE]",
    ]
    assert _collect_tokens(lines) == ["好"]


def test_stream_skips_malformed_and_choiceless_chunks():
    """非法 JSON 行与缺少 choices 的块应跳过。"""
    lines = [
        "data: not-json",
        'data: {"id": "c1", "object": "chat.completion.chunk"}',
        'data: {"id": "c1", "choices": [{"delta": {"content": "好"}}]}',
        "data: [DONE]",
    ]
    assert _collect_tokens(lines) == ["好"]


def main() -> int:
    tests = [
        obj
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            failed += 1
            print(f"FAIL {test.__name__}: {type(e).__name__}: {e}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

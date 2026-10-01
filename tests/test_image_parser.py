"""图片 OCR 解析测试:Vision 模型调用与结果文本块。

MockTransport 模拟 OpenAI 兼容 /chat/completions 响应,不发真实请求。

无需 pytest，可直接运行::

    uv run python tests/test_image_parser.py
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK,统一按 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx


def test_image_parser_extracts_text():
    """Vision 响应文本成为单个 TEXT 块;请求携带 base64 图像。"""

    async def scenario():
        from app.rag.parser.image import ImageParser

        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.content
            captured["path"] = request.url.path
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "图片中的文字是:校园开放日通知。"}}]
            })

        # base_url 不带 /v1(与嵌入 provider 同惯例),由解析器补齐
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        parser = ImageParser("https://api.example.com", "key", "vision-model", client=client)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "n.png"
            p.write_bytes(b"\x89PNG-fake-bytes")
            blocks = await parser.parse(p)

        assert len(blocks) == 1 and "校园开放日通知" in blocks[0].content, f"实际 {blocks}"
        assert b"image_url" in captured["body"], "请求应携带图像内容"
        assert captured["path"] == "/v1/chat/completions", f"应自动补 /v1,实际 {captured['path']}"
        await client.aclose()

    asyncio.run(scenario())


def test_image_parser_propagates_http_error():
    """Vision 调用失败向上抛出(worker 将文档置 failed 并记录原因)。"""

    async def scenario():
        from app.rag.parser.image import ImageParser

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        parser = ImageParser("https://api.example.com/v1", "key", "vision-model", client=client)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "n.jpg"
            p.write_bytes(b"fake-jpeg")
            try:
                await parser.parse(p)
            except Exception:
                pass
            else:
                raise AssertionError("HTTP 失败应向上抛出")
        await client.aclose()

    asyncio.run(scenario())


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

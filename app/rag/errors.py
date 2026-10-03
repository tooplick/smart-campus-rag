from __future__ import annotations


class RAGStageError(RuntimeError):
    """阶段化异常:标记失败阶段(embedding / llm),保留原始异常供上层细化错误码。

    chat 路由据此把底层 httpx 异常翻译成「哪个模型配置出了什么问题」的用户可读文案。
    """

    def __init__(self, stage: str, cause: BaseException):
        self.stage = stage
        self.cause = cause
        super().__init__(f"{stage} stage failed: {cause}")

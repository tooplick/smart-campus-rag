# 依赖唯一事实源:pyproject.toml + uv.lock(不再使用 requirements.txt)
# 基础镜像自带 Python 3.11 + uv;从 ghcr.io 分发(与 uv 官方文档一致)
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# 先只复制依赖清单,依赖不变时命中 Docker 层缓存
COPY pyproject.toml uv.lock ./
# UV_LINK_MODE=copy:Docker 分层文件系统不适合硬链接;--locked 严格按 uv.lock 安装
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
RUN uv sync --locked --no-dev --no-install-project

# 再复制源码(本项目无 build-system,代码以工作目录方式运行,不作包安装)
COPY . .

# 虚拟环境进 PATH,后续 CMD 直接用其中的 uvicorn
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

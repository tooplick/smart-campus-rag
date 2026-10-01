# 本地嵌入服务(llama.cpp) — bge-m3(1024 维,与 Qdrant 现有向量兼容)
# 用法: powershell -ExecutionPolicy Bypass -File scripts\start-embedding-server.ps1
# 系统侧配置: 模型页 Embedding → base_url=http://localhost:8080, model=bge-m3, api_key 任意
$llama = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\llama.exe"
$model = Join-Path $env:USERPROFILE "models\bge-m3-Q8_0.gguf"
if (-not (Test-Path $model)) {
    Write-Error "模型文件不存在: $model (请先下载 bge-m3-Q8_0.gguf)"
    exit 1
}
# --ubatch-size 必须 >= 最长输入 token 数(默认 512 会被长切片撑爆,报 input too large)
& $llama serve --embedding -m $model --host 127.0.0.1 --port 8080 `
    --batch-size 8192 --ubatch-size 8192

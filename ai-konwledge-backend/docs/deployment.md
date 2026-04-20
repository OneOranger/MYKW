# Deployment (Local)

1. 进入项目目录：

```powershell
cd E:\AIPG\my_kw\ai-konwledge-backend
```

2. 激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
conda deactivate
```

3. 安装依赖并运行：

```powershell
pip install -e .
uvicorn aipayment_kb_agent.api.app:app --host 127.0.0.1 --port 8000 --reload
```

4. 健康检查：

`GET http://127.0.0.1:8000/healthz`

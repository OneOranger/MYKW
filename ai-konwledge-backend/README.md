# AI Knowledge Backend

本项目是本地部署的个人 AI 知识库后端，提供：

- 多轮对话（短期 + 长期记忆）
- 本地文档入库（txt/md/pdf/docx/pptx/xlsx/csv）
- RAG 检索 + 引用明细 + 检索元数据
- LanceDB 向量表（`knowledge_chunks`）
- 知识库未命中时自动联网补充回答
- 自动升级（从问答提取知识点，生成待审核文档并可一键入库）
- Prompt Engineering 配置管理
- 详细日志（请求级、节点级）

## 启动

```powershell
.\.venv\Scripts\Activate.ps1
conda deactivate
pip install -e .
uvicorn aipayment_kb_agent.api.app:app --host 127.0.0.1 --port 8000 --reload
```

## 关键接口

- `POST /api/v1/query?auto_upgrade=true`
- `POST /api/v1/admin/upload`
- `POST /api/v1/admin/import/sync-raw`
- `GET /api/v1/admin/documents`
- `GET /api/v1/admin/vectorstore/stats`
- `GET /api/v1/upgrade/review`
- `POST /api/v1/upgrade/review/{candidate_id}`

## 目录

核心代码在 `src/aipayment_kb_agent/`，符合需求文档中的模块拆分。

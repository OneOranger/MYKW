# Architecture

## 核心流程

1. `POST /api/v1/query` 进入 `KnowledgeAgent`
2. MemoryManager 写入短期记忆并检索长期记忆
3. Retriever 执行 embedding + 向量检索
4. 命中不足时走 WebSearchTool 联网补充
5. 生成回答并返回 `hits/meta/citationOrder`
6. `auto_upgrade=true` 时触发自动升级 pipeline，生成待审核知识文档

## 数据存储

- 文档原件：`data/documents/raw`
- 自动升级候选：`data/documents/auto_ingested/pending`
- 已审核候选：`data/documents/auto_ingested/reviewed`
- 向量库：`data/vectorstores/knowledge_chunks.lance`（LanceDB）
- 入库清单：`data/vectorstores/ingestion_manifest.json`
- 记忆文件：`data/short_memory.json` / `data/long_memory.json`

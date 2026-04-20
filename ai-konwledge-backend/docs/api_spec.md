# API Spec

## Query

- `POST /api/v1/query?auto_upgrade=true|false`
  - request:
    - `session_id: string`
    - `message: string`
    - `auto_upgrade: boolean` (body/query 均可)
    - `category?: string`
    - `top_k?: number`
  - response:
    - `content`
    - `hits[]`
    - `meta`
    - `citationOrder[]`
    - `upgradeDecision`

## Admin

- `POST /api/v1/admin/upload` (multipart files)
- `POST /api/v1/admin/upload-path?local_path=...`
- `POST /api/v1/admin/import/sync-raw` (扫描 `data/documents/raw` 的新增/变更文件并自动入库)
- `GET /api/v1/admin/documents`
- `POST /api/v1/admin/rebuild`
- `GET /api/v1/admin/vectorstore/stats`
- `POST /api/v1/admin/vectorstore/recreate`
- `GET /api/v1/admin/upgrade/pending`（审核入口）
- `POST /api/v1/admin/upgrade/review/{candidate_id}`（审核动作）

## Upgrade

- `GET /api/v1/upgrade/review`
- `POST /api/v1/upgrade/review/{candidate_id}`
- `POST /api/v1/upgrade/trigger`

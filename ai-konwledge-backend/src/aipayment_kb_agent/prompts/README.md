# Prompt Templates

This directory stores prompt templates used by the backend.

- `system/base.yaml`: fallback answer style when no reliable local hit.
- `system/knowledge_retrieval.yaml`: answer style when local chunks are available.
- `system/auto_upgrade.yaml`: Q&A to candidate extraction rules.
- `system/update_guidelines.yaml`: markdown generation rules for ingestion.
- `tests/regression_cases.yaml`: executable prompt regression cases.
- `tests/run_regression.py`: run all prompt regression cases against local API.

All templates use UTF-8 and can be versioned independently.



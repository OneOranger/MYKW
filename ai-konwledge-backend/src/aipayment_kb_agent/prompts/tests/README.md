# Prompt Regression Tests

Run local prompt regression cases against the backend API.

## Usage

1. Start backend service at `http://127.0.0.1:8000`.
2. Run:

```bash
python src/aipayment_kb_agent/prompts/tests/run_regression.py
```

## Optional arguments

```bash
python src/aipayment_kb_agent/prompts/tests/run_regression.py \
  --cases src/aipayment_kb_agent/prompts/tests/regression_cases.yaml \
  --endpoint http://127.0.0.1:8000/api/v1/query \
  --top-k 8 \
  --timeout-sec 45
```

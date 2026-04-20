install:
	.\.venv\Scripts\python -m pip install -e .

run:
	.\.venv\Scripts\python -m uvicorn aipayment_kb_agent.api.app:app --host 127.0.0.1 --port 8000 --reload

test:
	.\.venv\Scripts\python -m pytest -q

FROM python:3.12-slim
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY api.py evidence_pdf.py identity_workflow.py identity_rules.py review_agent.py sanctions.py run_store.py ./
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]

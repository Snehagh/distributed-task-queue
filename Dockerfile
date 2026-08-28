FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command runs the API; the worker and scheduler override this in compose.
CMD ["uvicorn", "taskq.api:app", "--host", "0.0.0.0", "--port", "8000"]

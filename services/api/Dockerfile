FROM python:3.11-slim

WORKDIR /app
COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# API owns the citizen HTTP boundary, while the dedicated ingestion adapter and
# canonical normalizer remain the source-adapter/normalization implementation.
COPY services/api /app/api
COPY services/ingestion /app/ingestion

ENV PYTHONPATH=/app:/app/api:/app/ingestion
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

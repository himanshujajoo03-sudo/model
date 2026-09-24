FROM python:3.8-slim

WORKDIR /app

# Install exact versions matching Spark containers runtime (Python 3.8.10)
RUN pip install --no-cache-dir \
    numpy==1.24.4 \
    scipy==1.10.1 \
    scikit-learn==1.3.2 \
    joblib==1.4.2 \
    pandas==2.0.3 \
    PyYAML==6.0.3

ENV PYTHONPATH=/app/services/ml:/app

CMD ["python", "services/ml/training/train.py"]

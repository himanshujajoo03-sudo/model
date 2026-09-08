FROM bitnami/spark:3.5

USER root

# Copy ML library
COPY services/ml/ /opt/spark/ml/

# Copy Spark jobs
COPY services/spark/jobs/ /opt/spark/jobs/
COPY services/spark/requirements.txt /opt/spark/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /opt/spark/requirements.txt

USER 1001

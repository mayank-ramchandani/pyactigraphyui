FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
    PATH="/usr/lib/jvm/java-21-openjdk-amd64/bin:${PATH}" \
    MAX_SERVER_SIDE_BIN_MB=1000 \
    ACCELEROMETER_JAVA_HEAP_MB=2048 \
    ACCELEROMETER_TIMEOUT_SECONDS=1800 \
    GT3X_ACTIVITY_MODE=enmo \
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-21-jre-headless \
        build-essential \
        gcc \
        g++ \
        gfortran \
    && rm -rf /var/lib/apt/lists/*

COPY src/backend/requirements-docker.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools==59.8.0 wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN java -version

EXPOSE 10000

CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "10000"]

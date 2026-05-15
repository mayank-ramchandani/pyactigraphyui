FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    gfortran \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY src/backend/requirements-docker.txt /app/requirements-docker.txt
RUN pip install --upgrade pip setuptools==59.8.0 wheel
RUN pip install -r /app/requirements-docker.txt

COPY . /app

RUN java -version

EXPOSE 10000

CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "10000"]
FROM python:3.10.16-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

COPY src/backend/requirements-docker.txt /app/requirements-docker.txt
RUN pip install --upgrade pip setuptools==59.8.0 wheel
RUN pip install -r /app/requirements-docker.txt

COPY . /app

EXPOSE 10000

CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "10000"]
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema necessárias para psycopg
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context é a raiz do repositório (backend/ + frontend/).
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/
# Frontend separado do backend; <repo>/frontend é montado em /frontend
# (FRONTEND_DIR = BASE_DIR.parent/frontend = /frontend).
COPY frontend/ /frontend/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

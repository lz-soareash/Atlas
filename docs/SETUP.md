# SETUP

## Requisitos

- Python 3.12+
- (opcional, produção) Docker e/ou PostgreSQL 16 com extensão `pgvector`

## 1. Backend (serve a API + o frontend)

```bash
cd backend

# preparar variáveis de ambiente
copy ..\.env.example .env
#   -> DB_ENGINE=sqlite  (padrão, roda sem servidor Postgres)
#   -> ou DB_ENGINE=postgres para (produção)

# instalar dependências
python -m pip install -r requirements.txt
# (opcional) dependências de desenvolvimento
python -m pip install -r requirements-dev.txt

# aplicar migrações
python manage.py migrate

# criar superusuário (acesso ao /admin)
python manage.py createsuperuser

# rodar testes
python manage.py test

# subir servidor
python manage.py runserver
# -> Frontend e API em http://127.0.0.1:8000 (frontend em /, API em /api)
```

## 2. Frontend

O frontend fica **separado do backend** em `frontend/`, mas é servido pelo
próprio Django a partir de `frontend/templates/atlas/` e
`frontend/static/atlas/`. Não há build step nem dependências de biblioteca.
Basta o backend em execução — nenhuma instalação adicional é necessária.

## 3. Produção (Docker + PostgreSQL + pgvector)

Requer o Docker instalado.

```bash
# variáveis de ambiente (ajuste DB_USER/DB_PASSWORD/GEMINI_API_KEY)
copy .env.example .env

docker compose up --build
```

Serviços:

- `db` — PostgreSQL 16 + pgvector (porta 5432)
- `backend` — Django com API + frontend (porta 8000)

## Modelos de IA (Gemini)

Preencha no `.env`:

```env
GEMINI_API_KEY=SuaChaveAqui
GEMINI_MODEL=gemini-2.0-flash
```

> A chave fica **somente** no backend. Nunca expor no frontend nem versionar.

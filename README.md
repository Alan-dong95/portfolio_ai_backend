# portfolio-ai-api

FastAPI backend for [portfolio_ai](../portfolio_ai) — personalized feed, morning brief, portfolio symbols.

## Local dev

```bash
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health

## Production deploy

See **[DEPLOY.md](./DEPLOY.md)** — Zeabur + Supabase step-by-step.

Environment template: [.env.production.example](./.env.production.example)

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/feed` | Personalized news feed |
| GET | `/brief` | Morning brief |
| GET | `/portfolio` | Demo portfolio symbols |
| GET | `/symbols/lookup` | Symbol name lookup |

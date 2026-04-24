#!/bin/sh
set -e
cd /app
alembic upgrade head
python -c "from app.db.session import SessionLocal; from app.services.ai_foundation_seed import ensure_platform_default_prompts; db = SessionLocal(); ensure_platform_default_prompts(db); db.close()"
exec "$@"

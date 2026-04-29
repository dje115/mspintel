#!/bin/sh
set -e
cd /app
alembic upgrade head
python -c "from app.db.session import SessionLocal; from app.services.ai_foundation_seed import sync_platform_prompt_catalog; db = SessionLocal(); sync_platform_prompt_catalog(db); db.close()"
exec "$@"

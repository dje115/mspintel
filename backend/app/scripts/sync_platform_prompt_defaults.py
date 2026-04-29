"""CLI: upsert missing platform prompt definitions for an existing database (non-destructive).

Usage (Docker):
  docker compose exec backend python -m app.scripts.sync_platform_prompt_defaults

Local:
  cd backend && python -m app.scripts.sync_platform_prompt_defaults
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    from app.db.session import SessionLocal
    from app.services.ai_foundation_seed import sync_platform_prompt_catalog

    db = SessionLocal()
    try:
        stats = sync_platform_prompt_catalog(db)
        print(json.dumps(stats, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

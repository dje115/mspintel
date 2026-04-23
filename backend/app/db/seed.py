from app.db.session import SessionLocal
from app.services.seed import seed_all


def main() -> None:
    db = SessionLocal()
    try:
        seed_all(db)
        print("Seed complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()

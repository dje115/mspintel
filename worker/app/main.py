import time

from app.core.settings import get_settings
from app.jobs.runner import run_placeholder_jobs


def main() -> None:
    settings = get_settings()
    print("Worker service booted. Press Ctrl+C to stop.")

    while True:
        run_placeholder_jobs()
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()

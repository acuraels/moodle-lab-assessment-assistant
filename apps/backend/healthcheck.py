"""Container readiness: HTTP server and the configured database are available."""
import asyncio
import sys
from urllib.request import urlopen

from sqlalchemy import text

from app.database import engine


async def check_database() -> None:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        with urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
            if response.status != 200:
                raise RuntimeError("HTTP health check failed")
        asyncio.run(asyncio.wait_for(check_database(), timeout=3))
    except Exception:
        # Docker retains healthcheck output: never print connection secrets.
        sys.exit(1)

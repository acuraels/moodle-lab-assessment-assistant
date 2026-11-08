"""Run migrations and the cross-service smoke test in a disposable PostgreSQL.

Requires Docker and backend/ML test dependencies in the active Python. Creates
one uniquely named container with tmpfs data and removes only that container.
Never reads project .env or connects to the application's PostgreSQL/volumes.
"""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def docker(*args: str, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def main() -> None:
    name = "ml-integration-" + uuid4().hex[:12]
    created = False
    try:
        docker("run", "--detach", "--rm", "--name", name,
               "--label", "purpose=lab-assessment-disposable-test",
               "--tmpfs", "/var/lib/postgresql/data",
               "--env", "POSTGRES_USER=ml_test",
               "--env", "POSTGRES_PASSWORD=local-test-only",
               "--env", "POSTGRES_DB=ml_integration_test",
               "--publish", "127.0.0.1::5432", "postgres:17-alpine")
        created = True
        deadline = time.monotonic() + 60
        while docker("exec", name, "pg_isready", "-U", "ml_test", "-d", "ml_integration_test", check=False).returncode:
            if time.monotonic() > deadline:
                raise RuntimeError("Temporary PostgreSQL did not become ready")
            time.sleep(0.5)
        port = docker("port", name, "5432/tcp").stdout.strip().rsplit(":", 1)[1]
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("ML_", "OLLAMA_", "JWT_", "LTI_", "POSTGRES_"))
               and key not in {"DATABASE_URL", "MAX_FILE_SIZE_BYTES", "FRONTEND_URL"}}
        env.update(
            DATABASE_URL=f"postgresql+asyncpg://ml_test:local-test-only@127.0.0.1:{port}/ml_integration_test",
            JWT_SECRET="isolated-integration-test-secret-at-least-32",
            LTI_CONSUMER_KEY="isolated-test", LTI_CONSUMER_SECRET="isolated-test",
            ML_URL="http://ml.test", ML_TOKEN="", ML_MAX_ATTEMPTS="1",
            ML_PROCESSING_DEADLINE_SECONDS="1800", PYTHONDONTWRITEBYTECODE="1",
            LAB_ML_DISPOSABLE_TEST="1",
        )
        paths = [str(ROOT / "packages/assessment-contract"), str(ROOT / "apps/backend"), str(ROOT / "apps/ml")]
        env["PYTHONPATH"] = os.pathsep.join(paths + [env.get("PYTHONPATH", "")])
        # Neither application's default dotenv loader can see project .env files.
        with TemporaryDirectory(prefix="lab-ml-integration-") as working_directory:
            migration = (
                "from pathlib import Path; import sys; from alembic import command; "
                "from alembic.config import Config; root=Path(sys.argv[1]); "
                "config=Config(str(root/'alembic.ini')); "
                "config.set_main_option('script_location',str(root/'alembic')); "
                "command.upgrade(config,'head')"
            )
            subprocess.run([sys.executable, "-c", migration, str(ROOT / "apps/backend")],
                           cwd=working_directory, env=env, check=True)
            subprocess.run([sys.executable, str(ROOT / "tests/postgres_ml_smoke.py")],
                           cwd=working_directory, env=env, check=True)
        print("PASS: real PostgreSQL migrations, upload, ML multipart/extraction, result and teacher decision; Ollama MOCKED.")
    finally:
        if created:
            docker("stop", "--time", "5", name, check=False)


if __name__ == "__main__":
    main()

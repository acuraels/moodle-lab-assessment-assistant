# Backend

FastAPI, SQLAlchemy, Alembic и PostgreSQL 17. Контракты — в [api.md](../../api.md).
Основной запуск и backup описаны в [корневом README](../../README.md#единый-запуск-через-docker).

## Запуск

Настройте корневой `.env` на основе корневого `.env.example`, сохранив фактические
секреты и параметры существующей БД. Из корня:

```sh
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Проверка через Nginx: **http://localhost:8080/health**. Порты 8000 и 5432 хоста
закрыты; внутри Docker БД доступна как `postgres:5432`. Вложенный Compose заменяется
корневым. `apps/backend/.env` можно сохранить для ручного запуска Python;
корневой Compose его не читает и передаёт настройки контейнеру явно.

## Данные и миграции

Используется внешний volume `backend_postgres_data`. Отсутствие volume — ошибка,
а не повод создать пустую БД. Перед переключением обязателен проверенный backup.
Два PostgreSQL не должны одновременно использовать этот volume. Файлы хранятся
в PostgreSQL как BYTEA и входят в `pg_dump`.

После готовности БД backend выполняет `alembic upgrade head`, затем `exec uvicorn`.
При ошибке Alembic сервер не стартует. Healthcheck использует установленный Python
и проверяет `/health` плюс `SELECT 1`.

```sh
docker compose exec backend alembic current
docker compose logs --tail 100 backend
docker compose restart backend
```

Не запускайте seed для проверки: он меняет существующие демонстрационные данные.
Обычный `docker compose down` сохраняет внешний volume.

## Reverse proxy и LTI

Nginx сохраняет внешний Host с портом, схему, путь и POST body `/lti/launch`.
`FRONTEND_URL` — внешний URL Nginx, например `http://localhost:8080/`.
Uvicorn доверяет proxy headers при условии закрытых Docker-сетей и отсутствия
публикации его порта. Другой reverse proxy потребует пересмотра доверия и схемы.
Для same-origin API CORS не требуется. Moodle и ML пока не входят в Compose;
`worker.py` по-прежнему выставляет `ai_failed`, Outcomes не подключён.

## Совместимость сохранённых критериев

В ответе `GET /api/attempts/{attempt_id}/ai-result` критерий всегда содержит
`name`, `score`, `max_score`, `comment`. Если максимум или комментарий не были
сохранены в старом JSON, схема ответа возвращает `null`. Максимум не выводится
из общей оценки. Чтение не обновляет PostgreSQL; миграция и повторный seed
для этого исправления не нужны.

Регрессионные тесты схемы запускаются из `apps/backend` в окружении с
установленными зависимостями backend; отдельная установка pytest не требуется:

```sh
python -m unittest discover -s tests -v
```

Тесты не включены в production-образ. Их можно передать через stdin без копирования
в образ (PowerShell, из корня):

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -Raw -Encoding UTF8 apps/backend/tests/test_criteria_compatibility.py | docker compose exec -T backend python - -v
```

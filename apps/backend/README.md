# Backend

Backend приложения для проверки лабораторных работ, отправленных из Moodle
через LTI 1.1. API реализован на FastAPI, данные хранятся в PostgreSQL.

## Требования

- Docker Desktop с Docker Compose — рекомендуемый способ запуска;

## Запуск через Docker Compose

Откройте PowerShell в папке backend:

```powershell
cd C:\Dev\moodle-lab-assessment-assistant\apps\backend
```

Создайте файл `.env` из примера:

```powershell
Copy-Item .env.example .env
```

Для локальной разработки значения из `.env.example` подходят.

Соберите образ и запустите сервисы:

```powershell
docker compose up --build
```

После запуска будут доступны:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- проверка состояния: <http://localhost:8000/health>

Проверка из PowerShell:

```powershell
curl.exe http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

Миграции выполняются автоматически командой `alembic upgrade head` перед
запуском Uvicorn. Отдельный контейнер `db-init` не требуется: база
`lab_assessment` создаётся PostgreSQL при первой инициализации volume.

### Тестовые данные

После запуска backend можно заполнить базу демонстрационными данными. Но перед этим нужно в seed_demo.py заменить значения переменных на актуальные!

```powershell
docker compose exec backend python -m app.seed_demo
```

Для остановки:

```powershell
docker compose down
```

Чтобы остановить сервисы и удалить локальные данные PostgreSQL:

```powershell
docker compose down -v
```

Команда `down -v` удаляет все сохранённые данные базы и используется только
если база должна быть создана заново.

## Полный порядок запуска

После запуска backend откройте отдельные терминалы и выполните следующие
шаги.

### 1. Запустить frontend

В PowerShell:

```powershell
cd C:\Dev\moodle-lab-assessment-assistant\apps\frontend
npm i
npm run dev
```

Frontend будет доступен по адресу
<http://127.0.0.1:5173/>. Терминал с Vite оставьте запущенным.

### 2. Запустить Moodle

После запуска frontend клонируйте репозиторий локального Moodle:

```bash
git clone https://github.com/Ulyanayou/moodle-docker.git
cd moodle-docker
make up
```

Команду `make up` выполняйте в Bash.

Backend, frontend и Moodle должны оставаться запущенными одновременно:

- backend: <http://localhost:8000>;
- frontend: <http://127.0.0.1:5173/>;
- Moodle: <http://localhost/>.

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

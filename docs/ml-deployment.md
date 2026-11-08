# ML на Linux и Ollama на Windows через Tailscale

Основная схема: React → FastAPI/PostgreSQL → ML-сервис на Linux → Tailscale →
Ollama с моделью на Windows. ML-сервис извлекает текст из документов, составляет
запрос и проверяет оценку на CPU. На Linux GPU не требуется. Windows выполняет
генерацию на своей видеокарте.

Адрес Windows в этой конфигурации — `100.81.179.101`, Linux — `100.88.177.48`.
ML доступен backend по внутреннему адресу `http://ml:8001`; Ollama — по
`http://100.81.179.101:11434`. Автоматические тесты со заглушками не подтверждают
доступность удалённой машины и реальную генерацию.

## 1. Подготовить Ollama на Windows

Нужны Tailscale и [Ollama для Windows](https://docs.ollama.com/windows).
Python и код ML-сервиса на Windows для этой схемы не требуются.
Проверьте, что `tailscale status` показывает адрес `100.81.179.101`.

Если Ollama уже запущена из трея, завершите её перед запуском отдельного
`ollama serve`: новый процесс должен получить новый адрес прослушивания.
В PowerShell:

```powershell
$env:OLLAMA_HOST = '100.81.179.101:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
# Необязательно: OLLAMA_MODELS задаёт каталог весов вне репозитория.
ollama serve
```

Оставьте терминал открытым. Во втором PowerShell проверьте установленные модели:

```powershell
$env:OLLAMA_HOST = '100.81.179.101:11434'
ollama list
ollama --version
Invoke-RestMethod 'http://100.81.179.101:11434/api/tags'
```

Для текущей машины с 16 GB VRAM выбрана `freehuntx/qwen3-coder:14b`, проверенная
реальной генерацией на синтетическом наборе. Если её ещё нет:

```powershell
ollama pull freehuntx/qwen3-coder:14b
```

При контексте 8192 Ollama сообщила для 14B `size_vram=10786471040` байт
(10,05 GiB), с полной загрузкой модели на GPU. Для будущей машины с 8 GB этот
вариант не подтверждён. Сохранённое значение конфигурации по умолчанию
`qwen3:4b-instruct-2507-q4_K_M` — **неизмеренный кандидат для 8 GB**; перед сменой
нужны отдельные замеры памяти и качества. `qwen3:1.7b-q4_K_M` также не оценивалась.
Сравнение 7B и 14B и его ограничения — в [отчёте](ml-grading-evaluation.md).
Имя установленной модели должно точно совпадать с
`OLLAMA_MODEL` в Linux `.env`. Зафиксируйте версию Ollama и digest модели из
`/api/tags` для воспроизводимого прогона.

Доступ TCP 11434 от Linux должен разрешаться правилами tailnet и Windows
Firewall. Если порт блокируется, создайте узкое правило из PowerShell
с правами администратора:

```powershell
New-NetFirewallRule -DisplayName 'Ollama from ML Linux via Tailscale' -Direction Inbound -Action Allow -Protocol TCP -LocalAddress 100.81.179.101 -LocalPort 11434 -RemoteAddress 100.88.177.48
```

Ollama слушает только Tailscale-IP; открывать порт на публичном роутере не нужно.
У её HTTP API в этой схеме нет отдельного токена: доступ ограничивается tailnet
и указанным адресом клиента. Необязательный `ML_TOKEN` защищает только
backend → ML-сервис и не является токеном Ollama.

## 2. Запустить backend и ML на Linux

В корневой `.env` добавьте настройки, сохраняя действующие DATABASE_URL,
JWT/LTI-секреты и имя PostgreSQL volume:

```dotenv
ML_URL=http://ml:8001
OLLAMA_URL=http://100.81.179.101:11434
OLLAMA_MODEL=freehuntx/qwen3-coder:14b
ML_TOKEN=
ML_BIND_ADDRESS=127.0.0.1
ML_PORT=8001
ML_CONTEXT_TOKENS=8192
ML_TIMEOUT_SECONDS=540
ML_MAX_ATTEMPTS=2
ML_RETRY_DELAY_SECONDS=10
ML_PROCESSING_DEADLINE_SECONDS=1800
```

Если задаёте `ML_TOKEN`, Compose передаёт одно значение backend и ML-сервису;
оно отправляется в `X-ML-Token`. Секреты храните только в окружении/локальном
`.env`, не в Git.

Worker один на процесс; запускайте **один экземпляр backend с одним Uvicorn worker**.
ML-сервис также запускается с одним worker, чтобы ограничение генерации
распространялось на все запросы. Очередь — существующая таблица attempts;
lease, число попыток и общий дедлайн хранятся в PostgreSQL. Технический сбой
не превращается в оценку. Автоматически повторяются только временные ошибки,
в пределах числа попыток и срока. Ожидание в интерфейсе 120 секунд не останавливает
задачу. Публичного endpoint ручной повторной обработки пока нет; ai_failed
учитывается существующим лимитом загрузок.

Изменение включает аддитивную Alembic-миграцию снимка и служебных полей обработки.
Перед обновлением действующего стека выполните существующую процедуру backup из
[README](../README.md). Миграция применяется при обычном запуске backend;
не запускайте seed и не удаляйте volumes. Старые результаты сохраняются; старые
processing без снимка завершаются явной технической ошибкой, чтобы не оценить их
по изменившимся материалам. Для новой установки подготовьте `.env` и новый volume
по README.

```sh
docker compose --profile ml config --quiet
docker compose --profile ml up --build -d backend frontend ml
docker compose --profile ml ps
```

Эта команда запускает frontend, backend, PostgreSQL и ML. Локальная Ollama
отключена: её отдельный профиль `ollama` здесь не нужен. Сеть `model_access`
даёт контейнеру ML исходящий доступ к Tailscale-адресу Windows; `inference`
соединяет backend и ML внутри Compose.

Проверьте оба участка **из контейнеров**, а не только с Linux-хоста:

```sh
# ML -> Windows Ollama: должно вернуть HTTP 200.
docker compose exec -T ml python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["OLLAMA_URL"].rstrip("/")+"/api/tags",timeout=10).status)'
# Backend -> ML -> наличие выбранной модели: должно вернуть HTTP 200.
docker compose exec -T backend python -c 'import os,urllib.request; u=os.environ["ML_URL"].rstrip("/")+"/ready"; r=urllib.request.Request(u,headers={"X-ML-Token":os.environ.get("ML_TOKEN","")}); print(urllib.request.urlopen(r,timeout=10).status)'
```

`GET /health` проверяет процесс ML, `GET /ready` — доступность Ollama и наличие
нужной модели. Readiness не доказывает, что модель помещается в GPU и генерирует
корректный ответ: для этого нужен первый реальный документ. При 503 проверьте
адрес прослушивания Ollama, имя установленной модели, Windows Firewall и путь
Docker → Tailscale. Команды не выводят секреты. Backend продолжает обслуживать
историю и решения преподавателя при недоступной модели.

По умолчанию действует консервативная проверка размера контекста; точный локальный
tokenizer и ограничения описаны в [ML README](../apps/ml/README.md).

### Таймаут при одновременно включённой Amnezia

Успешный `tailscale ping` не гарантирует, что обычный HTTP идёт через Tailscale.
Если `curl` зависает, сначала проверьте маршрут на Linux:

```sh
ip -4 route get 100.81.179.101
ip -4 rule show
ip -4 route show table 52
```

На тестовом Linux правило Amnezia с приоритетом `219` направляло запросы через
`amnezia_awg`, опережая правило Tailscale `5270`. В таблице `52` уже был правильный
маршрут `100.81.179.101 dev tailscale0`. Для этой конфигурации помогло временное
правило только для Windows-сервера:

```sh
sudo ip -4 rule add pref 217 to 100.81.179.101/32 lookup 52
ip -4 route get 100.81.179.101
curl --fail --max-time 10 http://100.81.179.101:11434/api/tags
```

Ожидаемый маршрут — `dev tailscale0 table 52 src 100.88.177.48`. Значение `217`
выбрано по фактическим правилам этой машины: на другом хосте проверьте свободный
приоритет с меньшим числом, чем у перехватывающего VPN. При неверном маршруте
на Linux изменение Windows Firewall не устраняет причину. После успешного
`curl` повторите обе проверки из контейнеров выше: Docker использует также
правила пересылки и NAT.

Правило не сохраняется после перезагрузки; после переподключения VPN проверьте
его снова. Постоянное восстановление правила настраивается отдельно. Откат:

```sh
sudo ip -4 rule del pref 217 to 100.81.179.101/32 lookup 52
```

## 3. Критерии и первая проверка

Для числовой оценки вставьте в существующее поле «Критерии оценивания» JSON
(либо загрузите UTF-8 TXT с ним):

```json
{
  "criteria": [
    {"name": "Корректность решения", "max_score": 6},
    {"name": "Обоснование и проверка граничных случаев", "max_score": 4}
  ]
}
```

Это только пример формы: реальные названия и максимумы подтверждает преподаватель.
Подробные требования можно описать в методичке. Максимумы и состав критериев
модель менять не может; итог складывается кодом из баллов критериев.
Если критерии свободным текстом, отсутствуют или JSON-рубрика неоднозначна,
ML выдаёт содержательный результат `score=null`, `max_score=null`, `criteria=[]`
с объяснением ограничения в conclusion. Нулевая оценка не подставляется.

Сначала проверьте один документ через CLI из ML README, затем загрузите его
через действующее приложение. Ожидайте `processing → ai_checked`, проверьте
заключение/критерии, отправьте преподавателю и проверьте его решение. Отдельно
проверьте offline Windows, скан, повреждённый файл и превышение контекста:
они должны завершаться понятной технической ошибкой, без зависания processing.

## 4. Необязательная локальная Ollama и другие схемы

Чтобы также запустить Ollama в Docker на этой машине, измените в root `.env`:

```dotenv
ML_URL=http://ml:8001
OLLAMA_URL=http://ollama:11434
```

Запустите оба профиля:

```sh
docker compose --profile ml --profile ollama up --build -d backend frontend ml ollama
docker compose exec ollama ollama pull freehuntx/qwen3-coder:14b
```

Профиль `ollama` использует образ `ollama/ollama:0.40.15`, изменяемый через
`OLLAMA_IMAGE`. По умолчанию локальная Ollama работает на CPU; её порт наружу
не опубликован, веса сохраняются в volume `ollama_models`. Сеть `model_download`
позволяет скачать веса, `OLLAMA_NO_CLOUD=1` отключает облачный inference.
Для машины без GPU эта схема нужна только при осознанной проверке CPU-генерации.

На Docker-хосте с настроенной NVIDIA GPU доступен дополнительный overlay:

```sh
docker compose -f compose.yaml -f compose.gpu.yaml --profile ml --profile ollama up --build -d backend frontend ml ollama
```

Поддержка GPU и драйверов проверяется отдельно:
[GPU в Compose](https://docs.docker.com/compose/how-tos/gpu-support/).

Для точного подсчёта контекста нужен tokenizer.json именно выбранной модели.
Пример скачивания в ML README относится только к кандидату 4B, не к текущей 14B.
Если соответствующий файл подготовлен на Linux, скопируйте его в volume уже
запущенного ML:

```sh
docker compose cp /path/to/tokenizer.json ml:/opt/ml-tokenizer/tokenizer.json
```

После копирования добавьте `ML_TOKENIZER_PATH=/opt/ml-tokenizer/tokenizer.json`
в root `.env` и пересоздайте только ML через
`docker compose --profile ml up -d ml`. Без файла оставьте переменную пустой;
действует консервативный предел по UTF-8 байтам. Токенизатор не входит в Git.
Эта настройка применима и к удалённой, и к локальной Ollama.

Существующий вариант с ML и Ollama на Windows также поддерживается: установите
Python ML-сервис по [ML README](../apps/ml/README.md), привяжите его к
`100.81.179.101:8001`, а его `OLLAMA_URL` задайте адресом локальной Ollama.
На Linux укажите `ML_URL=http://100.81.179.101:8001` и запускайте backend/frontend
без профилей. Тогда исходящий путь в Tailscale проверяется из backend-контейнера,
а Windows Firewall должен разрешать TCP 8001 от Linux.

## 5. Проверяемость и качество

Тесты с подставным HTTP-транспортом проверяют контракт, ограничения, статусы,
ошибки и восстановление. После установки backend test extra, ML и общего пакета
из корня можно выполнить:

```sh
python -m unittest discover -s packages/assessment-contract/tests -v
python -m unittest discover -s apps/ml/tests -v
python -m pytest apps/backend/tests -q
python scripts/test_postgres_ml.py
```

Последняя команда требует Docker и создаёт уникальный временный PostgreSQL 17
с данными в tmpfs. Выполняет реальные миграции и сценарий upload → ML multipart →
извлечение DOCX → сохранение оценки → решение преподавателя, проверяет повреждённый
PDF. Удаляет только созданный ею контейнер, не использует существующий volume или
параметры проектной БД. Генерация Ollama в этом сценарии заменена заглушкой.
SQLite-тесты, PostgreSQL-сценарий и реальную генерацию запускают отдельно.
На отдельной Windows-машине фиксируйте модель/digest, версию runtime, контекст,
холодный/прогретый запуск, длительность, RAM/VRAM (`ollama ps`, GPU-метрики).
Сохраняйте результаты для хорошей, частичной, ошибочной, нерелевантной работы
и попытки prompt injection. Сравнивайте с экспертными замечаниями; отдельно
измеряйте ошибку оценок и полезность текста. Порог «75%» требует согласованной
метрики и размеченных работ. Автоматические тесты не подтверждают его достижение.

Результаты отдельного сравнения реальной генерации от 2026-11-08 приведены в
[отчёте оценки](ml-grading-evaluation.md): выбранная 14B совпала с метками в 13/14
числовых работ, два качественных ответа прошли только проверку формата.
Этот прогон использовал текстовые фикстуры и не проверял полный путь загрузки
документа через приложение.

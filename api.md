# API Moodle Lab Assessment Assistant

## 1. Назначение

Backend обслуживает LTI 1.1-приложение, встроенное в Moodle. Каждая лабораторная уже создана преподавателем в Moodle как отдельный модуль/элемент курса. При запуске конкретного модуля приложение открывает именно эту лабораторную: преподаватель задаёт материалы для ИИ-проверки, а студент загружает неограниченное количество попыток и отправляет выбранную попытку преподавателю.

API является REST API. Все даты и время передаются в ISO 8601 в UTC, например `2026-11-02T09:00:00Z`. В интерфейсе дата преобразуется в часовой пояс пользователя.

Базовый URL:

```text
https://<backend-host>/api
```

Служебные endpoints (`/lti/launch`, `/health`) не имеют префикса `/api`.

## 2. Термины и роли

| Термин | Значение |
|---|---|
| Курс | Курс Moodle, идентификатор которого передаётся в LTI `context_id`. |
| Лабораторная | Отдельный модуль Moodle с одной темой и собственными настройками ИИ. Один модуль Moodle = одна лабораторная. |
| Попытка | Одна загруженная студентом работа. Попытки одного студента не перезаписывают друг друга. |
| Настройки ИИ | Методичка, критерии, системные инструкции и эталонная работа. Каждый материал может быть текстом или файлом. |
| Оценка ИИ | Результат автоматической проверки конкретной попытки. |
| Решение преподавателя | Принятие работы или отправка на доработку с необязательным комментарием. |

Поддерживаются только роли, полученные от Moodle:

- `student` — работает с текущей лабораторной, открытой из модуля Moodle, загружает попытки и отправляет попытку преподавателю;
- `instructor` — настраивает текущую лабораторную, открытую из модуля Moodle, видит работы студентов и принимает решение по каждой работе.

Роль нельзя выбрать или изменить через API. Пользователь, курс и группа берутся из LTI launch.

## 3. Авторизация через LTI 1.1

### 3.1. Запуск приложения

```http
POST /lti/launch
Content-Type: application/x-www-form-urlencoded
```

Moodle отправляет подписанный OAuth 1.0 запрос LTI 1.1. Backend проверяет подпись по настроенным `LTI_CONSUMER_KEY` и `LTI_CONSUMER_SECRET`. При работе за reverse proxy URL для проверки подписи должен учитывать `X-Forwarded-Proto`.

Используемые параметры Moodle:

| Параметр | Обязателен | Назначение |
|---|---:|---|
| `user_id` | да | Стабильный идентификатор пользователя Moodle. |
| `roles` | да | Определение `student` или `instructor`. |
| `context_id` | да | Идентификатор курса Moodle. |
| `resource_link_id` | да | Стабильный идентификатор модуля Moodle; используется как идентификатор лабораторной. |
| `resource_link_title` | нет | Название модуля Moodle, например «ЛАБ 1». |
| `lis_person_name_full` | да | ФИО для отображения. |
| `lis_person_contact_email_primary` | нет | Email пользователя. |
| `Academic_group` | нет | Академическая группа студента, передаваемая Moodle. |
| `custom_deadline` | нет | Срок сдачи модуля, если он настроен в Moodle как пользовательский параметр LTI. |
| `custom_attempts_limit` | нет | Лимит попыток, если он настроен в Moodle как пользовательский параметр LTI. Пустое значение означает отсутствие лимита. |

`Instructor` и `Administrator` преобразуются в `instructor`; остальные поддержанные пользовательские роли — в `student`. Неизвестная или отсутствующая роль отклоняется.

`deadline` и `attempts_limit` не являются стандартными параметрами LTI 1.1. Moodle должен передавать их как `custom_deadline` и `custom_attempts_limit` в настройках конкретного LTI-модуля. Если эти параметры не переданы, backend использует `null`: срок сдачи не задан, количество попыток не ограничено.

Успешный ответ:

```http
HTTP/1.1 302 Found
Location: https://<frontend-host>/?token=<jwt>&lab_id=<resource_link_id>
```

`lab_id` — внутренний идентификатор записи, связанной с `resource_link_id`. Backend создаёт такую запись автоматически при первом запуске модуля; преподаватель не создаёт лабораторию через API. JWT содержит:

```json
{
  "sub": "moodle-user-id",
  "email": "student@example.org",
  "name": "Иванов Иван Иванович",
  "role": "student",
  "course_id": "moodle-course-id",
  "lab_id": "moodle-resource-link-id",
  "lab_title": "Описание лабораторной",
  "Academic_group": "ИВТ-301",
  "exp": 1793613600
}
```

Токен используется в API:

```http
Authorization: Bearer <jwt>
```

Ошибки:

```json
{
  "error": {
    "code": "LTI_VERIFICATION_FAILED",
    "message": "LTI request signature is invalid"
  }
}
```

| HTTP-код | Код | Когда |
|---:|---|---|
| 400 | `INVALID_LTI_REQUEST` | Не хватает обязательных LTI-параметров. |
| 403 | `LTI_VERIFICATION_FAILED` | Неверная OAuth-подпись или ключ. |
| 403 | `UNSUPPORTED_ROLE` | Роль Moodle не поддерживается. |

### 3.2. Текущий пользователь

```http
GET /api/me
Authorization: Bearer <jwt>
```

Ответ:

```json
{
  "id": "moodle-user-id",
  "name": "Иванов Иван Иванович",
  "email": "student@example.org",
  "role": "student",
  "course_id": "moodle-course-id",
  "Academic_group": "ИВТ-301"
}
```

Ошибки авторизации:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token"
  }
}
```

## 4. Общие правила API

### 4.1. Формат ошибок

Все ошибки имеют единый формат:

```json
{
  "error": {
    "code": "LAB_NOT_FOUND",
    "message": "Laboratory was not found",
    "details": {
      "lab_id": "lab-123"
    }
  }
}
```

`details` необязателен. Ошибка валидации может содержать массив:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request contains invalid fields",
    "fields": [
      {"field": "title", "message": "Field is required"}
    ]
  }
}
```

### 4.2. Пагинация и фильтры

Для списков используются:

```text
page=1
page_size=20
```

`page` начинается с `1`, допустимый `page_size` — от `1` до `100`, значение по умолчанию — `20`.

Ответ списка:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 0,
    "total_pages": 0
  }
}
```

### 4.3. Файлы

Разрешённые форматы:

- материалы настроек ИИ: `.pdf`, `.docx`, `.txt`;
- работа студента: `.pdf`, `.docx`.

Backend проверяет расширение, MIME-тип и фактический тип файла. Рекомендуемое ограничение — `20 MB` на один файл. Файл хранится с непредсказуемым внутренним именем; исходное имя возвращается только как метаданные.

## 5. Лабораторные работы

Все запросы к лабораторным ограничиваются `course_id` из JWT. Преподаватель не может получить лабораторию другого курса, даже если знает её идентификатор.

### 5.1. Контекст текущей лабораторной

Отдельного списка лабораторных и endpoint управления лабораторией в приложении нет: каждая лабораторная уже создана в Moodle как отдельный модуль курса. Студент и преподаватель попадают в приложение через LTI launch конкретного модуля.

Один модуль Moodle соответствует одной лабораторной:

```text
Модуль Moodle «ЛАБ 1. ...» -> лаборатория 1
Модуль Moodle «ЛАБ 2. ...» -> лаборатория 2
```

Идентификатором лаборатории служит `resource_link_id` из LTI 1.1. Backend автоматически создаёт или находит внутреннюю запись лаборатории при LTI launch.

### 5.2. Просмотр текущей лабораторной

```http
GET /api/labs/{lab_id}
Authorization: Bearer <jwt>
```

Доступно `instructor` и `student`. Студент может запросить только лабораторную,
переданную в его текущем LTI launch. Это нужно frontend для отображения темы,
описания, срока сдачи и лимита попыток до загрузки работы.

Ответ содержит только общие данные лабораторной. Настройки ИИ не включаются в endpoint просмотра лабораторной или работы преподавателем; они изменяются только через отдельные endpoints настройки (`/ai-settings`).

```json
{
  "id": "lab-123",
  "title": "Лабораторная работа №1. Работа с массивами",
  "description": "...",
  "deadline": "2026-11-28T23:59:00Z",
  "attempts_limit": null
}
```

Для преподавателя дополнительно возвращается `course_id`.

`deadline` — срок сдачи в UTC, полученный из `custom_deadline`. Если custom-параметр не передан, возвращается `null`. `attempts_limit` — максимально допустимое количество попыток, полученное из `custom_attempts_limit`; значение `null` означает, что количество попыток не ограничено.

Студент не может получить настройки ИИ или список лабораторных. Он может
получить только контекст текущей лабораторной по `lab_id` из своего LTI launch.

### 5.3. Управление модулем Moodle

Название, доступность и удаление модуля управляются в Moodle. Backend не предоставляет endpoints для изменения или удаления самой лабораторной.

## 6. Настройки ИИ

У лаборатории может быть от нуля до четырёх материалов. Для успешного сохранения должен быть задан хотя бы один из них. Каждый материал задаётся либо текстом, либо файлом, но не обоими одновременно.

Поддерживаемые поля:

| Поле | Тип | Форматы |
|---|---|---|
| `methodical_guide` | текст или файл | PDF, DOCX, TXT |
| `grading_criteria` | текст или файл | PDF, DOCX, TXT |
| `system_instructions` | текст или файл | PDF, DOCX, TXT |
| `reference_work` | текст или файл | PDF, DOCX, TXT |

### 6.1. Чтение настроек ИИ

```http
GET /api/labs/{lab_id}/ai-settings
Authorization: Bearer <jwt>
```

Доступно только преподавателю. Endpoint возвращает полный текущий набор
материалов перед сохранением. Это необходимо, потому что `PUT` заменяет весь
набор настроек, а не изменяет только переданные поля.

Если настройки ещё не сохранены, возвращается `200 OK`:

```json
{
  "lab_id": "lab-123",
  "version": 0,
  "settings_status": "not_configured",
  "updated_at": null,
  "methodical_guide": null,
  "grading_criteria": null,
  "system_instructions": null,
  "reference_work": null
}
```

Пример настроек с текстом и файлом:

```json
{
  "lab_id": "lab-123",
  "version": 3,
  "settings_status": "configured",
  "updated_at": "2026-11-03T10:20:00Z",
  "methodical_guide": {
    "text": "Методические указания...",
    "file": null
  },
  "grading_criteria": {
    "text": null,
    "file": {
      "file_id": "file-123",
      "name": "Критерии.pdf",
      "size": 24576,
      "content_type": "application/pdf",
      "download_url": "/api/files/file-123/download"
    }
  },
  "system_instructions": null,
  "reference_work": null
}
```

### 6.2. Загрузка файла материала

```http
POST /api/labs/{lab_id}/ai-settings/files
Authorization: Bearer <jwt>
Content-Type: multipart/form-data
```

Поля формы:

```text
field=methodical_guide
file=<binary>
```

Ответ: `201 Created`.

```json
{
  "file_id": "file-1",
  "field": "methodical_guide",
  "name": "guide.pdf",
  "size": 183420,
  "content_type": "application/pdf"
}
```

Файл загружается во временное хранилище и становится частью настроек только после сохранения настроек.

### 6.3. Сохранение настроек

```http
PUT /api/labs/{lab_id}/ai-settings
Authorization: Bearer <jwt>
Content-Type: application/json
```

Доступ: только `instructor`.

Пример с текстом и ранее загруженным файлом:

```json
{
  "methodical_guide": {"file_id": "file-1"},
  "grading_criteria": {"text": "Максимум 10 баллов. Корректность — 6..."},
  "system_instructions": {"text": "Отвечай на русском языке..."},
  "reference_work": null
}
```

Хотя бы одно поле должно быть не `null`. При сохранении создаётся новая версия настроек. Уже запущенные проверки используют снимок настроек, с которым они были запущены; изменение настроек не меняет прошлые результаты.

Ответ:

```json
{
  "lab_id": "lab-123",
  "version": 3,
  "settings_status": "configured",
  "updated_at": "2026-11-02T09:30:00Z"
}
```

Ошибки: `400 SETTINGS_EMPTY`, `400 INVALID_MATERIAL`, `404 LAB_NOT_FOUND`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_FILE_TYPE`.

### 6.4. Удаление отдельного материала

```http
DELETE /api/labs/{lab_id}/ai-settings/{field}
Authorization: Bearer <jwt>
```

`field` принимает `methodical_guide`, `grading_criteria`, `system_instructions` или `reference_work`. Удаление последнего материала разрешено только как промежуточное состояние; до запуска новой проверки настройки должны снова содержать хотя бы один материал.

## 7. Попытки студента

### 7.1. Список своих попыток

```http
GET /api/labs/{lab_id}/attempts?page=1&page_size=20
Authorization: Bearer <jwt>
```

Доступ: только `student`. Backend возвращает только попытки текущего пользователя в лаборатории, открытой через LTI launch. Попытки других студентов и другие лаборатории недоступны.

Ответ:

```json
{
  "items": [
    {
      "id": "attempt-456",
      "number": 2,
      "submitted_at": "2026-11-02T10:15:00Z",
      "file": {"id": "file-2", "name": "lab1.docx", "size": 84512},
      "status": "ai_checked",
      "ai_score": 8.5,
      "ai_conclusion": "Работа соответствует большинству критериев...",
      "teacher_comment": null
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 2,
    "total_pages": 1
  }
}
```

### 7.2. Загрузка новой попытки

```http
POST /api/labs/{lab_id}/attempts
Authorization: Bearer <jwt>
Content-Type: multipart/form-data
```

Поле формы:

```text
file=<PDF или DOCX>
```

Дата и время `submitted_at` устанавливаются backend при успешном приёме файла и не принимаются от клиента. Количество попыток определяется полем `attempts_limit` текущей лаборатории. При значении `null` количество попыток не ограничивается; при достижении лимита backend возвращает `409 ATTEMPT_LIMIT_REACHED`.

Ответ: `202 Accepted`.

```json
{
  "id": "attempt-456",
  "number": 2,
  "submitted_at": "2026-11-02T10:15:00Z",
  "status": "processing",
  "ai_score": null,
  "ai_conclusion": null
}
```

После ответа проверка выполняется асинхронно. Если настройки ИИ пусты, загрузка отклоняется с `409 AI_SETTINGS_NOT_CONFIGURED`.

### 7.3. Просмотр попытки

```http
GET /api/attempts/{attempt_id}
Authorization: Bearer <jwt>
```

Студент видит только свои попытки в открытой лабораторной, включая попытку, которую он отправил преподавателю. Преподаватель видит попытки только лабораторий своего курса. Ответ содержит файл, статус, оценку ИИ, заключение ИИ и комментарий преподавателя, если он есть.

### 7.4. Отправка попытки преподавателю

```http
POST /api/attempts/{attempt_id}/submit-to-teacher
Authorization: Bearer <jwt>
```

Доступ: студент — только для своей попытки со статусом `ai_checked` или `returned_for_revision`.

Ответ:

```json
{
  "id": "attempt-456",
  "status": "ai_checked"
}
```

Отправка преподавателю не меняет статус попытки. Студент видит свои попытки, включая отправленную преподавателю, а преподаватель получает её в списке работ. До явного решения преподавателя статус остаётся тем же, который был у попытки после проверки ИИ.

## 8. Проверка ИИ и статусы

### 8.1. Жизненный цикл попытки

```text
processing
    -> ai_checked
    -> accepted
    -> returned_for_revision
```

Из `returned_for_revision` студент может отправить ту же попытку повторно, либо загрузить новую. Статус `processing` означает, что ИИ ещё проверяет работу; `ai_checked` — проверка завершена. Отправка работы преподавателю не создаёт отдельный статус: до решения преподавателя сохраняется `ai_checked`.

В списке преподавателя отображаются:

| Статус API | Текст в интерфейсе |
|---|---|
| `processing` | В обработке |
| `ai_checked` | Проверено ИИ |
| `accepted` | Принято |
| `returned_for_revision` | На доработку |

### 8.2. Получение результата ИИ

```http
GET /api/attempts/{attempt_id}/ai-result
Authorization: Bearer <jwt>
```

Ответ при завершённой проверке:

```json
{
  "attempt_id": "attempt-456",
  "status": "ai_checked",
  "score": 8.5,
  "max_score": 10,
  "conclusion": "Работа соответствует большинству критериев.",
  "criteria": [
    {
      "name": "Корректность алгоритма",
      "score": 5.5,
      "max_score": 6,
      "comment": "Основной алгоритм реализован верно."
    }
  ],
  "settings_version": 3,
  "checked_at": "2026-11-02T10:16:20Z"
}
```

Пока проверка идёт, endpoint возвращает `202` и `status: processing`.

## 9. Работы преподавателя

### 9.1. Список работ

```http
GET /api/labs/{lab_id}/submissions
  ?status=all
  &student_name=Иванов
  &Academic_group=ИВТ-301
  &page=1
  &page_size=20
Authorization: Bearer <jwt>
```

Доступ: только `instructor`.

Параметр `status` принимает:

- `all` — все отправленные преподавателю работы;
- `ai_checked` — работы с завершённой проверкой ИИ;
- `returned_for_revision` — работы со статусом «На доработку».

Для вкладки «Проверено ИИ» включать `ai_checked`. Для вкладки «Все работы» используются `all`. До решения преподавателя работа сохраняет статус `ai_checked`.

Фильтры независимы:

- `student_name` — отдельный поиск по ФИО студента; ищет частичное совпадение без учёта регистра;
- `Academic_group` — отдельный фильтр группы; frontend получает доступные группы из списка и передаёт выбранное значение. Backend принимает только группу, которая есть среди студентов текущей лаборатории, и применяет точное совпадение.

Если оба параметра указаны, применяются оба фильтра одновременно. Сортировка по умолчанию: новые отправленные работы первыми.

Ответ:

```json
{
  "items": [
    {
      "attempt_id": "attempt-456",
      "student": {
        "id": "moodle-user-id",
        "name": "Иванов Иван Иванович",
        "Academic_group": "ИВТ-301"
      },
      "submitted_at": "2026-11-02T10:15:00Z",
      "ai_score": 8.5,
      "status": "ai_checked"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1
  }
}
```

В список попадают только попытки, которые студент отправил преподавателю. Незавершённые попытки и попытки, оставшиеся на стороне студента, не отображаются.

### 9.2. Статистика по лаборатории

```http
GET /api/labs/{lab_id}/submissions/statistics
Authorization: Bearer <jwt>
```

Доступ: только `instructor`.


Подсчёт выполняется по попыткам:

- `total_submitted` — всего попыток, отправленных преподавателю;
- `submitted_today` — попыток, отправленных преподавателю с начала текущих суток по UTC;
- `ai_checked` — попыток, проверенных ИИ и ещё не принятых и не отправленных на доработку;
- `accepted` — попыток, принятых преподавателем;
- `returned_for_revision` — попыток, отправленных на доработку;
- `processing` — попыток, которые сейчас проверяются ИИ.

Ответ:

```json
{
  "lab_id": "lab-123",
  "statistics": {
    "total_submitted": 128,
    "submitted_today": 7,
    "ai_checked": 18,
    "accepted": 74,
    "returned_for_revision": 36,
    "processing": 3
  },
  "calculated_at": "2026-11-02T10:30:00Z"
}
```

`total_submitted`, `submitted_today`, `ai_checked`, `accepted` и `returned_for_revision` считаются по попыткам, которые студент отправил преподавателю. `processing` считается по всем попыткам текущей лаборатории, которые сейчас проверяются ИИ, даже если студент ещё не отправил результат преподавателю. Один студент может иметь несколько попыток, каждая попытка считается отдельно.

### 9.3. Список групп для фильтра

```http
GET /api/labs/{lab_id}/submission-groups
Authorization: Bearer <jwt>
```

Доступ: только `instructor`.

Endpoint возвращает уникальные значения `Academic_group` только из студентов, чьи работы доступны преподавателю в текущей лабораторной. Frontend использует этот ответ для выпадающего списка групп.

Ответ:

```json
{
  "items": [
    {"Academic_group": "ИВТ-301"},
    {"Academic_group": "ИВТ-302"},
    {"Academic_group": "ИВТ-303"}
  ]
}
```

### 9.4. Просмотр работы преподавателем

```http
GET /api/instructor/attempts/{attempt_id}
Authorization: Bearer <jwt>
```

Ответ:

```json
{
  "id": "attempt-456",
  "lab": {
    "id": "lab-123",
    "title": "Лабораторная работа №1. Работа с массивами",
    "deadline": "2026-11-28T23:59:00Z",
    "attempts_limit": null
  },
  "student": {
    "id": "moodle-user-id",
    "name": "Иванов Иван Иванович",
    "Academic_group": "ИВТ-301"
  },
  "files": [
    {
      "id": "file-2",
      "name": "report.pdf",
      "download_url": "/api/files/file-2/download"
    },
    {
      "id": "file-3",
      "name": "attachment.docx",
      "download_url": "/api/files/file-3/download"
    }
  ],
  "submitted_at": "2026-11-02T10:15:00Z",
  "status": "ai_checked",
  "ai_score": 9.2,
  "ai_max_score": 10,
  "ai_conclusion": "Работа соответствует основным критериям. Структура отчёта и реализация алгоритма корректны. Рекомендуется проверить оформление выводов.",
  "teacher_comment": null,
  "actions": {
    "can_return_for_revision": true,
    "can_accept": true
  }
}
```

### 9.5. Решение преподавателя

```http
POST /api/instructor/attempts/{attempt_id}/review
Authorization: Bearer <jwt>
Content-Type: application/json
```

Доступ: только `instructor`, работа должна быть отправлена преподавателю. Открытие этого endpoint и ввод/изменение комментария не меняют статус работы.

Endpoint возвращает ровно данные, необходимые для карточки проверки работы:

- ФИО студента;
- группу студента;
- название лабораторной;
- статус работы;
- список загруженных студентом файлов;
- оценку и заключение ИИ;
- комментарий преподавателя;
- доступные действия: «На доработку» и «Принять работу».

Настройки ИИ, методичка, критерии, системные инструкции и эталонная работа в этот ответ не входят.

Принять работу:

```json
{
  "decision": "accept",
  "comment": "Работа принята."
}
```

Отправить на доработку:

```json
{
  "decision": "return_for_revision",
  "comment": "Исправьте обработку пустого массива."
}
```

Для `return_for_revision` комментарий обязателен. Для `accept` комментарий необязателен. До нажатия кнопки статус и данные работы не меняются. Только после явного нажатия «На доработку» или «Принять работу» frontend отправляет этот запрос, а backend меняет статус и сохраняет комментарий преподавателя. Если преподаватель только открыл работу или написал комментарий, сохраняется текущий статус, а решение ещё не фиксируется. Ответ:

```json
{
  "attempt_id": "attempt-456",
  "status": "accepted",
  "teacher_review": {
    "decision": "accept",
    "comment": "Работа принята.",
    "reviewed_by": "moodle-instructor-id",
    "reviewed_at": "2026-11-02T11:00:00Z"
  }
}
```

Повторное решение преподавателя разрешено только для исправления ошибочного решения и должно сохранять историю review. При принятии работы backend фиксирует оценку, которая была выставлена ИИ на момент решения.

## 10. Файлы

```http
GET /api/files/{file_id}/download
Authorization: Bearer <jwt>
```

Доступ проверяется по связи файла с лабораторией и пользователем. Студент не может скачать материалы ИИ, принадлежащие другой лабораторной, или чужую работу. Преподаватель может скачать работы только из своего курса.

Backend может вернуть короткоживущий URL вместо проксирования файла. URL не должен быть доступен без авторизации дольше срока, заданного конфигурацией.

## 11. Интеграция оценки с Moodle

На первом этапе балл сохраняется в приложении и показывается студенту и преподавателю. Для синхронизации итоговой оценки с Moodle рекомендуется отдельный LTI 1.1 Outcomes endpoint:

```text
POST /api/instructor/attempts/{attempt_id}/publish-grade
```

Он должен быть включён только после настройки Moodle `lis_outcome_service_url`, `lis_result_sourcedid` и OAuth-параметров. До включения этой интеграции endpoint возвращает `501 OUTCOMES_NOT_CONFIGURED`. Автоматическая отправка оценки в Moodle без настроенного Outcomes Service запрещена.

## 12. Матрица доступа

| Endpoint | Student | Instructor |
|---|---:|---:|
| `POST /lti/launch` | LTI | LTI |
| `GET /api/me` | да | да |
| `GET /api/labs/{id}` | да, текущая | да |
| `GET /api/labs/{id}/ai-settings` | нет | да |
| `PUT /api/labs/{id}/ai-settings` | нет | да |
| `GET /api/labs/{id}/attempts` | свои | нет |
| `POST /api/labs/{id}/attempts` | да | нет |
| `GET /api/attempts/{id}` | свои | нет |
| `POST /api/attempts/{id}/submit-to-teacher` | свои | нет |
| `GET /api/labs/{id}/submissions` | нет | да |
| `GET /api/labs/{id}/submissions/statistics` | нет | да |
| `GET /api/labs/{id}/submission-groups` | нет | да |
| `GET /api/instructor/attempts/{id}` | нет | да |
| `POST /api/instructor/attempts/{id}/review` | нет | да |

Во всех случаях кроме LTI launch дополнительно проверяются `course_id`, принадлежность ресурса текущему курсу и права на конкретную лабораторную/попытку. Для студента также проверяется, что `lab_id` совпадает с лабораторной, переданной в текущем LTI launch.

## 13. Сводка HTTP-кодов

| Код | Назначение |
|---:|---|
| 200 | Успешное чтение или изменение. |
| 201 | Ресурс или временный файл создан. |
| 202 | Попытка принята и передана на асинхронную проверку. |
| 302 | Успешный LTI launch, перенаправление во frontend. |
| 400 | Ошибка формата или валидации запроса. |
| 401 | Нет токена или токен недействителен. |
| 403 | Недостаточно прав или неверная LTI-подпись. |
| 404 | Ресурс не найден в доступном пользователю курсе. |
| 409 | Конфликт состояния, например настройки ИИ не заданы. |
| 413 | Файл превышает лимит размера. |
| 415 | Неподдерживаемый тип файла. |
| 422 | Запрос не прошёл структурную валидацию. |
| 501 | Функция не настроена, например Moodle Outcomes Service. |
# PDF-отчёт об оценивании

[Скачать отчёт за 8 ноября 2026 года](ml-grading-evaluation-2026-11-08.pdf).

Источник текста и таблиц — [Markdown-отчёт](../ml-grading-evaluation.md).
PDF содержит те же результаты и ограничения, включая неверные оценки.

Для повторного экспорта из корня репозитория нужны Python 3, ReportLab и шрифты
DejaVu Sans / DejaVu Sans Mono. Экспорт проверен с `reportlab==4.2.5`:

```sh
python3 -m venv /tmp/grading-report-venv
/tmp/grading-report-venv/bin/pip install reportlab==4.2.5
/tmp/grading-report-venv/bin/python scripts/export_grading_report.py
```

Сам экспорт не использует сеть, Ollama, БД или файлы локальных сессий.
По умолчанию шрифты берутся из `/usr/share/fonts/truetype/dejavu`;
другой каталог задаётся через `--font-directory`. Шрифты встраиваются в PDF.
Ссылки на исходники ведут в GitHub. Параметры `--source` и `--output` позволяют
выбрать другой исходник или путь результата. Экспортёр поддерживает используемые
в этом отчёте заголовки, абзацы, таблицы, ссылки, жирный текст и код внутри строки.

При одинаковых исходнике, шрифтах и версии ReportLab повторный экспорт даёт
одинаковый PDF; изменяющееся время сборки в файл не записывается.

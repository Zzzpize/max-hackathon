# 06. ТЗ Backend — модуль «Домашки»

## Роль

Зона ответственности: новый модуль `backend/app/modules/homework/` +
роутер `backend/app/routers/homework.py`. Генерация домашних заданий
через GigaChat, хранение, редактирование, экспорт в TXT и PDF.
Модули `roadmap`, `check`, `generate` (для контрольных), `memory`,
`dashboard` — вне зоны. Frontend и бот — вне зоны.

Модуль **полностью независим** от модуля проверки: сгенерированная
здесь домашка НЕ становится автоматически `WorkTemplate`. Если
учитель захочет проверить эту же домашку через модуль проверки —
он вручную создаёт `WorkTemplate` в другой части приложения.
Ноль связей на уровне данных.

Пути в этом документе — от корня репозитория.

## Контракт

Endpoints добавляются в `openapi.yaml` под `/homework`. Согласовать с
Team Lead. Auth — `X-Init-Data` для MiniApp, `Bearer + X-Teacher-Id`
для бота через `app.auth.current_teacher`.

## Что мы расширяем

Существующий модуль `app/modules/generate/pipeline.py::generate_work`
создаёт контрольные для модуля проверки (`WorkTemplate`). Мы **не
трогаем его**, но **выделяем общую LLM-логику** генерации задач в
`app/modules/generate/core.py` (см. задачу 5), которую переиспользуют
и `generate_work`, и наш новый `generate_homework`. Разные модели
хранения, общий движок генерации.

## Задачи

Сгруппировано по компонентам, от базового к продвинутому.

### Модель данных

1. Добавить таблицу `homeworks`:
   - `id: str` (PK, uuid)
   - `teacher_id: str` (index, NOT NULL)
   - `title: str` — например «Домашка на 12.10: дроби»
   - `subject: str` — `math | algebra | physics | geometry`
   - `grade: int` — 1..11
   - `topic: str` — узкая тема (например «Сложение обыкновенных дробей»)
   - `prompt: str` — исходный запрос учителя
   - `tasks: JSONB` — список задач: `[{index, statement, expected_answer, difficulty?}]`
   - `notes: str | None` — заметки учителя (опционально)
   - `created_at: datetime`
   - `updated_at: datetime`
2. Alembic-миграция `0005_homeworks.py`.
3. Обновить `app/models/__init__.py` — добавить экспорт `Homework`.

### Общий движок генерации (рефакторинг)

4. Выделить из `app/modules/generate/pipeline.py::generate_work` общую
   часть в `app/modules/generate/core.py::generate_tasks(
   subject: str, grade: int, topic: str, n_tasks: int,
   extra_context: str) → list[dict]`:
   - Собирает system_prompt (с учётом subject+grade)
   - Вызывает GigaChat
   - Возвращает список задач в формате
     `[{index, statement, expected_answer, difficulty?}]`
5. Существующий `generate_work` переписать поверх `generate_tasks`
   (backward-compatible — форма ответа `WorkTemplate` та же).
6. Обновить system_prompt под все предметы. Ветвление в промпте:
   - `math` (1-4): арифметика, простые уравнения
   - `algebra` (5-11): уравнения, неравенства, функции
   - `geometry` (5-11): планиметрия, стереометрия, теоремы
   - `physics` (5-11): расчётные задачи, формулы, единицы измерения

### Homework pipeline

7. Модуль `app/modules/homework/pipeline.py::generate_homework(
   teacher_id: str, subject: str, grade: int, topic: str,
   n_tasks: int, prompt: str) → Homework`:
   - Вызывает `core.generate_tasks(subject, grade, topic, n_tasks, prompt)`
   - Оборачивает результат в ORM-объект `Homework` (не коммитит)
   - Генерирует `title` если учитель не задал: `"<Тема>, <дата>"`
8. Валидация задач:
   - `n_tasks` — 1..30
   - Каждая задача: `statement` не пустой, `expected_answer` не пустой
   - `difficulty` (если есть): один из `easy | medium | hard`

### REST endpoints

9. `POST /homework` — сгенерировать домашку. Body:
   `{title?: str, subject: str, grade: int, topic: str, n_tasks: int,
   prompt: str}`. 201 + Homework.
10. `GET /homework` — список домашек учителя. Query: `limit=50`,
    `offset=0`, `subject?`, `grade?`, `topic?` (для поиска). Сортировка:
    `updated_at DESC, id`.
11. `GET /homework/{id}` — одна домашка. 403 если чужая, 404 если не
    найдена.
12. `PATCH /homework/{id}` — ручное редактирование. Может менять
    `title`, `notes`, `tasks` (заменяет целиком). Валидация (задача 8).
13. `POST /homework/{id}/regenerate` — сгенерировать новую версию
    задач при том же контексте, но со свежей LLM-выдачей. Body:
    `{extra_prompt?: str}` — дополнительный контекст. Перезаписывает
    `tasks` в той же записи. 200 + Homework.
14. `DELETE /homework/{id}` — удаление. 204 No Content.
15. `GET /homework/{id}/export?format=txt|pdf` — скачивание.
    Content-Disposition: `filename="homework-<title>-<date>.<ext>"`.

### Экспорт

16. Модуль `app/modules/homework/export.py`:
    - `render_txt(hw: Homework) → bytes` — только задания, без
      ответов. Формат:
      ```
      Домашнее задание
      Предмет: <subject_ru>, класс: <grade>
      Тема: <topic>
      Дата: <today>

      1. <statement>

      2. <statement>

      ...

      ---
      Ответы (для учителя)
      1. <expected_answer>
      2. <expected_answer>
      ```
    - `render_pdf(hw: Homework) → bytes` — A4. Первая часть: задания
      с пробелами для решений (по 3-5 строк на задачу). Последняя
      страница: ответы. Библиотека — та же, что в модуле роадмапов
      (согласовать).
17. Учителю в TXT/PDF полезны обе части (для раздачи ученикам —
    первая, для проверки — вторая). Если понадобится «только задания»
    без ответов — добавить query-параметр `?with_answers=false`
    (задача P2).

## API

Полный перечень в `openapi.yaml` под `/homework`. Auth — обе схемы.

## Business logic

### Изоляция

Модуль не читает и не пишет в `work_templates`, `submissions`,
`students`, `roadmaps`. Если учитель хочет «использовать эту домашку
как контрольную» — он вручную создаёт `WorkTemplate` через
существующий поток проверки.

### Разница с `POST /works/generate`

- `POST /works/generate` — создаёт `WorkTemplate`, который живёт в
  модуле проверки и используется для сверки с фото учеников. Строгие
  ответы, ориентация на автоматическую сверку.
- `POST /homework` — создаёт `Homework`, который живёт в модуле
  домашек. Может содержать открытые задачи, задачи на объяснение и
  т.п. Ориентация на печать/раздачу.

При этом оба используют общий движок `generate_tasks` — так что
качество генерации улучшается для обоих одновременно, когда
дорабатывается промпт.

### Свобода учителя

- Хранит сколько угодно домашек
- Может править задания и ответы вручную после генерации
- Может регенерировать (создаёт новую версию поверх той же записи)

## Validation

- `topic` — 1..200 символов
- `prompt` — 5..2000 символов
- `title` — 1..200 символов (если задан)
- `subject` — enum, `grade` — 1..11
- `n_tasks` — 1..30

## Error handling

- Аналогично модулю роадмапов: LLM retry×1, при повторной ошибке 502.

## Tests

Минимум:

18. `tests/test_homework_api.py::test_generate_and_list` — POST /homework
    с моковым LLM → GET /homework возвращает 1 запись.
19. `tests/test_homework_api.py::test_tenant_isolation` — учитель B не
    видит домашки учителя A.
20. `tests/test_homework_api.py::test_regenerate_replaces_tasks` —
    POST /homework/{id}/regenerate меняет `tasks`, `id` остаётся.
21. `tests/test_homework_export.py::test_txt_contains_all_tasks` —
    TXT-экспорт содержит все задания и ответы.
22. `tests/test_generate_core.py::test_shared_engine` — общий
    `generate_tasks` вызывается и из `generate_work`, и из
    `generate_homework` с корректными параметрами.

## Definition of Done

1. `docker compose up backend` — миграция 0005 применяется.
2. `POST /homework` возвращает домашку с ≥ 3 задачами для валидного
   запроса по всем subject+grade комбинациям (math/algebra/physics/
   geometry × 1..11).
3. `GET /homework/{id}/export?format=txt` содержит и задания, и
   ответы, каждая часть читаемая.
4. `POST /homework/{id}/regenerate` работает.
5. Все 5 smoke-тестов проходят.
6. Кросс-тенантный доступ отсутствует.
7. Модуль генерации `WorkTemplate` (`generate_work`) продолжает
   работать после рефакторинга — существующий тест `test_generate.py`
   не сломан.

## Priority

### P0

Задачи 1–3, 4–6 (общий движок + subject-поддержка), 7–12, 14, 16
(TXT).

### P1

Задачи 13 (regenerate), 15 (endpoint экспорта), 16 (PDF), 18–22.

### P2

Задача 17 (`with_answers` флаг), фильтрация в GET по subject/grade
(задача 10 — базовое реализовано, поиск по topic — P2).

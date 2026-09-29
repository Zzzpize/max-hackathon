# Помощник учителя — проверка контрольных в MAX

Чат-бот и мини-приложение в мессенджере MAX для автоматической
проверки математических контрольных работ учеников 2–4 классов.

**Prod:** https://max.nc-group.space
**Бот:** `@t680_hakaton_max_bot` в MAX

## Основной пользовательский сценарий

1. Учитель открывает мини-приложение через бота, создаёт контрольную
   (тема, задания, эталонные ответы) и добавляет учеников класса.
2. Учитель выбирает работу и ученика — либо в MiniApp, либо через
   команды `/work` и `/student` в чате бота.
3. Учитель фотографирует работу ученика и отправляет боту в чат
   (или загружает через MiniApp).
4. Бот распознаёт ответы через GigaChat Vision, сверяет с эталоном,
   объясняет ошибки и оценивает уверенность.
5. Учитель открывает результат в MiniApp и одним свайпом
   подтверждает/правит оценку.
6. Результат уходит в долгосрочный профиль ученика — типовые
   ошибки, слабые темы, тренд.

## Архитектура

```
      MAX (мессенджер)
        │        │
   webhook   miniapp iframe
        │        │
        ▼        ▼
     ┌──────┐ ┌─────────┐
     │ bot  │ │ miniapp │ (nginx + static React)
     │ (TS) │ │ (React) │
     └──┬───┘ └────┬────┘
        │          │ /api
        │          ▼
        │     ┌──────────────┐      HTTPS
        └────►│   backend    │────────────► GigaChat
              │   (FastAPI)  │
              └──────┬───────┘
                     │
                     ▼
              ┌────────────┐
              │ PostgreSQL │
              └────────────┘
```

Три сервиса приложения:

- **backend** — FastAPI + PostgreSQL + GigaChat SDK. Модульная
  архитектура (`modules/check`, `modules/memory`, `modules/generate`).
- **bot** — Node.js + TypeScript. Использует официальный SDK
  `@maxhub/max-bot-api`. Внутренний HTTP-сервер на 3001 для
  push-уведомлений от backend.
- **miniapp** — React + Vite + TypeScript. Обслуживается через nginx,
  который проксирует `/api` в backend и `/webhook/*` в bot.

Общий стейт учителя (выбранная работа и ученик) — в БД, через
`GET/PUT /teachers/{id}/state`. Оба клиента синхронизированы: что
выбрал через бот — увидишь в MiniApp, и наоборот.

## Локальный запуск

Нужен Docker и Docker Compose v2.

```bash
cp .env.example .env
# заполнить GIGACHAT_CLIENT_ID/SECRET и MAX_BOT_TOKEN
docker compose up --build
```

Порты по умолчанию:

- `8000` — backend (OpenAPI: http://localhost:8000/docs)
- `3000` — bot webhook приёмник
- `3001` — bot internal API (health, notify)
- `80` — miniapp (SPA + `/api` reverse proxy)
- `5432` — postgres (только внутри compose сети)

Бот в локальном режиме работает через long polling (без публичного
HTTPS). MiniApp можно открыть на http://localhost, но без MAX Bridge
скрипт покажет fallback `teacher-stub`.

## Прод-запуск

Prod-сервер: Ubuntu 22.04, Docker 29.6, Compose v5.3.
Reverse-proxy — Caddy (в составе другого проекта), выдаёт
Let's Encrypt автоматически.

`docker-compose.prod.yml` — override для prod:

- Убраны биндинги портов (postgres, backend, bot, miniapp)
- MiniApp дополнительно подключён к внешней сети `mptime_default`,
  чтобы Caddy мог до него достучаться

Деплой одной командой:

```bash
python deploy.py                 # обновить все сервисы
python deploy.py bot             # обновить только бот
python deploy.py bot miniapp     # несколько сервисов
python deploy.py --recreate      # с даунтаймом (down + up)
```

Скрипт читает креды из `tmp/deploy.env` (gitignored) или из
переменных окружения `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PASSWORD`,
`DEPLOY_PATH`.

Установка домена в Caddy на сервере — уже сделана. Блок в
`/opt/mptime/Caddyfile`:

```
max.nc-group.space {
    encode gzip zstd
    reverse_proxy max-checker-miniapp-1:80
}
```

При изменении Caddyfile — `docker exec mptime-caddy-1 caddy reload`.

## Переменные окружения

См. `.env.example`. Обязательные:

- `GIGACHAT_CLIENT_ID` + `GIGACHAT_CLIENT_SECRET` — GigaChat Ultra.
  Backend сам считает base64 credentials.
- `MAX_BOT_TOKEN` — токен бота от организаторов
- `MAX_BOT_USERNAME` — публичный username бота (для OpenAppButton)
- `MAX_WEBHOOK_DOMAIN` — если задан, бот регистрирует webhook в
  MAX. Иначе — long polling.

Опциональные:

- `MAX_WEBHOOK_SECRET` — если хочется дополнительной защиты webhook
- `MINIAPP_PUBLIC_URL` — публичный URL MiniApp, используется для
  формирования ссылок из бота
- `GIGACHAT_AUTH_KEY` — можно указать base64 напрямую вместо
  `CLIENT_ID`+`CLIENT_SECRET`

## Работа с данными

MVP использует **синтетические работы** для демонстрации. Реальные
фото работ учеников на этапе пилота хранятся на volume
`storage_data` в обезличенном виде: соответствие `student_id → ФИО`
знает только учитель, в БД хранится псевдоним. Обработка ведётся
через GigaChat API (российская инфраструктура). Согласия родителей —
часть пилотного пакета.

Русские trusted CA (Минцифры) установлены в Docker-образы бота и
бэкенда, чтобы Node/Python доверяли сертификатам `*.max.ru` и
GigaChat.

## Состав команды и зоны ответственности

- **Frontend + MAX + DevOps** — `miniapp/`, `bot/`, `docker-compose.*`,
  `deploy.py`, инфра.
- **Backend + LLM** — `backend/`, GigaChat интеграция, пайплайн
  проверки, БД.
- **PM/Analytics** — `tmp/`, пилотные метрики, согласие партнёров,
  проверка GigaChat Vision на реальных фото.

Контракт API — `openapi.yaml` в корне.

## Проверка основного сценария (для жюри)

1. Открыть в MAX бот `@t680_hakaton_max_bot`.
2. Отправить `/start`, нажать «Открыть мини-приложение».
3. Создать одну контрольную (`/works/new`).
4. Создать одного ученика (`/students/new`).
5. Выбрать работу и ученика через кнопки «Сменить» в Hub — или в
   боте командами `/work` и `/student`.
6. Отправить фото контрольной боту в чат или через кнопку
   «Загрузить фото работы» в MiniApp.
7. Дождаться push-уведомления «работа готова» → открыть результат в
   MiniApp → подтвердить.

## Известные ограничения MVP

- Только математика 2–4 классов, только фото рукописных работ.
- Открытые задания (сочинения, развёрнутые ответы) не проверяются.
- Оценка выставляется только после подтверждения учителем.
- Валидация MAX WebApp initData на бэкенде — P1, сейчас клиент
  посылает `teacher_id` в query. В продакшн-сценарии заменить на
  HMAC-валидацию по бот-токену.
- В боте состояние диалога живёт в БД (`teacher_states`) — если
  бэкенд-сервис перезапускается, стейт сохраняется. Если down на
  несколько минут — команды бота будут отвечать «попробуй ещё раз».

## Документация

- `backend/HOMEWORK.md` — реализация модуля домашних заданий, контракт,
  запуск тестов и замечание по авторизованному скачиванию файлов в MiniApp
- `openapi.yaml` — контракт REST API
- `tmp/01_concept.md` — концепция продукта, проблема, ценность
- `tmp/02_architecture.md` — детальная архитектура и модель данных
- `tmp/03_tz_backend.md` — ТЗ бэкендера
- `tmp/04_tz_frontend.md` — ТЗ фронта/MAX/DevOps
- `tmp/max_notes.md` — справочник по MAX Bot API и Bridge
- `tmp/server.md` — заметки по прод-серверу и Caddy

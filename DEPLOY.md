# Деплой калькулятора совместимости

Сайт — это **один Flask-приложение** (`backend/app.py`), которое отдаёт страницу из корня проекта (`index.html`, `script.js`, `styles.css`). Для продакшена нужны **переменные окружения** (ключи API, Telegram, база).

## Обязательные переменные в проде

| Переменная | Зачем |
|------------|--------|
| `DATABASE_URL` | PostgreSQL на хостинге (рекомендуется). Формат: `postgresql+psycopg2://USER:PASS@HOST:5432/DBNAME` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Уведомления о заявках |
| `DEEPSEEK_API_KEY` | Чат с экспертом |

Опционально: `CRM_WEBHOOK_URL`, `TELEGRAM_HTTPS_PROXY`.

**Почему не serverless Vercel для заявок:** `api/index.py` в репозитории — укороченный расчёт и **без** PostgreSQL для лидов. Продакшен-ориентир: **Flask + `DATABASE_URL` (Postgres)** в одном сервисе (см. [Dockerfile](Dockerfile)). Статика и API тогда с одного домена — лиды сохраняются в БД.

## Docker Compose (локально или VPS с Postgres)

Поднимает `web` + PostgreSQL с готовым `DATABASE_URL`:

```bash
docker compose up --build
```

Сайт: http://localhost:8000 — таблица лидов создаётся при старте приложения.

Пароли и имена базы в `docker-compose.yml` замените на свои перед публичным VPS.

## Способ A — Docker (Railway, Fly.io, свой VPS)

1. Залейте репозиторий на GitHub/GitLab.
2. В панели выберите деплой из Dockerfile (на **Railway**: New Project → Deploy from GitHub → выберите репозиторий; билд подхватит `Dockerfile`).
3. Добавьте PostgreSQL-плагин (или внешнюю БД) и пропишите **`DATABASE_URL`** в Variables.
4. Остальные секреты — в том же разделе Variables.

Локально проверка образа:

```bash
docker build -t compat-site .
docker run --rm -p 8000:8000 -e PORT=8000 compat-site
```

Откройте http://localhost:8000 .

## Способ B — Heroku-подобный билд без Docker (Render)

1. **New Web Service** → подключите репозиторий.
2. **Build command:** `pip install -r backend/requirements.txt`
3. **Start command:** `gunicorn --chdir backend --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
4. Подключите managed **PostgreSQL** и задайте `DATABASE_URL` из вкладки базы.
5. Environment: остальные ключи как в таблице выше.

На **Railway** без Docker можно указать те же Start/Build или просто использовать Dockerfile — проще Dockerfile.

## Способ C — только фронт на Vercel + API где угодно

Текущий `vercel.json` вызывает упрощённый `api/index.py` без полной базы лидов и без расширенной синастрии как в `backend/app.py`. Фронтенд покажет упрощённый режим с заглушками в детальных блоках. Для боевого сайта используйте **единый Flask** из способов выше или проксируйте домен полностью на этот сервис.

## После деплоя

- Заявки: `GET https://ваш-домен/api/leads` или страница `/leads`.
- Убедитесь, что HTTPS и что в `.env` на сервере нет локальных путей — только переменные хостинга.

### Яндекс.Вебмастер: `robots.txt` и sitemap

- В продакшене задайте **`PUBLIC_SITE_URL`** (например `https://example.ru` без `/` в конце) — тогда `/robots.txt` и `/sitemap.xml` отдают абсолютные URL для робота и для формы «файл Sitemap» в Вебмастере укажите `https://example.ru/sitemap.xml`.
- Если переменная не задана, база берётся из **`Host`/`X-Forwarded-*`** запроса (удобно для проверки, в бою лучше явный домен).
- В корне репозитория лежат статические [`robots.txt`](robots.txt) и [`sitemap.xml`](sitemap.xml) с плейсхолдером **`__CANONICAL_SITE_BASE__`**: замените его на тот же `https://ваш-домен.ru` **во всех вхождениях** (для хостинга только статикой без Flask). При работе через **Flask** эндпоинты `/robots.txt` и `/sitemap.xml` **перекрывают** эти файлы и формируют ответ сами.

# Калькулятор совместимости

## Что внутри

- Реальные астрологические расчеты через `pyswisseph` на backend API.
- Учет времени рождения, города и часового пояса (IANA) для более точных аспектов.
- UI-калькулятор с анимацией, диаграммой и блоками аналитики.
- Экспорт персонального PNG для публикации в соцсетях.
- Темная/светлая тема с сохранением выбора.
- Mini-CRM форма с хранением заявок в SQLite/PostgreSQL и авто-уведомлениями.

## Запуск

1. Перейдите в папку backend:

```bash
cd backend
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите сервер:

```bash
python app.py
```

4. Откройте в браузере:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## Переменные окружения

- `DATABASE_URL` - строка подключения БД.
  - По умолчанию: SQLite `backend/leads.db`
  - Пример PostgreSQL: `postgresql+psycopg2://user:pass@localhost:5432/compatibility`
- `CRM_WEBHOOK_URL` - URL для отправки лидов в CRM.
- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота.
- `TELEGRAM_CHAT_ID` - чат/канал для уведомлений.

## API

- `POST /api/compatibility`:

```json
{
  "birth1": "1998-04-15",
  "birthTime1": "09:20",
  "city1": "Moscow",
  "timezone1": "Europe/Moscow",
  "birth2": "1995-11-22",
  "birthTime2": "14:10",
  "city2": "Almaty",
  "timezone2": "Asia/Almaty",
  "relationshipType": "romance",
  "name1": "Анна",
  "name2": "Иван"
}
```

- `POST /api/leads`:

```json
{
  "name": "Анна",
  "contact": "+79990000000",
  "message": "Хочу понять перспективы на 12 месяцев",
  "context": {
    "score": 78,
    "relationType": "Романтика"
  }
}
```

- `GET /api/leads?limit=50` - получить последние заявки.
# AstrologiSite

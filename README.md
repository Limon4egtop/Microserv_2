# Micro Task Backend (Python/FastAPI)

- **api_gateway** — единая точка входа, проксирование `/v1/users/*` и `/v1/orders/*`, проверка JWT, rate-limit, CORS, X-Request-ID, трассировка.
- **service_users** — регистрация, вход, профиль, список пользователей (только admin).
- **service_orders** — CRUD жизненного цикла заказа, проверка прав на уровне сервиса, доменные события (заготовка).

## Быстрый старт (Docker Compose)

### Dev
```bash
docker compose -f docker-compose.dev.yml up --build
```

### Test
```bash
docker compose -f docker-compose.test.yml up --build
```

### Prod (пример, без секретов в репозитории)
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

По умолчанию API Gateway доступен на `http://localhost:8000`.

Swagger UI:
- Gateway: `http://localhost:8000/docs`
- Users service: `http://localhost:8001/docs`
- Orders service: `http://localhost:8002/docs`

Jaeger (трассы):
- `http://localhost:16686`

## Формат ответов

Успех:
```json
{ "success": true, "data": { ... } }
```

Ошибка:
```json
{ "success": false, "error": { "code": "SOME_CODE", "message": "..." } }
```

## Минимальные сценарии (чек-лист)

1) Регистрация: `POST /v1/users/register`
2) Вход: `POST /v1/users/login` -> JWT
3) Профиль: `GET /v1/users/me` (Bearer JWT)
4) Обновление профиля: `PUT /v1/users/me` (Bearer JWT)
5) Заказ: `POST /v1/orders` (Bearer JWT)
6) Список заказов: `GET /v1/orders` (Bearer JWT)
7) Обновление статуса: `PATCH /v1/orders/{id}/status` (Bearer JWT)
8) Отмена: `POST /v1/orders/{id}/cancel` (Bearer JWT)

## Тесты

Запуск юнит/интеграционных тестов локально (без Docker):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r service_users/requirements.txt -r service_orders/requirements.txt -r api_gateway/requirements.txt
pytest -q
```

## Спецификация OpenAPI

Готовая спецификация внешнего API лежит в `docs/openapi.yaml`.

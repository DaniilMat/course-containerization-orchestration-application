# Assistant

Персональный ассистент на FastAPI. Репозиторий ведётся в рамках лабораторных по Docker и Kubernetes.

Автор: Матвеев Д.А., ИСУ 466659

## Как запустить

```bash
docker build -t matveev-assistant:v1 .
docker build -t matveev-assistant:final -f Dockerfile.optimized .
docker run -d --name matveev-assistant -p 5489:5489 \
  -e APP_OWNER=matveev \
  -e APP_SECRET=<ваш_секретный_ключ> \
  matveev-assistant:final
```
	
## Переменные окружения

| Переменная | Для чего | Пример |
| --- | --- | --- |
| `APP_OWNER` | ваша фамилия, показывается на главной | `matveev` |
| `APP_SECRET` | секретный ключ для эндпоинта `/secret/...` | задаётся при запуске |
| `PORT` | порт приложения | `5489` |

## Как проверить

```bash
curl http://localhost:5489/health
docker ps --filter "name=matveev-assistant"   # статус (healthy)
```

## Хранение данных

Создаются: volume `matveev-pgdata` (данные PostgreSQL) и сеть `matveev-backend`.

```bash
docker volume create matveev-pgdata
docker network create matveev-backend

docker run -d --name matveev-postgres --network matveev-backend \
  -e POSTGRES_USER=<пользователь> -e POSTGRES_PASSWORD=<пароль> -e POSTGRES_DB=<база> \
  -v matveev-pgdata:/var/lib/postgresql/data postgres:15

docker run -d --name matveev-assistant --network matveev-backend -p 8059:8059 \
  -e PORT=8059 -e APP_OWNER=matveev -e APP_SECRET=<ключ> \
  -e DATABASE_URL="postgresql://<пользователь>:<пароль>@matveev-postgres:5432/<база>" \
  -v "$(pwd)/config":/app/config:ro matveev-assistant:v3
```

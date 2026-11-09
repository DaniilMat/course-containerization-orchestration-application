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

# 1. Базовый образ Python
FROM python:3.11-slim

# 2. Метаданные
LABEL maintainer="matveev@lab.local"
LABEL version="1.0"

# 3. Рабочая директория
WORKDIR /app

# 4. Порт приложения
ENV PORT=5489

# 5. Копируем зависимости
COPY requirements.txt .

# 6. Устанавливаем зависимости
RUN pip install -r requirements.txt

# 7. Копируем исходный код
COPY . .

# 8. Указываем порт приложения
EXPOSE ${PORT}

# 9. Запускаем FastAPI через Uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}

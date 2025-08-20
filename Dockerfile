# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и исходный код
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Указываем порт, который будет использоваться
EXPOSE 5000

# Команда для запуска приложения
CMD ["fastapi", "run", "main.py", "--port", "5000"]

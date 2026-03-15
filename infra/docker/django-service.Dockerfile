FROM python:3.11-slim

ARG SERVICE_DIR

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ${SERVICE_DIR}/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ${SERVICE_DIR} /app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:${PORT:-8000}"]


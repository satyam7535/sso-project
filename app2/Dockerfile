FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

COPY . .

EXPOSE 8002

CMD ["sh", "-c", "python manage.py migrate && gunicorn --bind 0.0.0.0:8002 app2.wsgi:application"]

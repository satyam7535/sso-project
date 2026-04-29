FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .
# Install gunicorn and psycopg2 for production/postgres
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

COPY . .

# Expose port 8000
EXPOSE 8000

# Run migrations and start Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn --bind 0.0.0.0:8000 auth_service.wsgi:application"]

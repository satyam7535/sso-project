@echo off
echo Starting Auth Service on port 8000...
start cmd /k "cd auth_service && ..\venv\Scripts\activate 2>nul || echo Virtual environment not found, using global python && python manage.py runserver 8000"

echo Starting App 1 on port 8001...
start cmd /k "cd app1 && ..\venv\Scripts\activate 2>nul || echo Virtual environment not found, using global python && python manage.py runserver 8001"

echo Starting App 2 on port 8002...
start cmd /k "cd app2 && ..\venv\Scripts\activate 2>nul || echo Virtual environment not found, using global python && python manage.py runserver 8002"

echo All servers are starting in separate windows!

# Inventory Management System (POS)

Система управления инвентаризацией и продажами с поддержкой долгов, кассиров и складских операций.

## Features

✅ **Управление товарами** — добавление, редактирование, архивирование товаров с генерацией штрих-кодов  
✅ **Продажи (POS)** — быстрые кассовые чеки с поддержкой наличных и в долг  
✅ **Долги** — управление платежами в рассрочку с графиком платежей  
✅ **Складские операции** — приход/расход товаров с документацией  
✅ **Управление кассирами** — добавление и контроль работников  
✅ **JWT Authentication** — безопасная аутентификация через токены  
✅ **REST API** — полный API с документацией Swagger  
✅ **Docker** — готово к деплою в Docker контейнерах  

## Tech Stack

- **Backend:** Django 4.2, Django REST Framework
- **Database:** PostgreSQL 15
- **Cache/Tasks:** Redis, Celery
- **Authentication:** JWT (SimpleJWT)
- **Documentation:** Swagger (drf-yasg)
- **Deployment:** Docker, Nginx, Gunicorn

## Quick Start (Development)

### 1. Требования

- Python 3.10+
- PostgreSQL 15
- Redis 7

### 2. Установка

```bash
git clone https://github.com/your-repo/Inventory.git
cd Inventory

# Virtual environment
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows

# Установить зависимости
pip install -r requirements.txt

# Миграции
python manage.py migrate

# Создать админа
python manage.py createsuperuser

# Запустить сервер
python manage.py runserver
Приложение доступно на http://localhost:8000
 3. Docker Compose (рекомендуется)
docker-compose up -d
docker-compose exec web python manage.py createsuperuser
Приложение: http://localhost:8000
 Swagger docs: http://localhost:8000/api/docs/
 Admin: http://localhost:8000/admin/
 API Documentation
Swagger: http://localhost:8000/api/docs/
 ReDoc: http://localhost:8000/api/redoc/
 Authentication
 Получить JWT Token
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Ответ:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
 Использовать Token
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/v1/products/
 API Endpoints
 Products
•
POST /api/v1/products/ — Создать товар (IsAdmin)
•
PATCH /api/v1/products/<id>/ — Обновить товар (IsAdmin)
•
DELETE /api/v1/products/<id>/ — Архивировать товар (IsAdmin)
•
GET /api/v1/products/barcode/<id>/ — Печать штрих-кода (Authenticated)
 Sales
•
POST /api/v1/sales/ — Создать продажу (IsCashier)
•
GET /api/v1/sales/<id>/ — Получить детали продажи (Authenticated)
•
DELETE /api/v1/sales/<id>/ — Отменить продажу (IsCashier)
 Transactions
•
POST /api/v1/transactions/search/ — Поиск транзакций (IsCashier)
•
POST /api/v1/debts/pay/<id>/ — Оплатить долг (IsCashier)
 Cashiers (Admin only)
•
POST /api/v1/cashiers/ — Создать кассира (IsAdmin)
•
GET /api/v1/cashiers/ — Список кассиров (IsAdmin)
•
PATCH /api/v1/cashiers/<id>/ — Обновить кассира (IsAdmin)
•
DELETE /api/v1/cashiers/<id>/ — Удалить кассира (IsAdmin)
 Stock
•
POST /api/v1/stocks/ — Создать складской документ (Authenticated)
 Auth
•
POST /api/token/ — Получить JWT токены
•
POST /api/token/refresh/ — Обновить access token
•
POST /api/v1/logout/ — Выход (Authenticated)
 Production Deployment
Смотри DEPLOYMENT.md для полной инструкции по деплою на Linux сервер.
 Quickstart с Docker Compose
cp .env.example .env
# Отредактируй .env с правильными значениями

docker-compose up -d
docker-compose exec web python manage.py createsuperuser
Настройка Nginx + SSL описана в DEPLOYMENT.md.
 Environment Variables
Смотри .env.example для полного списка. Основные:
SECRET_KEY=your-secret-key
DEBUG=False (production)
DATABASE_URL=postgres://user:pass@host/db
CELERY_BROKER_URL=redis://localhost:6379/0
ALLOWED_HOSTS=yourdomain.com
 Development
 Запустить тесты
python manage.py test
 Запустить Celery
celery -A inventory_project worker -l info
 Миграции БД
python manage.py makemigrations
python manage.py migrate
 Troubleshooting
 ModuleNotFoundError
pip install -r requirements.txt
 Database connection error
Убедись что PostgreSQL запущен:
docker-compose up postgres
 Redis connection error
docker-compose up redis
 License
MIT License
 Author
Your Team

---

### **Этап 11) Создаёшь .env.example в корне проекта**

Новый файл `C:\Users\hack_prince\Desktop\Inventory\.env.example`:
 Django
SECRET_KEY=your-super-secret-key-here-change-this DEBUG=False ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com
 Database (Postgres для production)
DATABASE_URL=postgres://user:password@db-host:5432/inventory_db
 Cache & Tasks (Redis)
CELERY_BROKER_URL=redis://redis-host:6379/0 CELERY_RESULT_BACKEND=redis://redis-host:6379/0
 CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://app.yourdomain.com
 JWT
JWT_ACCESS_MINUTES=60 JWT_REFRESH_DAYS=7
 Security (production)
SECURE_SSL_REDIRECT=True SECURE_HSTS_SECONDS=31536000
 Sentry (optional error tracking)
SENTRY_DSN=
 Gunicorn
GUNICORN_WORKERS=4
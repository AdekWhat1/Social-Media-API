# Social Media API

## Getting Started

### 1. Setup Environment

Create a `.env` file in the root directory:

```env
SECRET_KEY=your_secret_key_here
POSTGRES_DB=social_media_api
POSTGRES_USER=social_media_user
POSTGRES_PASSWORD=social_media_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

2. Launch Services
Build and start all containers in detached mode:

docker compose up --build -d

3. Create Admin User (Optional)
docker compose exec -it web python manage.py createsuperuser

4. Available Endpoints
Swagger UI: http://localhost:8000/api/doc/swagger/
ReDoc: http://localhost:8000/api/doc/redoc/
Admin Panel: http://localhost:8000/admin/

5. Stop the Application
docker compose down

# Timestamper Project

Time tracking application with separated frontend and backend architecture.

## Project Structure

```
timestamper-gitproject/
├── backend/          # Django REST API
├── frontend/         # Vue
├── docker-compose.yml
└── README.md
```

## Technology Stack

- **Backend**: Django with Django REST Framework
- **Frontend**: Vue
- **Database**: SQLite (development)
- **Cache**: Redis
- **Task Queue**: Celery
- **Containerization**: Docker & Docker Compose

## Quick Start with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/aaronm-th/timestamper-gitproject
   cd timestamper-gitproject
   ```

2. Start all services:
   ```bash
   docker-compose up --build
   ```

3. Access the application:
   - Frontend: http://localhost:5173
   - Django Admin: http://localhost:8000/admin



## Default Users

The following users are available for testing:

- **Admin User**
  - Email: admin@admin.com
  - Password: admin

- **Test User 1**
  - Email: ea@mail.de
  - Password: test

- **Test User 2**
  - Email: aa@mail.de
  - Password: aaron






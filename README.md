# Precision Agriculture Platform - Backend

A Django REST API backend for the Precision Agriculture Platform, configured with PostgreSQL database support.

## Features

- Django 5.0 framework
- PostgreSQL database integration
- Django REST Framework for API development
- CORS support for frontend integration
- Environment-based configuration using python-decouple

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/RifqiAfandi/Precision-Agriculture-Platform-BE.git
   cd Precision-Agriculture-Platform-BE
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**
   - Create a PostgreSQL database:
     ```sql
     CREATE DATABASE precision_agriculture;
     ```
   - Create a database user (optional, or use existing postgres user)

5. **Configure environment variables**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Update the `.env` file with your database credentials and other settings

6. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create a superuser** (optional, for admin access)
   ```bash
   python manage.py createsuperuser
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/`

## Project Structure

```
Precision-Agriculture-Platform-BE/
├── precision_agriculture/    # Main project settings
│   ├── settings.py          # Django settings with PostgreSQL config
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
├── manage.py                # Django management script
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment variables
└── README.md               # This file
```

## Environment Variables

The following environment variables can be configured in your `.env` file:

- `SECRET_KEY`: Django secret key for cryptographic signing
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DB_NAME`: PostgreSQL database name
- `DB_USER`: PostgreSQL database user
- `DB_PASSWORD`: PostgreSQL database password
- `DB_HOST`: PostgreSQL database host
- `DB_PORT`: PostgreSQL database port
- `CORS_ALLOW_ALL_ORIGINS`: Allow all CORS origins (True/False)
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins

## API Documentation

The API is built with Django REST Framework. Visit:
- Admin panel: `http://localhost:8000/admin/`
- API root: `http://localhost:8000/api/` (once configured)

## Development

To run tests:
```bash
python manage.py test
```

To collect static files:
```bash
python manage.py collectstatic
```

## License

This project is part of the Precision Agriculture Platform.

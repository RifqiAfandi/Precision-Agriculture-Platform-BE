# Precision Agriculture Platform - Backend# Precision Agriculture Platform - Backend



Backend API dengan autentikasi JWT dan sistem manajemen pengguna.Backend API untuk Precision Agriculture Platform dengan autentikasi JWT dan sistem manajemen pengguna lengkap.



## Features## 🚀 Features



- Django 5.0 REST Framework- ✅ Django 5.0 REST Framework

- JWT Authentication (djangorestframework-simplejwt)- ✅ JWT Authentication dengan djangorestframework-simplejwt

- Custom User Model (email-based)- ✅ Custom User Model (email-based authentication)

- User Registration & Login- ✅ User Registration & Login

- Profile Management- ✅ Profile Management

- Password Change- ✅ Password Change

- Token Blacklist untuk logout- ✅ Token Blacklist untuk logout

- PostgreSQL & SQLite support- ✅ PostgreSQL & SQLite support

- CORS enabled- ✅ CORS enabled untuk frontend integration

- Environment-based configuration- ✅ Environment-based configuration



## Prerequisites## 📋 Prerequisites



- Python 3.8+- Python 3.8 atau lebih tinggi

- PostgreSQL 12+ (opsional, SQLite untuk development)- PostgreSQL 12+ (opsional, bisa pakai SQLite untuk development)

- pip- pip (Python package manager)



## Installation## Installation



### 1. Setup Environment### 1. Setup Environment

```bash```bash

python -m venv venvpython -m venv venv

venv\Scripts\activate  # Windowsvenv\Scripts\activate  # Windows

source venv/bin/activate  # Linux/Macsource venv/bin/activate  # Linux/Mac

``````



### 2. Install Dependencies### 2. Install Dependencies

```bash```bash

pip install -r requirements.txtpip install -r requirements.txt

``````



### 3. Environment Configuration (Optional)### 3. Environment Configuration (Optional)



Create `.env` file:Create `.env` file:



**Development (SQLite):****Development (SQLite):**

```env```env

SECRET_KEY=your-secret-key-hereSECRET_KEY=your-secret-key-here

DEBUG=TrueDEBUG=True

USE_SQLITE=TrueUSE_SQLITE=True

CORS_ALLOW_ALL_ORIGINS=TrueCORS_ALLOW_ALL_ORIGINS=True

``````



**Production (PostgreSQL):****Production (PostgreSQL):**

```env```env

SECRET_KEY=your-secret-key-hereSECRET_KEY=your-secret-key-here

DEBUG=FalseDEBUG=False

USE_SQLITE=FalseUSE_SQLITE=False

DB_NAME=precision_agricultureDB_NAME=precision_agriculture

DB_USER=postgresDB_USER=postgres

DB_PASSWORD=your_passwordDB_PASSWORD=your_password

DB_HOST=localhostDB_HOST=localhost

DB_PORT=5432DB_PORT=5432

CORS_ALLOW_ALL_ORIGINS=FalseCORS_ALLOW_ALL_ORIGINS=False

CORS_ALLOWED_ORIGINS=https://yourdomain.comCORS_ALLOWED_ORIGINS=https://yourdomain.com

``````



### 4. Run Migrations & Seed### 4. Run Migrations & Seed

```bash```bash

python manage.py migratepython manage.py migrate

python manage.py seed_users  # Optional: create sample userspython manage.py seed_users  # Optional: create sample users

``````



### 5. Run Server### 5. Run Server

```bash```bash

python manage.py runserverpython manage.py runserver

``````



Server: `http://localhost:8000`Server: `http://localhost:8000`



## Project Structure## Project Structure



``````

Precision-Agriculture-Platform-BE/Precision-Agriculture-Platform-BE/

├── precision_agriculture/├── precision_agriculture/

│   ├── settings.py          # Django settings + JWT config│   ├── settings.py          # Django settings + JWT config

│   ├── urls.py              # Main URL routing│   ├── urls.py              # Main URL routing

│   ├── wsgi.py│   ├── wsgi.py

│   └── asgi.py│   └── asgi.py

├── users/├── users/

│   ├── migrations/│   ├── migrations/

│   ├── management/│   ├── management/

│   │   └── commands/│   │   └── commands/

│   │       └── seed_users.py    # Create sample users│   │       └── seed_users.py    # Create sample users

│   ├── models.py            # Custom User model│   ├── models.py            # Custom User model

│   ├── serializers.py       # API serializers│   ├── serializers.py       # API serializers

│   ├── views.py             # API views│   ├── views.py             # API views

│   ├── urls.py              # Auth endpoints│   ├── urls.py              # Auth endpoints

│   ├── admin.py│   ├── admin.py

│   └── tests.py│   └── tests.py

├── manage.py├── manage.py

├── requirements.txt├── requirements.txt

├── db.sqlite3               # SQLite DB (development)├── db.sqlite3               # SQLite DB (development)

└── README.md└── README.md

``````



## API Endpoints## API Endpoints



| Method | Endpoint | Auth || Method | Endpoint | Auth |

|--------|----------|------||--------|----------|------|

| POST | `/api/auth/register/` | No || POST | `/api/auth/register/` | No |

| POST | `/api/auth/login/` | No || POST | `/api/auth/login/` | No |

| POST | `/api/auth/logout/` | Yes || POST | `/api/auth/logout/` | Yes |

| GET | `/api/auth/profile/` | Yes || GET | `/api/auth/profile/` | Yes |

| PATCH | `/api/auth/profile/update/` | Yes || PATCH | `/api/auth/profile/update/` | Yes |

| POST | `/api/auth/change-password/` | Yes || POST | `/api/auth/change-password/` | Yes |

| POST | `/api/token/refresh/` | No || POST | `/api/token/refresh/` | No |



**Admin Panel:** `http://localhost:8000/admin/`**Admin Panel:** `http://localhost:8000/admin/`



## Quick Test## Quick Test



### Register### Register

```bash```bash

curl -X POST http://localhost:8000/api/auth/register/ \curl -X POST http://localhost:8000/api/auth/register/ \

  -H "Content-Type: application/json" \  -H "Content-Type: application/json" \

  -d '{"email":"test@example.com","name":"Test User","password":"test123","confirm_password":"test123"}'  -d '{"email":"test@example.com","name":"Test User","password":"test123","confirm_password":"test123"}'

``````



### Login### Login

```bash```bash

curl -X POST http://localhost:8000/api/auth/login/ \curl -X POST http://localhost:8000/api/auth/login/ \

  -H "Content-Type: application/json" \  -H "Content-Type: application/json" \

  -d '{"email":"test@example.com","password":"test123"}'  -d '{"email":"test@example.com","password":"test123"}'

``````



### Get Profile### Get Profile

```bash```bash

curl -X GET http://localhost:8000/api/auth/profile/ \curl -X GET http://localhost:8000/api/auth/profile/ \

  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

``````



## Frontend Integration## Frontend Integration



Frontend sudah terintegrasi di folder `../Precision-Agriculture-Platform-FE`Frontend sudah terintegrasi di folder `../Precision-Agriculture-Platform-FE`



**API Service:** `src/services/api.js`  **API Service:** `src/services/api.js`  

**Auth Context:** `src/contexts/AuthContext.jsx`**Auth Context:** `src/contexts/AuthContext.jsx`



### Frontend .env### Frontend .env

```env```env

VITE_API_URL=http://localhost:8000/apiVITE_API_URL=http://localhost:8000/api

``````



## Development Commands## 🛠️ Development



```bash### Run Tests

python manage.py test                # Run tests```bash

python manage.py makemigrations      # Create migrationspython manage.py test

python manage.py migrate             # Apply migrations```

python manage.py createsuperuser     # Create admin

python manage.py shell               # Django shell### Create New Migration

python manage.py collectstatic       # Collect static files```bash

```python manage.py makemigrations

python manage.py migrate

## Database Schema```



### User Model### Collect Static Files

| Field | Type |```bash

|-------|------|python manage.py collectstatic

| id | Integer (PK) |```

| email | Email (unique, username) |

| name | String |### Run Shell

| company | String (optional) |```bash

| password | String (hashed) |python manage.py shell

| is_active | Boolean |```

| is_staff | Boolean |

| is_superuser | Boolean |## 📊 Database Schema

| date_joined | DateTime |

| last_login | DateTime |### User Model

| Field | Type | Description |

## Sample Users (After Seed)|-------|------|-------------|

| id | Integer | Primary key (auto) |

| Email | Password | Role || email | EmailField | Unique email (username field) |

|-------|----------|------|| name | CharField | User's full name |

| admin@agriiweb.com | admin123 | Superuser || company | CharField | Company name (optional) |

| demo@agriiweb.com | demo123 | User || password | CharField | Hashed password |

| user1@agriiweb.com | password123 | User || is_active | Boolean | Account active status |

| farmer@test.com | farmer123 | User || is_staff | Boolean | Staff status |

| is_superuser | Boolean | Superuser status |

## Security Notes| date_joined | DateTime | Registration date |

| last_login | DateTime | Last login timestamp |

- Use HTTPS in production

- Generate new SECRET_KEY## 🔒 Security Notes

- Set `CORS_ALLOW_ALL_ORIGINS=False`

- Use PostgreSQL in production1. **HTTPS:** Gunakan HTTPS di production

- Don't commit `.env` file2. **Secret Key:** Generate secret key baru untuk production

- Access token: 1 hour3. **CORS:** Konfigurasi CORS dengan benar (jangan `ALLOW_ALL` di production)

- Refresh token: 7 days4. **Database:** Gunakan PostgreSQL di production

5. **Environment Variables:** Jangan commit file `.env`

## Troubleshooting6. **Token Storage:** Gunakan HttpOnly cookies untuk production



**PostgreSQL Error:** Set `USE_SQLITE=True`  ## 🐛 Troubleshooting

**CORS Error:** Add frontend URL to `CORS_ALLOWED_ORIGINS`  

**Token Expired:** Use refresh token endpoint### PostgreSQL Connection Error

Jika mendapat error koneksi PostgreSQL, gunakan SQLite untuk development:

## Dependencies```bash

set USE_SQLITE=True

- Django 5.0+```

- djangorestframework 3.14+

- djangorestframework-simplejwt 5.3+### Token Expired

- django-cors-headers 4.3+Token akan expired setelah:

- psycopg2-binary 2.9+- Access Token: 1 jam

- python-decouple 3.8+- Refresh Token: 7 hari



## AuthorGunakan refresh token untuk mendapatkan access token baru.



**Rifqi Afandi**  ### CORS Error

GitHub: [@RifqiAfandi](https://github.com/RifqiAfandi)Pastikan frontend URL sudah ditambahkan di `CORS_ALLOWED_ORIGINS` di settings.


## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | - |
| `DEBUG` | Debug mode | True |
| `ALLOWED_HOSTS` | Allowed hosts | localhost,127.0.0.1 |
| `USE_SQLITE` | Use SQLite instead of PostgreSQL | False |
| `DB_NAME` | PostgreSQL database name | precision_agriculture |
| `DB_USER` | PostgreSQL user | postgres |
| `DB_PASSWORD` | PostgreSQL password | postgres |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `CORS_ALLOW_ALL_ORIGINS` | Allow all CORS origins | True |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | localhost URLs |

## 📦 Dependencies

- Django 5.0+
- djangorestframework 3.14+
- djangorestframework-simplejwt 5.3+
- django-cors-headers 4.3+
- psycopg2-binary 2.9+ (untuk PostgreSQL)
- python-decouple 3.8+

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is part of the Precision Agriculture Platform.

## 👨‍💻 Author

**Rifqi Afandi**
- GitHub: [@RifqiAfandi](https://github.com/RifqiAfandi)

## 📞 Support

Jika ada pertanyaan atau issues, silakan buat issue di GitHub repository.

# Precision Agriculture Platform - Backend

Backend API untuk Precision Agriculture Platform dengan autentikasi JWT dan sistem manajemen pengguna lengkap.

## 🚀 Features

- ✅ Django 5.0 REST Framework
- ✅ JWT Authentication dengan djangorestframework-simplejwt
- ✅ Custom User Model (email-based authentication)
- ✅ User Registration & Login
- ✅ Profile Management
- ✅ Password Change
- ✅ Token Blacklist untuk logout
- ✅ PostgreSQL & SQLite support
- ✅ CORS enabled untuk frontend integration
- ✅ Environment-based configuration

## 📋 Prerequisites

- Python 3.8 atau lebih tinggi
- PostgreSQL 12+ (opsional, bisa pakai SQLite untuk development)
- pip (Python package manager)

## 🔧 Installation

### 1. Clone Repository
```bash
git clone https://github.com/RifqiAfandi/Precision-Agriculture-Platform-BE.git
cd Precision-Agriculture-Platform-BE
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Buat file `.env` di root project:

**Untuk Development (SQLite):**
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database - SQLite
USE_SQLITE=True

# CORS
CORS_ALLOW_ALL_ORIGINS=True
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

**Untuk Production (PostgreSQL):**
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com

# Database - PostgreSQL
USE_SQLITE=False
DB_NAME=precision_agriculture
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# CORS
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

### 5. Run Migrations
```bash
# Untuk SQLite (Development)
set USE_SQLITE=True      # Windows
export USE_SQLITE=True   # Linux/Mac

python manage.py migrate
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Server akan berjalan di: `http://localhost:8000`

## 📁 Project Structure

```
Precision-Agriculture-Platform-BE/
├── precision_agriculture/        # Main project settings
│   ├── __init__.py
│   ├── settings.py              # Django settings dengan JWT config
│   ├── urls.py                  # Main URL routing
│   ├── wsgi.py                  # WSGI configuration
│   └── asgi.py                  # ASGI configuration
├── users/                       # Users app
│   ├── migrations/              # Database migrations
│   ├── __init__.py
│   ├── admin.py                 # Admin configuration
│   ├── apps.py                  # App configuration
│   ├── models.py                # Custom User model
│   ├── serializers.py           # API serializers
│   ├── views.py                 # API views
│   ├── urls.py                  # Users URL routing
│   └── tests.py                 # Unit tests
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── db.sqlite3                   # SQLite database (development)
├── API_DOCUMENTATION.md         # Complete API documentation
├── frontend-integration-example.js  # Frontend integration guide
└── README.md                    # This file
```

## 🔐 API Endpoints

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register user baru | No |
| POST | `/api/auth/login/` | Login user | No |
| POST | `/api/auth/logout/` | Logout user | Yes |
| GET | `/api/auth/profile/` | Get user profile | Yes |
| PUT/PATCH | `/api/auth/profile/update/` | Update user profile | Yes |
| POST | `/api/auth/change-password/` | Change password | Yes |

### Admin Panel
- URL: `http://localhost:8000/admin/`
- Manage users, view blacklisted tokens, dll.

**📖 Lihat [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) untuk dokumentasi lengkap**

## 🎯 Quick Start Testing

### 1. Register User Baru
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test User",
    "company": "Test Company",
    "password": "testpass123",
    "confirm_password": "testpass123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 3. Get Profile (dengan token)
```bash
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔗 Frontend Integration

### Install API Service di Frontend

Salin file `frontend-integration-example.js` ke frontend project Anda di `src/services/api.js`

### Update .env di Frontend (Vite)
```env
VITE_API_URL=http://localhost:8000/api
```

### Contoh Penggunaan di React Component

```javascript
import apiService from '@/services/api';
import { toast } from 'sonner';

// Login
const handleLogin = async (email, password) => {
  try {
    const response = await apiService.login(email, password);
    onLogin(response.user);
    toast.success('Login berhasil!');
  } catch (error) {
    toast.error(error.data?.error || 'Login gagal');
  }
};

// Register
const handleRegister = async (formData) => {
  try {
    const response = await apiService.register(formData);
    onLogin(response.user);
    toast.success('Registrasi berhasil!');
  } catch (error) {
    toast.error('Registrasi gagal');
  }
};
```

## 🛠️ Development

### Run Tests
```bash
python manage.py test
```

### Create New Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### Collect Static Files
```bash
python manage.py collectstatic
```

### Run Shell
```bash
python manage.py shell
```

## 📊 Database Schema

### User Model
| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key (auto) |
| email | EmailField | Unique email (username field) |
| name | CharField | User's full name |
| company | CharField | Company name (optional) |
| password | CharField | Hashed password |
| is_active | Boolean | Account active status |
| is_staff | Boolean | Staff status |
| is_superuser | Boolean | Superuser status |
| date_joined | DateTime | Registration date |
| last_login | DateTime | Last login timestamp |

## 🔒 Security Notes

1. **HTTPS:** Gunakan HTTPS di production
2. **Secret Key:** Generate secret key baru untuk production
3. **CORS:** Konfigurasi CORS dengan benar (jangan `ALLOW_ALL` di production)
4. **Database:** Gunakan PostgreSQL di production
5. **Environment Variables:** Jangan commit file `.env`
6. **Token Storage:** Gunakan HttpOnly cookies untuk production

## 🐛 Troubleshooting

### PostgreSQL Connection Error
Jika mendapat error koneksi PostgreSQL, gunakan SQLite untuk development:
```bash
set USE_SQLITE=True
```

### Token Expired
Token akan expired setelah:
- Access Token: 1 jam
- Refresh Token: 7 hari

Gunakan refresh token untuk mendapatkan access token baru.

### CORS Error
Pastikan frontend URL sudah ditambahkan di `CORS_ALLOWED_ORIGINS` di settings.

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

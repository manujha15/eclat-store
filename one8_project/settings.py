"""
Django settings for one8_project — ÉCLAT beauty store.
Supports local MySQL and production MySQL via DATABASE_URL.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------- Security ----------

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-e1414+cs%vfe(-egu4qwbk!8_a8ni(wh3h89^piaamm@*8y_fr'
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    '127.0.0.1,localhost,10.209.39.73,.vercel.app'
).split(',')

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://*.vercel.app',
]

# ---------- Apps ----------

INSTALLED_APPS = [
    'django_tidb',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',   
    'store',
]
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'one8_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'one8_project.wsgi.app'


# ---------- Database ----------
# Local:  MySQL (below)
# Prod:   PostgreSQL via DATABASE_URL (auto-detected on Render)

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=False,
        )
    }
    DATABASES['default']['ENGINE'] = 'django_tidb'
    
    DATABASES['default']['OPTIONS'] = {
        'ssl': {
            'ca': str(BASE_DIR / 'certs' / 'isrgrootx1.pem'),
        },
        'charset': 'utf8mb4',
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'one8_db',
            'USER': 'root',
            'PASSWORD': os.environ.get('DB_PASSWORD', 'Eclat2026!'),
            'HOST': '127.0.0.1',
            'PORT': '3306',
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }


# ---------- Auth ----------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------- i18n ----------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ---------- Static & Media ----------

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise only serves static files — media still uses default storage.
# For production, see Cloudinary section in the guide.



# ---------- Email ----------

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'orders@eclat.local'


# ---------- Branding ----------

SITE_NAME = 'ÉCLAT'
SITE_TAGLINE = 'Beauty, distilled.'


# ---------- Stripe ----------

STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
# ---------- Cloudinary (Media Files) ----------

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}


HERO_VIDEO_URL = os.environ.get(
    'HERO_VIDEO_URL',
    'https://res.cloudinary.com/ke9ebxr3/video/upload/v1790872109/hero/hero.mp4'
)

# Vercel/production pe Cloudinary use karo
if not DEBUG:
    STORAGES = {
        'default': {
            'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

# ---------- Uploads ----------

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800


# ---------- Production Security ----------

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
"""Environment-based configuration; MySQL is the default database."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes'}

DEBUG = env_bool('DJANGO_DEBUG')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY in the environment or a local .env file.')
ALLOWED_HOSTS = [value.strip() for value in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if value.strip()]
CSRF_TRUSTED_ORIGINS = [value.strip() for value in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if value.strip()]
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'library']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'library_project.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'library.context_processors.library_access']}}]
WSGI_APPLICATION = 'library_project.wsgi.application'

if os.getenv('DB_ENGINE', 'mysql') == 'sqlite':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.getenv('SQLITE_PATH', str(BASE_DIR / 'db.sqlite3'))}}
else:
    mysql_options = {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'", 'isolation_level': 'read committed'}
    if os.getenv('MYSQL_SSL_CA'):
        mysql_options['ssl'] = {'ca': os.environ['MYSQL_SSL_CA']}
    DATABASES = {'default': {'ENGINE': 'django.db.backends.mysql', 'NAME': os.getenv('MYSQL_DATABASE', 'reading_room'), 'USER': os.getenv('MYSQL_USER', 'reading_room'), 'PASSWORD': os.getenv('MYSQL_PASSWORD', ''), 'HOST': os.getenv('MYSQL_HOST', '127.0.0.1'), 'PORT': os.getenv('MYSQL_PORT', '3306'), 'OPTIONS': mysql_options, 'CONN_MAX_AGE': 0 if DEBUG else 60, 'CONN_HEALTH_CHECKS': True, 'TEST': {'NAME': os.getenv('MYSQL_TEST_DATABASE', 'test_reading_room')}}}

AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Kolkata')
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '31536000' if not DEBUG else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = env_bool('DJANGO_HSTS_PRELOAD')
if env_bool('DJANGO_TRUST_PROXY'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'library@example.com')
LOAN_DAYS = int(os.getenv('LOAN_DAYS', '14'))
MAX_ACTIVE_LOANS = int(os.getenv('MAX_ACTIVE_LOANS', '5'))
RESERVATION_HOLD_DAYS = int(os.getenv('RESERVATION_HOLD_DAYS', '2'))

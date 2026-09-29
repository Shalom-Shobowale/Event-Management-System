from decimal import Decimal
from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


# ============================================================
# Environment
# ============================================================

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

# ---- Secret key ----
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Dev fallback — never used in production because the else branch
        # raises ImproperlyConfigured when DEBUG=False and no env var is set.
        SECRET_KEY = 'django-insecure-jb1%pgmwk146v$!6_89cz=cew*^+1engcv4c8x-4e$dhi%u$3c'
    else:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY environment variable must be set in production.'
        )

# ---- Allowed hosts ----
if DEBUG:
    ALLOWED_HOSTS = ['event-management-system-a9be.onrender.com','127.0.0.1', 'localhost', '0.0.0.0', '[::1]']
else:
    _hosts_raw = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
    ALLOWED_HOSTS = [
        h.strip() for h in _hosts_raw.split(',') if h.strip()
    ]
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'DJANGO_ALLOWED_HOSTS environment variable must be set in production '
            '(e.g. "eventflow.ng,www.eventflow.ng").'
        )


# ============================================================
# Applications
# ============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'anymail',
    # 'crispy_forms',
    # 'crispy_bootstrap5',

    # Local apps
    'core',
    'event',
    'guest',
    'ticket',
    'vendors',
    'bookings',
    'collaboration',
    'admin_panel',
    'payments',
    'reports',
]

if DEBUG:
    INSTALLED_APPS.append('debug_toolbar')


CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'


# ============================================================
# Middleware
# ============================================================

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

if DEBUG:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')


# ============================================================
# Security (production only — dev stays loose for local testing)
# ============================================================

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_REFERRER_POLICY = 'same-origin'


# ============================================================
# URLs & templates
# ============================================================

ROOT_URLCONF = 'eventflow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'admin_panel.context_processor.admin_sidebar_context',
            ],
        },
    },
]

if DEBUG:
    INTERNAL_IPS = ['127.0.0.1']

WSGI_APPLICATION = 'eventflow.wsgi.application'


# ============================================================
# Database
# ============================================================

DATABASES = {
    'default': dj_database_url.parse(
        os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}


# ============================================================
# Auth
# ============================================================

AUTH_USER_MODEL = 'core.Host'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'


# ============================================================
# i18n / tz
# ============================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ============================================================
# Static & media files
# ============================================================

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Cloudflare R2 for user uploads, WhiteNoise for static
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'access_key': os.environ.get('R2_ACCESS_KEY_ID'),
            'secret_key': os.environ.get('R2_SECRET_ACCESS_KEY'),
            'bucket_name': os.environ.get('R2_BUCKET_NAME'),
            'endpoint_url': os.environ.get('R2_ENDPOINT_URL'),
            'region_name': 'auto',
        },
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# Email
# ============================================================

EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'

ANYMAIL = {
    'RESEND_API_KEY': os.environ.get('RESEND_API_KEY'),
}

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'EventFlow <noreply@resend.dev>'
)

# Base URL — used to build absolute links in emails.
# Required in production; defaults to localhost in dev.
SITE_URL = os.environ.get('SITE_URL', '').rstrip('/')
if not SITE_URL:
    if DEBUG:
        SITE_URL = 'http://127.0.0.1:8000'
    else:
        raise ImproperlyConfigured(
            'SITE_URL environment variable must be set in production '
            '(e.g. "https://eventflow.ng"). Used to build absolute links in emails.'
        )


# ============================================================
# Payments — Paystack
# ============================================================

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY')

PLATFORM_COMMISSION_PERCENT = Decimal(
    os.environ.get('PLATFORM_COMMISSION_PERCENT', '5.00')
)
VENDOR_TRIAL_DAYS = int(os.environ.get('VENDOR_TRIAL_DAYS', '30'))


# ============================================================
# Notifications
# ============================================================

NOTIFICATION_RETENTION_DAYS = 90


# ============================================================
# Caching
# ============================================================

CACHES = {
    'default': {
        'BACKEND': os.environ.get(
            'CACHE_BACKEND',
            'django.core.cache.backends.locmem.LocMemCache'
        ),
        'LOCATION': os.environ.get('CACHE_LOCATION', 'eventflow-default'),
        'TIMEOUT': int(os.environ.get('CACHE_TIMEOUT', '300')),
    }
}


# ============================================================
# Pagination
# ============================================================

PAGE_SIZE = 12
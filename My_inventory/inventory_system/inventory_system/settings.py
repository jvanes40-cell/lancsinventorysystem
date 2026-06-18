"""
Django settings for inventory_system project.
Production configuration for Windows Mini PC (Local LAN deployment).
"""
from pathlib import Path
import os
from decouple import config, Csv

# ---------------------------------------------------------------------------
# BASE
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Loaded from .env — must be 50+ random characters
SECRET_KEY = config('SECRET_KEY')

# Always False in production
DEBUG = False

# Your mini PC's local IP + localhost
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# HTTP only — no HTTPS on local LAN
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost,http://127.0.0.1',
    cast=Csv()
)

# ---------------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gudang',
]

# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ---------------------------------------------------------------------------
# URLS & WSGI
# ---------------------------------------------------------------------------

ROOT_URLCONF = 'inventory_system.urls'
WSGI_APPLICATION = 'inventory_system.wsgi.application'

# ---------------------------------------------------------------------------
# TEMPLATES
# ---------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# DATABASE — SQLite (upgrade to PostgreSQL later when ready)
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# INTERNATIONALISATION
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Jakarta'
USE_I18N      = True
USE_TZ        = True

# ---------------------------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------------------------

STATIC_URL  = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ---------------------------------------------------------------------------
# DEFAULT PRIMARY KEY
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# AUTH REDIRECTS
# ---------------------------------------------------------------------------

LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL           = '/login/'

# ---------------------------------------------------------------------------
# CACHE — in-memory, sufficient for local LAN
# ---------------------------------------------------------------------------

CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'lancs-wms',
    }
}

# ---------------------------------------------------------------------------
# SESSIONS
# ---------------------------------------------------------------------------

SESSION_ENGINE     = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 28800   # 8 hours — one warehouse shift

# No HTTPS on LAN — these must stay False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE    = False

# ---------------------------------------------------------------------------
# SECURITY HARDENING
# ---------------------------------------------------------------------------

SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'

# Silence HTTPS warnings — intentional, this is a private HTTP-only LAN deployment.
# Re-enable all of these if you ever add SSL/HTTPS in the future.
SILENCED_SYSTEM_CHECKS = [
    'security.W004',   # HSTS — no HTTPS on LAN
    'security.W008',   # SSL redirect — HTTP only on LAN
    'security.W012',   # SESSION_COOKIE_SECURE — no HTTPS on LAN
    'security.W016',   # CSRF_COOKIE_SECURE — no HTTPS on LAN
]

# Future HTTPS upgrade checklist (uncomment when you add SSL):
#   SECURE_SSL_REDIRECT            = True
#   SECURE_HSTS_SECONDS            = 31536000
#   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
#   SESSION_COOKIE_SECURE          = True
#   CSRF_COOKIE_SECURE             = True
#   SILENCED_SYSTEM_CHECKS         = []

# ---------------------------------------------------------------------------
# LOGGING — errors written to logs/lancs_errors.log
# ---------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'lancs_errors.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
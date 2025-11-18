# settings.py

from pathlib import Path
import os


def env_list(key: str, default: str = "") -> list[str]:
    """Parse comma-separated env variables into a list."""
    value = os.getenv(key, default)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-h^wq%_fic=vs6(xm!0!@hx%fec^&dcbznz-j)oh=ra2z9t1ght"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "*") or ["*"]

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "core",
    "api",
    "django_celery_beat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.SecurityMiddleware",
    "core.middleware.RateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AuditMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.views.permission_context_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

# 添加靜態文件設置
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

AUTH_USER_MODEL = "core.User"

# 郵件設定
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.porkbun.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "service@traitty.com"
EMAIL_HOST_PASSWORD = "Traitty2025$"
DEFAULT_FROM_EMAIL = "Traitty特質評鑑 <service@traitty.com>"

EMAIL_USE_SSL = False
EMAIL_USE_TLS = True

SITE_URL = os.getenv("SITE_URL", "https://dev.traitty.com").rstrip("/")
# 登入設置
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# ==================== 點數系統設定 ====================

# 點數系統開關
POINT_SYSTEM_ENABLED = True  # 是否啟用點數系統
UNLIMITED_POINTS_MODE = False  # 無限制模式（暫時關閉付款驗證）

# 新用戶預設點數
DEFAULT_POINTS_FOR_INDIVIDUAL = 2  # 個人用戶預設點數
DEFAULT_POINTS_FOR_ENTERPRISE = 4  # 企業用戶預設點數

# 點數相關設定
POINT_EXPIRY_DAYS = 365  # 點數有效期（天）
MIN_PURCHASE_POINTS = 50  # 最小購買點數
MAX_PURCHASE_POINTS = 10000  # 最大購買點數

# 日誌檔案位置（容器環境預設放在 /tmp，避免權限問題）
POINTS_LOG_PATH = os.getenv("POINTS_LOG_PATH", "/tmp/points.log")

# 日誌設定
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": POINTS_LOG_PATH,
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "utils.point_service": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "core.point_views": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# CELERY_BROKER_URL = "redis://localhost:6379"
# CELERY_RESULT_BACKEND = "redis://localhost:6379"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Taipei"

# Celery Beat 排程器設定
try:
    from celery.schedules import crontab
except ImportError:
    crontab = None

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {}

# 註解掉設定檔中的排程，只使用資料庫排程 (DatabaseScheduler) 避免重複執行
# if crontab:
#     CELERY_BEAT_SCHEDULE.update({
#         'crawl-pending-test-results': {
#             'task': 'core.tasks.crawl_all_pending_results',
#             'schedule': crontab(minute='*/10'),  # 每10分鐘執行一次
#             'options': {'queue': 'crawler'},
#         },
#         'cleanup-old-crawl-logs': {
#             'task': 'core.tasks.cleanup_old_crawl_logs',
#             'schedule': crontab(minute=30, hour=2),  # 每天凌晨2:30清理舊紀錄
#             'options': {'queue': 'maintenance'},
#         },
#     })

# 快取設定 (使用本地記憶體快取)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "TIMEOUT": 60 * 60 * 24 * 30,  # 30天
        "OPTIONS": {
            "MAX_ENTRIES": 10000,
            "CULL_FREQUENCY": 3,
        },
    }
}

# REST Framework 設定
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/hour", "user": "1000/hour"},
}

# JWT 設定
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}

# CORS 設定
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 開發服務器
    "http://127.0.0.1:3000",
    "http://localhost:8080",  # Vue 開發服務器
    "http://127.0.0.1:8080",
]

CORS_ALLOW_CREDENTIALS = True

# 安全設定
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# API 速率限制
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "default"

# 檔案上傳設定
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# 爬蟲相關設定
CRAWLER_SETTINGS = {
    "TIMEOUT": 30,  # 頁面加載超時時間（秒）
    "RETRY_TIMES": 3,  # 重試次數
    "DELAY_BETWEEN_REQUESTS": 2,  # 請求間延遲（秒）
    "HEADLESS": True,  # 是否使用無頭模式
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "projectdb"),
        "USER": os.getenv("POSTGRES_USER", "projectuser"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "projectpass"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,  # keep-alive
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "core.validators.CustomPasswordValidator",
    },
    {
        "NAME": "core.validators.NoSequentialPasswordValidator",
    },
]

# 會話安全設定
SESSION_COOKIE_SECURE = False  # 在生產環境中應設為 True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1小時
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# CSRF 安全設定
CSRF_COOKIE_SECURE = False  # 在生產環境中應設為 True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_AGE = 3600

# 登入嘗試限制
LOGIN_ATTEMPTS_LIMIT = 5
LOGIN_ATTEMPTS_TIMEOUT = 300  # 5分鐘

# 密碼重設 Token 有效期
PASSWORD_RESET_TIMEOUT = 3600  # 1小時


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "zh-hant"  # 改為繁體中文
TIME_ZONE = "Asia/Taipei"  # 改為台灣時區
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

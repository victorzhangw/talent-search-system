from .settings import *

# 切回 SQLite（你的 db.sqlite3 在 manage.py 同層）
DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}

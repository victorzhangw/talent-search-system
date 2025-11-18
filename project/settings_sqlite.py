from .settings import *
# 只把 default DB 切到 SQLite 來源
DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",  # project/settings.py 通常有定義 BASE_DIR
}

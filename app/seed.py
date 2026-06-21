# -*- coding: utf-8 -*-
"""بوت‌استرپ حساب مدیر سیستم — فقط زمانی اجرا می‌شود که پایگاه‌داده کاملاً خالی باشد."""
import os

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import CommissionSettings, User

DEFAULT_ADMIN_PASSWORD = "Demo@12345"


def run():
    if User.query.first() is not None:
        return

    try:
        _seed()
    except IntegrityError:
        # یک کارگر (worker) دیگر هم‌زمان داده را وارد کرده است؛ بی‌خطر است.
        db.session.rollback()


def _seed():
    admin_password = os.environ.get("ADMIN_PASSWORD") or DEFAULT_ADMIN_PASSWORD
    admin = User(name="مدیر سیستم", email="admin@sazehmarket.app", role="admin", status="active")
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.add(CommissionSettings())
    db.session.commit()

    if not os.environ.get("ADMIN_PASSWORD"):
        print(f"[seed] رمز عبور پیش‌فرض مدیر سیستم (admin@sazehmarket.app): {admin_password}")

# -*- coding: utf-8 -*-
"""دادهٔ آغازین نمایشی — فقط زمانی اجرا می‌شود که پایگاه‌داده کاملاً خالی باشد."""
import os

from sqlalchemy.exc import IntegrityError

from app import data, services
from app.extensions import db
from app.models import CommissionSettings, InventoryItem, Sale, User

DEMO_PASSWORD = "Demo@12345"


def run():
    if User.query.first() is not None:
        return

    try:
        _seed()
    except IntegrityError:
        # یک کارگر (worker) دیگر هم‌زمان داده را وارد کرده است؛ بی‌خطر است.
        db.session.rollback()


def _seed():
    admin_password = os.environ.get("ADMIN_PASSWORD") or DEMO_PASSWORD
    admin = User(name="مدیر سیستم", email="admin@sazehmarket.app", role="admin", status="active")
    admin.set_password(admin_password)
    db.session.add(admin)

    buyer1 = User(
        name="شرکت ساختمانی پویا", email="buyer1@sazehmarket.app", role="buyer",
        company_name="شرکت ساختمانی پویا", city=data.CITIES[0], status="active",
    )
    buyer1.set_password(DEMO_PASSWORD)

    buyer2 = User(
        name="گروه توسعه‌گران البرز", email="buyer2@sazehmarket.app", role="buyer",
        company_name="گروه توسعه‌گران البرز", city=data.CITIES[2], status="active",
    )
    buyer2.set_password(DEMO_PASSWORD)

    supplier1 = User(
        name=data.SUPPLIER_NAMES[0]["fa"], email="supplier1@sazehmarket.app", role="supplier",
        company_name=data.SUPPLIER_NAMES[0]["fa"], city=data.CITIES[0], status="active",
    )
    supplier1.set_password(DEMO_PASSWORD)

    supplier2 = User(
        name=data.SUPPLIER_NAMES[1]["fa"], email="supplier2@sazehmarket.app", role="supplier",
        company_name=data.SUPPLIER_NAMES[1]["fa"], city=data.CITIES[3], status="pending",
    )
    supplier2.set_password(DEMO_PASSWORD)

    supplier3 = User(
        name=data.SUPPLIER_NAMES[2]["fa"], email="supplier3@sazehmarket.app", role="supplier",
        company_name=data.SUPPLIER_NAMES[2]["fa"], city=data.CITIES[1], status="suspended",
    )
    supplier3.set_password(DEMO_PASSWORD)

    db.session.add_all([buyer1, buyer2, supplier1, supplier2, supplier3])
    db.session.flush()

    services.create_project_from_rfq(
        buyer1,
        data.parse_rfq_text("برای ۱۲۰۰ متر زیربنا میلگرد ۱۴ و ۱۶ و تیرآهن نیاز دارم، تحویل در تهران"),
        "برای ۱۲۰۰ متر زیربنا میلگرد ۱۴ و ۱۶ و تیرآهن نیاز دارم، تحویل در تهران",
    )
    services.create_project_from_rfq(
        buyer2,
        data.parse_rfq_text("۸۰۰ متر سیمان و گچ برای نازک‌کاری در اصفهان"),
        "۸۰۰ متر سیمان و گچ برای نازک‌کاری در اصفهان",
    )

    db.session.add(InventoryItem(
        supplier_id=supplier1.id, material=data.MATERIALS["rebar"], spec="A3 - #14",
        stock=420, unit=data.tri("تن", "طن", "ton"), base_price=28_500_000,
    ))
    db.session.add(InventoryItem(
        supplier_id=supplier1.id, material=data.MATERIALS["beam"], spec="IPE 14",
        stock=140, unit=data.tri("تن", "طن", "ton"), base_price=31_000_000,
    ))
    db.session.add(InventoryItem(
        supplier_id=supplier1.id, material=data.MATERIALS["cement"], spec="تیپ ۲",
        stock=3000, unit=data.tri("کیسه", "كيس", "bag"), base_price=410_000,
    ))

    for month_index, amount in enumerate(data._gen_price_series(180, days=12, volatility=0.18, seed=21)):
        db.session.add(Sale(supplier_id=supplier1.id, month_index=month_index, amount=amount))

    db.session.add(CommissionSettings())
    db.session.commit()

    if not os.environ.get("ADMIN_PASSWORD"):
        print(f"[seed] رمز عبور پیش‌فرض مدیر سیستم (admin@sazehmarket.app): {admin_password}")

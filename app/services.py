# -*- coding: utf-8 -*-
"""منطق تجاری پلتفرم — لایهٔ واسط بین مدل‌های پایگاه‌داده و API.

این ماژول تمام عملیات خواندن/نوشتن واقعی روی پروژه‌ها، استعلام‌ها،
پیشنهادها، موجودی و آمار مدیریتی را پیاده‌سازی می‌کند و جای توابع
حذف‌شدهٔ نسخهٔ قبلیِ مبتنی بر حافظه (app/data.py) را می‌گیرد.
"""
import random
import time

from app import data
from app.extensions import db
from app.models import CommissionSettings, InventoryItem, Project, Quote, RFQ, Sale, User

UNIT_PRICE_TOMAN = {
    "rebar": 28_500_000,
    "beam": 31_000_000,
    "cement": 410_000,
    "sheet": 33_000_000,
    "profile": 29_500_000,
    "gypsum": 165_000,
}
DEFAULT_UNIT_PRICE = 20_000_000


def estimate_bom_price(bom):
    total = 0.0
    for item in bom or []:
        price = UNIT_PRICE_TOMAN.get(item.get("material_id"), DEFAULT_UNIT_PRICE)
        total += price * float(item.get("qty") or 0)
    return max(int(total), 5_000_000)


# ---------------------------------------------------------------------------
# پنل خریدار — پروژه‌ها و استعلام‌ها
# ---------------------------------------------------------------------------

def create_project_from_rfq(buyer, parsed, raw_text):
    city = parsed.get("city")
    bom = parsed.get("bom") or []

    project_no = Project.query.filter_by(buyer_id=buyer.id).count() + 1
    name = data.tri(
        f"پروژه شماره {project_no}", f"المشروع رقم {project_no}", f"Project #{project_no}"
    )
    project = Project(buyer_id=buyer.id, name=name, city=city, bom=bom, raw_request=raw_text)
    db.session.add(project)
    db.session.flush()

    rfq = RFQ(
        project_id=project.id,
        title=data.tri("استعلام اولیه مصالح", "طلب عرض أسعار أولي", "Initial Materials RFQ"),
        status="open",
        deadline_ts=time.time() + random.randint(3600, 3 * 24 * 3600),
    )
    db.session.add(rfq)
    db.session.flush()

    base_price = estimate_bom_price(bom)
    for quote_data in data.make_demo_quotes(random.randint(3, 5), base_price):
        db.session.add(Quote(rfq_id=rfq.id, **quote_data))

    db.session.commit()
    return project.to_dict()


def get_buyer_projects(buyer):
    projects = Project.query.filter_by(buyer_id=buyer.id).order_by(Project.id.desc()).all()
    return [p.to_dict() for p in projects]


def get_buyer_project_detail(buyer, pid):
    project = Project.query.filter_by(id=pid, buyer_id=buyer.id).first()
    return project.to_dict() if project else None


def select_quote(buyer, pid, rid, quote_id):
    project = Project.query.filter_by(id=pid, buyer_id=buyer.id).first()
    if not project:
        return None
    rfq = next((r for r in project.rfqs if r.id == rid), None)
    if not rfq:
        return None
    for q in rfq.quotes:
        q.selected = q.id == quote_id
    rfq.status = "closed"
    project.progress = min(100, project.progress + 8)
    db.session.commit()
    return rfq.to_dict()


# ---------------------------------------------------------------------------
# پنل فروشنده — فید استعلام‌ها، پیشنهاد قیمت، موجودی و فروش
# ---------------------------------------------------------------------------

def _feed_item(rfq):
    project = rfq.project
    primary = project.bom[0] if project.bom else {}
    return {
        "id": rfq.id,
        "project": project.name,
        "city": project.city,
        "material": primary.get("material"),
        "qty": primary.get("qty"),
        "unit": primary.get("unit"),
        "quote_count": len(rfq.quotes),
        "deadline_ts": rfq.deadline_ts,
    }


def supplier_feed(city=None):
    rfqs = (
        RFQ.query.join(Project)
        .filter(RFQ.status == "open")
        .order_by(RFQ.id.desc())
        .all()
    )
    items = [_feed_item(r) for r in rfqs]
    if city:
        items = [
            i for i in items
            if i["city"] and city in (i["city"].get("fa"), i["city"].get("en"))
        ]
    return items


def submit_supplier_quote(supplier, rfq_id, price, delivery_days):
    rfq = RFQ.query.get(rfq_id)
    if not rfq or rfq.status != "open":
        return None, "استعلام یافت نشد یا بسته شده است"
    existing = Quote.query.filter_by(rfq_id=rfq_id, supplier_id=supplier.id).first()
    if existing:
        return None, "شما قبلاً برای این استعلام پیشنهاد ثبت کرده‌اید"
    try:
        price_val = float(price)
    except (TypeError, ValueError):
        return None, "قیمت پیشنهادی نامعتبر است"
    quote = Quote(
        rfq_id=rfq_id,
        supplier_id=supplier.id,
        price=price_val,
        delivery_days=int(delivery_days) if delivery_days else 5,
        payment_terms=data.tri("نقدی", "نقدًا", "Cash"),
        rating=4.8,
    )
    db.session.add(quote)
    db.session.commit()
    return quote.to_dict(), None


def supplier_inventory(supplier):
    items = InventoryItem.query.filter_by(supplier_id=supplier.id).all()
    return [i.to_dict() for i in items]


def supplier_sales(supplier):
    sales = Sale.query.filter_by(supplier_id=supplier.id).order_by(Sale.month_index).all()
    return {"series": [s.amount for s in sales]}


# ---------------------------------------------------------------------------
# پنل مدیر سیستم
# ---------------------------------------------------------------------------

def admin_stats():
    users = User.query.filter(User.role != "admin").order_by(User.id).all()
    total_suppliers = sum(1 for u in users if u.role == "supplier")

    month_count = 12
    revenue_series = [0] * month_count
    for sale in Sale.query.all():
        if 0 <= sale.month_index < month_count:
            revenue_series[sale.month_index] += sale.amount

    monthly_volume_toman = revenue_series[-1] * 1_000_000 if revenue_series else 0
    settings = get_commission_settings()
    monthly_commission_toman = round(monthly_volume_toman * settings["fee_percent"] / 100)

    return {
        "total_users": len(users),
        "total_suppliers": total_suppliers,
        "monthly_volume_toman": monthly_volume_toman,
        "monthly_commission_toman": monthly_commission_toman,
        "revenue_series": revenue_series,
        "users": [u.to_admin_dict() for u in users],
        "categories": data.CATEGORIES,
    }


def set_user_status(uid, status):
    if status not in ("active", "pending", "suspended"):
        return None
    user = User.query.get(uid)
    if not user or user.role == "admin":
        return None
    user.status = status
    db.session.commit()
    return user.to_admin_dict()


def get_commission_settings():
    settings = CommissionSettings.query.first()
    if not settings:
        settings = CommissionSettings()
        db.session.add(settings)
        db.session.commit()
    return settings.to_dict()


def update_commission_settings(body):
    settings = CommissionSettings.query.first()
    if not settings:
        settings = CommissionSettings()
        db.session.add(settings)
    if "tier1_monthly" in body:
        settings.tier1_monthly = int(body["tier1_monthly"])
    if "tier2_monthly" in body:
        settings.tier2_monthly = int(body["tier2_monthly"])
    if "tier3_monthly" in body:
        settings.tier3_monthly = int(body["tier3_monthly"])
    if "fee_percent" in body:
        settings.fee_percent = float(body["fee_percent"])
    db.session.commit()
    return settings.to_dict()

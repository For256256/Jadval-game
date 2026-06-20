# -*- coding: utf-8 -*-
"""مدل‌های پایگاه‌داده سازه‌مارکت (SQLAlchemy) — لایهٔ ماندگاری واقعی پلتفرم."""
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # buyer | supplier | admin
    company_name = db.Column(db.String(180))
    city = db.Column(db.JSON)  # {fa, ar, en} یا None
    status = db.Column(db.String(20), nullable=False, default="active")  # active | pending | suspended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship("Project", back_populates="buyer", foreign_keys="Project.buyer_id")
    quotes = db.relationship("Quote", back_populates="supplier", foreign_keys="Quote.supplier_id")
    inventory_items = db.relationship("InventoryItem", back_populates="supplier", cascade="all, delete-orphan")
    sales = db.relationship("Sale", back_populates="supplier", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def display_name(self):
        return self.company_name or self.name

    def to_admin_dict(self):
        return {
            "id": self.id,
            "name": self.display_name,
            "role": self.role,
            "city": self.city,
            "status": self.status,
        }


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.JSON, nullable=False)  # {fa, ar, en}
    city = db.Column(db.JSON)
    bom = db.Column(db.JSON, nullable=False, default=list)
    progress = db.Column(db.Integer, default=4)
    raw_request = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", back_populates="projects", foreign_keys=[buyer_id])
    rfqs = db.relationship(
        "RFQ", back_populates="project", cascade="all, delete-orphan", order_by="RFQ.id"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "progress": self.progress,
            "bom": self.bom,
            "rfqs": [r.to_dict() for r in self.rfqs],
        }


class RFQ(db.Model):
    __tablename__ = "rfqs"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.JSON, nullable=False)  # {fa, ar, en}
    status = db.Column(db.String(20), default="open")  # open | closed
    deadline_ts = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("Project", back_populates="rfqs")
    quotes = db.relationship(
        "Quote", back_populates="rfq", cascade="all, delete-orphan", order_by="Quote.price"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "deadline_ts": self.deadline_ts,
            "quote_count": len(self.quotes),
            "quotes": [q.to_dict() for q in self.quotes],
        }


class Quote(db.Model):
    __tablename__ = "quotes"

    id = db.Column(db.Integer, primary_key=True)
    rfq_id = db.Column(db.Integer, db.ForeignKey("rfqs.id"), nullable=False)
    # برای پیشنهادهای واقعی یک تأمین‌کننده ثبت‌شده؛ خالی برای پیشنهادهای نمایشیِ رقبا
    supplier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    supplier_name = db.Column(db.JSON)  # عکس فوری نام، برای پیشنهادهای نمایشی بدون حساب واقعی
    price = db.Column(db.Float, nullable=False)
    payment_terms = db.Column(db.JSON)
    delivery_days = db.Column(db.Integer, default=5)
    rating = db.Column(db.Float, default=4.5)
    selected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rfq = db.relationship("RFQ", back_populates="quotes")
    supplier = db.relationship("User", back_populates="quotes", foreign_keys=[supplier_id])

    def to_dict(self):
        supplier_label = self.supplier.display_name if self.supplier else None
        return {
            "id": self.id,
            "supplier": supplier_label or self.supplier_name,
            "price": self.price,
            "payment_terms": self.payment_terms,
            "delivery_days": self.delivery_days,
            "rating": self.rating,
            "selected": self.selected,
        }


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    material = db.Column(db.JSON, nullable=False)
    spec = db.Column(db.String(160))
    stock = db.Column(db.Integer, default=0)
    unit = db.Column(db.JSON)
    base_price = db.Column(db.Integer, default=0)

    supplier = db.relationship("User", back_populates="inventory_items")

    def to_dict(self):
        return {
            "material": self.material,
            "spec": self.spec,
            "stock": self.stock,
            "unit": self.unit,
            "base_price": self.base_price,
        }


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month_index = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)

    supplier = db.relationship("User", back_populates="sales")


class CommissionSettings(db.Model):
    __tablename__ = "commission_settings"

    id = db.Column(db.Integer, primary_key=True)
    tier1_monthly = db.Column(db.Integer, default=1_000_000)
    tier2_monthly = db.Column(db.Integer, default=3_000_000)
    tier3_monthly = db.Column(db.Integer, default=5_000_000)
    fee_percent = db.Column(db.Float, default=3.0)

    def to_dict(self):
        return {
            "tier1_monthly": self.tier1_monthly,
            "tier2_monthly": self.tier2_monthly,
            "tier3_monthly": self.tier3_monthly,
            "fee_percent": self.fee_percent,
        }

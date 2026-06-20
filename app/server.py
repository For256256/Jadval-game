# -*- coding: utf-8 -*-
"""
بک‌اند Flask پلتفرم سازه‌مارکت (SazehMarket).
"""
import os
import secrets as pysecrets
from flask import Flask, jsonify, request, render_template

from app import data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = os.environ.get("SECRET_KEY", pysecrets.token_hex(32))
app.json.ensure_ascii = False


# ---------------------------------------------------------------------------
# صفحات
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", page="home")


@app.route("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html", page="dashboard",
        role_initial="خ", role_label_key="common.role_buyer", role_label_fallback="خریدار / پیمانکار",
        page_title_key="dashboard.title", page_title_fallback="پنل خریدار",
    )


@app.route("/supplier")
def supplier():
    return render_template(
        "supplier.html", page="supplier",
        role_initial="ف", role_label_key="common.role_supplier", role_label_fallback="تأمین‌کننده",
        page_title_key="supplier.title", page_title_fallback="پنل فروشنده",
    )


@app.route("/admin")
def admin():
    return render_template(
        "admin.html", page="admin",
        role_initial="A", role_label_key="common.role_admin", role_label_fallback="مدیر سیستم",
        page_title_key="admin.title", page_title_fallback="مدیریت سیستم",
    )


# ---------------------------------------------------------------------------
# API عمومی
# ---------------------------------------------------------------------------

@app.route("/api/categories")
def api_categories():
    return jsonify(data.CATEGORIES)


@app.route("/api/cities")
def api_cities():
    return jsonify(data.CITIES)


@app.route("/api/price-history")
def api_price_history():
    material = request.args.get("material", "rebar")
    if material not in ("rebar", "beam"):
        material = "rebar"
    return jsonify(data.price_history(material))


@app.route("/api/rfq/parse", methods=["POST"])
def api_rfq_parse():
    body = request.get_json(force=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "متن درخواست خالی است"}), 400
    parsed = data.parse_rfq_text(text)
    return jsonify(parsed)


@app.route("/api/rfq", methods=["POST"])
def api_rfq_create():
    body = request.get_json(force=True) or {}
    text = (body.get("text") or "").strip()
    bom = body.get("bom")
    if not text and not bom:
        return jsonify({"error": "اطلاعات درخواست ناقص است"}), 400
    parsed = {"bom": bom, "city": body.get("city")} if bom else data.parse_rfq_text(text)
    project = data.add_project_from_rfq(parsed, text)
    return jsonify(project), 201


# ---------------------------------------------------------------------------
# API پنل خریدار
# ---------------------------------------------------------------------------

@app.route("/api/projects")
def api_projects():
    return jsonify(data.all_projects())


@app.route("/api/projects/<int:pid>")
def api_project_detail(pid):
    project = data.find_project(pid)
    if not project:
        return jsonify({"error": "پروژه یافت نشد"}), 404
    return jsonify(project)


@app.route("/api/projects/<int:pid>/rfqs/<int:rid>/select", methods=["POST"])
def api_select_quote(pid, rid):
    body = request.get_json(force=True) or {}
    quote_id = body.get("quote_id")
    project, rfq = data.find_rfq(pid, rid)
    if not rfq:
        return jsonify({"error": "استعلام یافت نشد"}), 404
    for q in rfq["quotes"]:
        q["selected"] = (q["id"] == quote_id)
    rfq["status"] = "closed"
    project["progress"] = min(100, project["progress"] + 8)
    return jsonify(rfq)


# ---------------------------------------------------------------------------
# API پنل فروشنده
# ---------------------------------------------------------------------------

@app.route("/api/supplier/feed")
def api_supplier_feed():
    city = request.args.get("city")
    feed = data.supplier_feed()
    if city:
        feed = [f for f in feed if f["city"]["fa"] == city or f["city"]["en"] == city]
    return jsonify(feed)


@app.route("/api/supplier/quote", methods=["POST"])
def api_supplier_quote():
    body = request.get_json(force=True) or {}
    rfq_id = body.get("rfq_id")
    price = body.get("price")
    delivery_days = body.get("delivery_days", 5)
    for project in data.all_projects():
        for rfq in project["rfqs"]:
            if rfq["id"] == rfq_id:
                new_quote = {
                    "id": data.next_id(),
                    "supplier": data.tri("شرکت شما", "شركتك", "Your Company"),
                    "price": int(price) if price else 0,
                    "delivery_days": int(delivery_days),
                    "payment_terms": data.tri("نقدی", "نقدًا", "Cash"),
                    "rating": 4.8,
                    "selected": False,
                }
                rfq["quotes"].append(new_quote)
                rfq["quotes"].sort(key=lambda q: q["price"])
                return jsonify(new_quote), 201
    return jsonify({"error": "استعلام یافت نشد"}), 404


# ---------------------------------------------------------------------------
# API پنل مدیر سیستم
# ---------------------------------------------------------------------------

@app.route("/api/supplier/inventory")
def api_supplier_inventory():
    return jsonify(data.SUPPLIER_INVENTORY)


@app.route("/api/supplier/sales")
def api_supplier_sales():
    return jsonify(data.supplier_sales())


@app.route("/api/admin/stats")
def api_admin_stats():
    return jsonify(data.admin_stats())


@app.route("/api/admin/users/<int:uid>/status", methods=["POST"])
def api_admin_user_status(uid):
    body = request.get_json(force=True) or {}
    status = body.get("status")
    user = data.set_user_status(uid, status)
    if not user:
        return jsonify({"error": "کاربر یافت نشد"}), 404
    return jsonify(user)


@app.route("/api/admin/commission", methods=["GET", "POST"])
def api_admin_commission():
    if request.method == "POST":
        body = request.get_json(force=True) or {}
        return jsonify(data.update_commission_settings(body))
    return jsonify(data.get_commission_settings())


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

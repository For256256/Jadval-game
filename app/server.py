# -*- coding: utf-8 -*-
"""
بک‌اند Flask پلتفرم سازه‌مارکت (SazehMarket).
"""
import os
import secrets as pysecrets

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

from app import data, seed, services
from app.auth import get_current_user, role_required_api, role_required_page
from app.extensions import db
from app.models import User

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)
DEFAULT_DB_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "sazehmarket.db")

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = os.environ.get("SECRET_KEY", pysecrets.token_hex(32))
app.json.ensure_ascii = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", DEFAULT_DB_URI)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    seed.run()


@app.context_processor
def inject_current_user():
    return {"current_user": get_current_user(), "role_home": _role_home}


def _role_home(role):
    return {
        "buyer": url_for("dashboard"),
        "supplier": url_for("supplier"),
        "admin": url_for("admin"),
    }.get(role, url_for("index"))


# ---------------------------------------------------------------------------
# احراز هویت
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(_role_home(get_current_user().role))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return render_template("login.html", page="login", error="ایمیل یا رمز عبور اشتباه است", email=email), 401
        if user.status == "suspended":
            return render_template(
                "login.html", page="login",
                error="حساب شما مسدود شده است؛ با مدیر سیستم تماس بگیرید", email=email,
            ), 403

        session.clear()
        session["user_id"] = user.id
        g.pop("_user", None)
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(_role_home(user.role))

    return render_template("login.html", page="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user():
        return redirect(_role_home(get_current_user().role))

    if request.method == "POST":
        role = request.form.get("role") if request.form.get("role") in ("buyer", "supplier") else "buyer"
        name = (request.form.get("name") or "").strip()
        company_name = (request.form.get("company_name") or "").strip() or None
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        city_fa = request.form.get("city")
        form_state = dict(role=role, name=name, company_name=company_name, email=email, city_fa=city_fa, cities=data.CITIES)

        if not name or not email or len(password) < 6:
            return render_template(
                "register.html", error="لطفاً همهٔ فیلدها را به‌درستی تکمیل کنید (رمز عبور حداقل ۶ کاراکتر)",
                **form_state,
            ), 400
        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="این ایمیل قبلاً ثبت شده است", **form_state), 409

        user = User(
            name=name, email=email, role=role, company_name=company_name,
            city=data.find_city_by_fa(city_fa), status="active" if role == "buyer" else "pending",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session.clear()
        session["user_id"] = user.id
        g.pop("_user", None)
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(_role_home(user.role))

    role = request.args.get("role") if request.args.get("role") in ("buyer", "supplier") else "buyer"
    return render_template("register.html", role=role, cities=data.CITIES)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# صفحات
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", page="home")


@app.route("/dashboard")
@role_required_page("buyer")
def dashboard():
    user = get_current_user()
    return render_template(
        "dashboard.html", page="dashboard",
        role_initial=(user.display_name or "?")[:1], role_label_key="common.role_buyer", role_label_fallback="خریدار / پیمانکار",
        page_title_key="dashboard.title", page_title_fallback="پنل خریدار",
    )


@app.route("/supplier")
@role_required_page("supplier")
def supplier():
    user = get_current_user()
    return render_template(
        "supplier.html", page="supplier",
        role_initial=(user.display_name or "?")[:1], role_label_key="common.role_supplier", role_label_fallback="تأمین‌کننده",
        page_title_key="supplier.title", page_title_fallback="پنل فروشنده",
    )


@app.route("/admin")
@role_required_page("admin")
def admin():
    user = get_current_user()
    return render_template(
        "admin.html", page="admin",
        role_initial=(user.display_name or "?")[:1], role_label_key="common.role_admin", role_label_fallback="مدیر سیستم",
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
@role_required_api("buyer")
def api_rfq_create():
    body = request.get_json(force=True) or {}
    text = (body.get("text") or "").strip()
    bom = body.get("bom")
    if not text and not bom:
        return jsonify({"error": "اطلاعات درخواست ناقص است"}), 400
    parsed = {"bom": bom, "city": body.get("city")} if bom else data.parse_rfq_text(text)
    project = services.create_project_from_rfq(get_current_user(), parsed, text)
    return jsonify(project), 201


# ---------------------------------------------------------------------------
# API پنل خریدار
# ---------------------------------------------------------------------------

@app.route("/api/projects")
@role_required_api("buyer")
def api_projects():
    return jsonify(services.get_buyer_projects(get_current_user()))


@app.route("/api/projects/<int:pid>")
@role_required_api("buyer")
def api_project_detail(pid):
    project = services.get_buyer_project_detail(get_current_user(), pid)
    if not project:
        return jsonify({"error": "پروژه یافت نشد"}), 404
    return jsonify(project)


@app.route("/api/projects/<int:pid>/rfqs/<int:rid>/select", methods=["POST"])
@role_required_api("buyer")
def api_select_quote(pid, rid):
    body = request.get_json(force=True) or {}
    quote_id = body.get("quote_id")
    rfq = services.select_quote(get_current_user(), pid, rid, quote_id)
    if not rfq:
        return jsonify({"error": "استعلام یافت نشد"}), 404
    return jsonify(rfq)


# ---------------------------------------------------------------------------
# API پنل فروشنده
# ---------------------------------------------------------------------------

@app.route("/api/supplier/feed")
@role_required_api("supplier")
def api_supplier_feed():
    city = request.args.get("city")
    return jsonify(services.supplier_feed(city))


@app.route("/api/supplier/quote", methods=["POST"])
@role_required_api("supplier")
def api_supplier_quote():
    user = get_current_user()
    if user.status != "active":
        msg = "حساب شما هنوز توسط مدیر سیستم تأیید نشده است" if user.status == "pending" else "حساب شما مسدود شده است"
        return jsonify({"error": msg}), 403
    body = request.get_json(force=True) or {}
    quote, error = services.submit_supplier_quote(
        user, body.get("rfq_id"), body.get("price"), body.get("delivery_days", 5)
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify(quote), 201


@app.route("/api/supplier/inventory")
@role_required_api("supplier")
def api_supplier_inventory():
    return jsonify(services.supplier_inventory(get_current_user()))


@app.route("/api/supplier/sales")
@role_required_api("supplier")
def api_supplier_sales():
    return jsonify(services.supplier_sales(get_current_user()))


# ---------------------------------------------------------------------------
# API پنل مدیر سیستم
# ---------------------------------------------------------------------------

@app.route("/api/admin/stats")
@role_required_api("admin")
def api_admin_stats():
    return jsonify(services.admin_stats())


@app.route("/api/admin/users/<int:uid>/status", methods=["POST"])
@role_required_api("admin")
def api_admin_user_status(uid):
    body = request.get_json(force=True) or {}
    user = services.set_user_status(uid, body.get("status"))
    if not user:
        return jsonify({"error": "کاربر یافت نشد"}), 404
    return jsonify(user)


@app.route("/api/admin/commission", methods=["GET", "POST"])
@role_required_api("admin")
def api_admin_commission():
    if request.method == "POST":
        body = request.get_json(force=True) or {}
        return jsonify(services.update_commission_settings(body))
    return jsonify(services.get_commission_settings())


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

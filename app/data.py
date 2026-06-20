# -*- coding: utf-8 -*-
"""
داده‌های نمایشی (Mock Data) سازه‌مارکت.
همه‌چیز در حافظه نگه‌داری می‌شود؛ هدف این ماژول شبیه‌سازی رفتار واقعی پلتفرم
برای دموی فرانت‌اند/بک‌اند است، نه ذخیره‌سازی پایدار.
"""
import random
import re
import time
import itertools

_id_counter = itertools.count(1000)


def next_id():
    return next(_id_counter)


# ---------------------------------------------------------------------------
# واحدهای سه‌زبانه پایه
# ---------------------------------------------------------------------------

def tri(fa, ar, en):
    return {"fa": fa, "ar": ar, "en": en}


CATEGORIES = [
    {"id": "steel", "icon": "bar-chart-3", "name": tri("فولاد و آهن‌آلات", "الحديد والصلب", "Steel & Rebar")},
    {"id": "cement", "icon": "package", "name": tri("سیمان", "الأسمنت", "Cement")},
    {"id": "gypsum", "icon": "layers", "name": tri("گچ", "الجبس", "Gypsum")},
    {"id": "plumbing", "icon": "wrench", "name": tri("تأسیسات", "التركيبات الصحية", "Plumbing & HVAC")},
    {"id": "electrical", "icon": "zap", "name": tri("برق", "الكهرباء", "Electrical")},
    {"id": "mechanical", "icon": "cog", "name": tri("مکانیک", "الميكانيكا", "Mechanical")},
    {"id": "industrial", "icon": "factory", "name": tri("تجهیزات صنعتی", "المعدات الصناعية", "Industrial Equip.")},
]

CITIES = [
    tri("تهران", "طهران", "Tehran"),
    tri("شیراز", "شيراز", "Shiraz"),
    tri("اصفهان", "إصفهان", "Isfahan"),
    tri("تبریز", "تبريز", "Tabriz"),
    tri("مشهد", "مشهد", "Mashhad"),
    tri("اهواز", "الأحواز", "Ahvaz"),
    tri("کرج", "كرج", "Karaj"),
]
CITY_KEYWORDS = {
    "تهران": 0, "شیراز": 1, "اصفهان": 2, "تبریز": 3, "مشهد": 4, "اهواز": 5, "کرج": 6,
}

MATERIALS = {
    "rebar": tri("میلگرد", "حديد التسليح", "Rebar"),
    "beam": tri("تیرآهن", "العتبات الحديدية", "Steel Beam (IPE)"),
    "cement": tri("سیمان", "الأسمنت", "Cement"),
    "sheet": tri("ورق فولادی", "الصاج الحديدي", "Steel Sheet"),
    "profile": tri("پروفیل", "بروفايل", "Steel Profile"),
    "gypsum": tri("گچ ساختمانی", "الجبس", "Building Gypsum"),
}

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def fa_digits_to_en(s):
    return s.translate({ord(p): str(i) for i, p in enumerate(PERSIAN_DIGITS)})


# ---------------------------------------------------------------------------
# موتور ساده برآورد و تفسیر درخواست (شبیه‌سازی NLP Parser / Estimation Engine)
# ---------------------------------------------------------------------------

def parse_rfq_text(text: str):
    """تحلیل سبک متن آزاد فارسی برای ساخت فهرست صورت‌مجلس (BOM) اولیه.

    این یک تخمین ابتدایی مبتنی بر کلیدواژه است (نه یک مدل زبانی واقعی) و
    صرفاً برای پر کردن فرم اولیه‌ای است که کاربر تأیید یا ویرایش می‌کند.
    """
    raw = text or ""
    norm = fa_digits_to_en(raw)

    area = 0
    m = re.search(r"(\d{2,6})\s*(متر\s*مربع|متر\s*زیربنا|مترمربع|متر)", norm)
    if m:
        area = int(m.group(1))

    city = None
    for name, _ in CITY_KEYWORDS.items():
        if name in norm:
            city = tri(name, CITIES[CITY_KEYWORDS[name]]["ar"], CITIES[CITY_KEYWORDS[name]]["en"])
            break

    sizes = [int(n) for n in re.findall(r"\b(\d{1,2})\b", norm) if 6 <= int(n) <= 40]

    bom = []
    base_area = area or 500  # مقدار پایه اگر متراژ ذکر نشده باشد

    if "میلگرد" in norm:
        rebar_sizes = sizes or [14]
        total_weight = round(base_area * 0.062, 1)  # تخمین تقریبی تن میلگرد به ازای متر زیربنا
        per_size = round(total_weight / len(rebar_sizes), 2)
        for sz in rebar_sizes[:4]:
            bom.append({
                "id": next_id(),
                "material": MATERIALS["rebar"],
                "spec": f"A3 - #{sz}",
                "qty": per_size,
                "unit": tri("تن", "طن", "ton"),
            })

    if "تیرآهن" in norm:
        beam_size = sizes[0] if sizes and "میلگرد" not in norm else 14
        total_weight = round(base_area * 0.018, 1)
        bom.append({
            "id": next_id(),
            "material": MATERIALS["beam"],
            "spec": f"IPE {beam_size}",
            "qty": total_weight,
            "unit": tri("تن", "طن", "ton"),
        })

    if "سیمان" in norm:
        bags = int(base_area * 0.42)
        bom.append({
            "id": next_id(),
            "material": MATERIALS["cement"],
            "spec": tri("تیپ ۲", "نوع ٢", "Type II"),
            "qty": bags,
            "unit": tri("کیسه", "كيس", "bag"),
        })

    if "ورق" in norm:
        bom.append({
            "id": next_id(),
            "material": MATERIALS["sheet"],
            "spec": tri("ST37 - ضخامت ۳", "ST37 - 3mm", "ST37 - 3mm"),
            "qty": round(base_area * 0.01, 1),
            "unit": tri("تن", "طن", "ton"),
        })

    if "پروفیل" in norm:
        bom.append({
            "id": next_id(),
            "material": MATERIALS["profile"],
            "spec": "40x40x2",
            "qty": round(base_area * 0.008, 1),
            "unit": tri("تن", "طن", "ton"),
        })

    if "گچ" in norm:
        bom.append({
            "id": next_id(),
            "material": MATERIALS["gypsum"],
            "spec": tri("سفید", "أبيض", "White"),
            "qty": int(base_area * 0.3),
            "unit": tri("کیسه", "كيس", "bag"),
        })

    if not bom:
        bom.append({
            "id": next_id(),
            "material": MATERIALS["rebar"],
            "spec": "A3 - #14",
            "qty": 5,
            "unit": tri("تن", "طن", "ton"),
        })

    return {
        "area_sqm": area,
        "city": city,
        "bom": bom,
    }


# ---------------------------------------------------------------------------
# تاریخچه قیمت (ویجت نوسانات قیمت روز)
# ---------------------------------------------------------------------------

def _gen_price_series(base, days=21, volatility=0.012, seed=1):
    rnd = random.Random(seed)
    price = base
    out = []
    for i in range(days):
        drift = rnd.uniform(-volatility, volatility)
        price = max(price * (1 + drift), base * 0.6)
        out.append(round(price))
    return out


_REBAR_SERIES = _gen_price_series(295000, seed=7)
_BEAM_SERIES = _gen_price_series(412000, seed=13)


def price_history(material: str):
    series = _REBAR_SERIES if material == "rebar" else _BEAM_SERIES
    today = series[-1]
    yesterday = series[-2]
    change_pct = round((today - yesterday) / yesterday * 100, 2)
    return {
        "material": material,
        "unit": tri("تومان / کیلوگرم", "تومان / كجم", "Toman / kg"),
        "series": series,
        "today": today,
        "change_pct": change_pct,
    }


# ---------------------------------------------------------------------------
# پروژه‌ها، استعلام‌ها و پیشنهادها (پنل خریدار)
# ---------------------------------------------------------------------------

SUPPLIER_NAMES = [
    tri("فولاد گسترش پارس", "فولاد جسترش بارس", "Pars Steel Expansion Co."),
    tri("آهن‌آلات ایران‌سازه", "حديد إيران سازه", "Iran Sazeh Ironworks"),
    tri("بازرگانی فلزات نوین", "تجارة المعادن الحديثة", "Novin Metals Trading"),
    tri("گروه صنعتی البرز فولاد", "مجموعة ألبرز الصناعية", "Alborz Steel Industrial Group"),
    tri("تجارت آهن جنوب", "تجارة حديد الجنوب", "South Iron Trade"),
    tri("شرکت تأمین مصالح کیان", "شركة كيان للتوريد", "Kian Supply Co."),
]


def _make_quotes(n, base_price):
    rnd = random.Random(base_price)
    quotes = []
    for i in range(n):
        supplier = SUPPLIER_NAMES[i % len(SUPPLIER_NAMES)]
        price = round(base_price * rnd.uniform(0.93, 1.07))
        quotes.append({
            "id": next_id(),
            "supplier": supplier,
            "price": price,
            "delivery_days": rnd.randint(2, 10),
            "payment_terms": rnd.choice([
                tri("نقدی", "نقدًا", "Cash"),
                tri("۳۰ روزه", "٣٠ يومًا", "30-day credit"),
                tri("۵۰٪ پیش‌پرداخت", "دفعة مقدمة ٥٠٪", "50% advance"),
            ]),
            "rating": round(rnd.uniform(3.6, 5.0), 1),
            "selected": False,
        })
    quotes.sort(key=lambda q: q["price"])
    return quotes


def seed_projects():
    projects = [
        {
            "id": next_id(),
            "name": tri("برج مسکونی الماس", "برج الماس السكني", "Diamond Residential Tower"),
            "city": CITIES[0],
            "progress": 64,
            "bom": [
                {"id": next_id(), "material": MATERIALS["rebar"], "spec": "A3 - #14", "qty": 32, "unit": tri("تن", "طن", "ton")},
                {"id": next_id(), "material": MATERIALS["rebar"], "spec": "A3 - #16", "qty": 28, "unit": tri("تن", "طن", "ton")},
                {"id": next_id(), "material": MATERIALS["beam"], "spec": "IPE 14", "qty": 11, "unit": tri("تن", "طن", "ton")},
            ],
            "rfqs": [
                {"id": next_id(), "title": MATERIALS["rebar"], "status": "open", "quotes": _make_quotes(4, 296000)},
                {"id": next_id(), "title": MATERIALS["beam"], "status": "open", "quotes": _make_quotes(3, 415000)},
            ],
        },
        {
            "id": next_id(),
            "name": tri("مجتمع تجاری ستاره شرق", "مجمع نجمة الشرق التجاري", "East Star Commercial Complex"),
            "city": CITIES[2],
            "progress": 31,
            "bom": [
                {"id": next_id(), "material": MATERIALS["cement"], "spec": tri("تیپ ۲", "نوع ٢", "Type II"), "qty": 1200, "unit": tri("کیسه", "كيس", "bag")},
                {"id": next_id(), "material": MATERIALS["gypsum"], "spec": tri("سفید", "أبيض", "White"), "qty": 800, "unit": tri("کیسه", "كيس", "bag")},
            ],
            "rfqs": [
                {"id": next_id(), "title": MATERIALS["cement"], "status": "open", "quotes": _make_quotes(5, 720000)},
            ],
        },
        {
            "id": next_id(),
            "name": tri("کارخانه فولاد سپاهان", "مصنع سباهان للصلب", "Sepahan Steel Plant"),
            "city": CITIES[3],
            "progress": 88,
            "bom": [
                {"id": next_id(), "material": MATERIALS["sheet"], "spec": "ST37 - 3mm", "qty": 18, "unit": tri("تن", "طن", "ton")},
            ],
            "rfqs": [
                {"id": next_id(), "title": MATERIALS["sheet"], "status": "closed", "quotes": _make_quotes(3, 510000)},
            ],
        },
    ]
    return projects


PROJECTS = seed_projects()


def all_projects():
    return PROJECTS


def find_project(pid):
    return next((p for p in PROJECTS if p["id"] == pid), None)


def find_rfq(pid, rid):
    p = find_project(pid)
    if not p:
        return None, None
    rfq = next((r for r in p["rfqs"] if r["id"] == rid), None)
    return p, rfq


def add_project_from_rfq(parsed, raw_text):
    project = {
        "id": next_id(),
        "name": tri("پروژه جدید", "مشروع جديد", "New Project"),
        "city": parsed.get("city") or CITIES[0],
        "progress": 4,
        "bom": parsed["bom"],
        "rfqs": [
            {
                "id": next_id(),
                "title": item["material"],
                "status": "open",
                "quotes": _make_quotes(random.randint(2, 5), 300000),
            }
            for item in parsed["bom"][:3]
        ],
        "raw_request": raw_text,
    }
    PROJECTS.insert(0, project)
    return project


# ---------------------------------------------------------------------------
# فید استعلام برای پنل فروشنده
# ---------------------------------------------------------------------------

def supplier_feed():
    now = time.time()
    items = []
    rnd = random.Random(42)
    for p in PROJECTS:
        for rfq in p["rfqs"]:
            if rfq["status"] != "open":
                continue
            deadline = now + rnd.randint(120, 5400)
            items.append({
                "id": rfq["id"],
                "project": p["name"],
                "city": p["city"],
                "material": rfq["title"],
                "qty": next((b["qty"] for b in p["bom"] if b["material"] == rfq["title"]), 0),
                "unit": next((b["unit"] for b in p["bom"] if b["material"] == rfq["title"]), tri("تن", "طن", "ton")),
                "deadline_ts": deadline,
                "quote_count": len(rfq["quotes"]),
            })
    return items


# ---------------------------------------------------------------------------
# پنل مدیر سیستم
# ---------------------------------------------------------------------------

_ADMIN_USERS = [
    {"id": next_id(), "name": tri("شرکت ساختمانی پویا", "شركة بويا للبناء", "Pooya Construction Co."), "role": "buyer", "city": CITIES[0], "status": "active"},
    {"id": next_id(), "name": tri("فولاد گسترش پارس", "فولاد جسترش بارس", "Pars Steel Expansion Co."), "role": "supplier", "city": CITIES[0], "status": "active"},
    {"id": next_id(), "name": tri("آهن‌آلات ایران‌سازه", "حديد إيران سازه", "Iran Sazeh Ironworks"), "role": "supplier", "city": CITIES[3], "status": "pending"},
    {"id": next_id(), "name": tri("انبوه‌سازان البرز", "مطورو ألبرز", "Alborz Developers"), "role": "buyer", "city": CITIES[6], "status": "active"},
    {"id": next_id(), "name": tri("بازرگانی فلزات نوین", "تجارة المعادن الحديثة", "Novin Metals Trading"), "role": "supplier", "city": CITIES[2], "status": "suspended"},
]


def admin_stats():
    return {
        "total_users": 4820,
        "total_suppliers": 612,
        "monthly_volume_toman": 184_500_000_000,
        "monthly_commission_toman": 3_320_000_000,
        "pending_verifications": 14,
        "revenue_series": [120, 145, 132, 168, 190, 175, 210, 240, 228, 260, 295, 332],
        "users": _ADMIN_USERS,
        "categories": CATEGORIES,
    }


def set_user_status(uid, status):
    user = next((u for u in _ADMIN_USERS if u["id"] == uid), None)
    if user:
        user["status"] = status
    return user


# ---------------------------------------------------------------------------
# موجودی، فروش و تنظیمات کمیسیون (پنل فروشنده / مدیر)
# ---------------------------------------------------------------------------

SUPPLIER_INVENTORY = [
    {"id": next_id(), "material": MATERIALS["rebar"], "spec": "A3 - #14", "stock": 42, "unit": tri("تن", "طن", "ton"), "base_price": 296000},
    {"id": next_id(), "material": MATERIALS["rebar"], "spec": "A3 - #16", "stock": 35, "unit": tri("تن", "طن", "ton"), "base_price": 299500},
    {"id": next_id(), "material": MATERIALS["beam"], "spec": "IPE 14", "stock": 18, "unit": tri("تن", "طن", "ton"), "base_price": 412000},
    {"id": next_id(), "material": MATERIALS["sheet"], "spec": "ST37 - 3mm", "stock": 24, "unit": tri("تن", "طن", "ton"), "base_price": 503000},
]

_SUPPLIER_SALES_SERIES = [82, 95, 88, 110, 102, 128, 140, 134, 150, 168, 175, 190]

_COMMISSION_SETTINGS = {
    "tier1_monthly": 1_500_000,
    "tier2_monthly": 4_000_000,
    "fee_percent": 2.0,
}


def supplier_sales():
    return {"series": _SUPPLIER_SALES_SERIES, "unit": tri("میلیون تومان", "مليون تومان", "M Toman")}


def get_commission_settings():
    return _COMMISSION_SETTINGS


def update_commission_settings(payload):
    for key in ("tier1_monthly", "tier2_monthly", "fee_percent"):
        if key in payload:
            _COMMISSION_SETTINGS[key] = payload[key]
    return _COMMISSION_SETTINGS

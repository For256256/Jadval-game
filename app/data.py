# -*- coding: utf-8 -*-
"""داده‌های مرجع ثابت (دسته‌ها، شهرها، کالاها) و موتور تفسیر RFQ سازه‌مارکت.

این ماژول فقط شامل داده‌های مرجع ایستا و منطق بدون‌حالت (stateless) است؛
داده‌های واقعی و پایدار (کاربران، پروژه‌ها، استعلام‌ها، پیشنهادها، موجودی و
فروش) در app/models.py روی پایگاه‌داده نگه‌داری می‌شوند.
"""
import itertools
import random
import re

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


def find_city_by_fa(name):
    return next((c for c in CITIES if c["fa"] == name), None)


MATERIALS = {
    "rebar": tri("میلگرد", "حديد التسليح", "Rebar"),
    "beam": tri("تیرآهن", "العتبات الحديدية", "Steel Beam (IPE)"),
    "cement": tri("سیمان", "الأسمنت", "Cement"),
    "sheet": tri("ورق فولادی", "الصاج الحديدي", "Steel Sheet"),
    "profile": tri("پروفیل", "بروفايل", "Steel Profile"),
    "gypsum": tri("گچ ساختمانی", "الجبس", "Building Gypsum"),
}

SUPPLIER_NAMES = [
    tri("فولاد گسترش پارس", "فولاد جسترش بارس", "Pars Steel Expansion Co."),
    tri("آهن‌آلات ایران‌سازه", "حديد إيران سازه", "Iran Sazeh Ironworks"),
    tri("بازرگانی فلزات نوین", "تجارة المعادن الحديثة", "Novin Metals Trading"),
    tri("گروه صنعتی البرز فولاد", "مجموعة ألبرز الصناعية", "Alborz Steel Industrial Group"),
    tri("تجارت آهن جنوب", "تجارة حديد الجنوب", "South Iron Trade"),
    tri("شرکت تأمین مصالح کیان", "شركة كيان للتوريد", "Kian Supply Co."),
]

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
                "material_id": "rebar",
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
            "material_id": "beam",
            "material": MATERIALS["beam"],
            "spec": f"IPE {beam_size}",
            "qty": total_weight,
            "unit": tri("تن", "طن", "ton"),
        })

    if "سیمان" in norm:
        bags = int(base_area * 0.42)
        bom.append({
            "id": next_id(),
            "material_id": "cement",
            "material": MATERIALS["cement"],
            "spec": tri("تیپ ۲", "نوع ٢", "Type II"),
            "qty": bags,
            "unit": tri("کیسه", "كيس", "bag"),
        })

    if "ورق" in norm:
        bom.append({
            "id": next_id(),
            "material_id": "sheet",
            "material": MATERIALS["sheet"],
            "spec": tri("ST37 - ضخامت ۳", "ST37 - 3mm", "ST37 - 3mm"),
            "qty": round(base_area * 0.01, 1),
            "unit": tri("تن", "طن", "ton"),
        })

    if "پروفیل" in norm:
        bom.append({
            "id": next_id(),
            "material_id": "profile",
            "material": MATERIALS["profile"],
            "spec": "40x40x2",
            "qty": round(base_area * 0.008, 1),
            "unit": tri("تن", "طن", "ton"),
        })

    if "گچ" in norm:
        bom.append({
            "id": next_id(),
            "material_id": "gypsum",
            "material": MATERIALS["gypsum"],
            "spec": tri("سفید", "أبيض", "White"),
            "qty": int(base_area * 0.3),
            "unit": tri("کیسه", "كيس", "bag"),
        })

    if not bom:
        bom.append({
            "id": next_id(),
            "material_id": "rebar",
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


def make_demo_quotes(n, base_price, seed=None):
    """فهرست پیشنهادهای نمایشیِ رقبا برای شبیه‌سازی فضای رقابتی بازار.

    این پیشنهادها به هیچ حساب کاربری واقعی متصل نیستند (supplier_id=None) و
    صرفاً عکس فوری نام تأمین‌کننده را در quote.supplier_name نگه می‌دارند.
    """
    rnd = random.Random(seed if seed is not None else base_price)
    quotes = []
    for i in range(n):
        supplier = SUPPLIER_NAMES[i % len(SUPPLIER_NAMES)]
        price = round(base_price * rnd.uniform(0.93, 1.07))
        quotes.append({
            "supplier_name": supplier,
            "price": price,
            "delivery_days": rnd.randint(2, 10),
            "payment_terms": rnd.choice([
                tri("نقدی", "نقدًا", "Cash"),
                tri("۳۰ روزه", "٣٠ يومًا", "30-day credit"),
                tri("۵۰٪ پیش‌پرداخت", "دفعة مقدمة ٥٠٪", "50% advance"),
            ]),
            "rating": round(rnd.uniform(3.6, 5.0), 1),
        })
    return quotes


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

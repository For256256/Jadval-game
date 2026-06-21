# -*- coding: utf-8 -*-
"""داده‌های مرجع ثابت (دسته‌ها، شهرها، کالاها) و موتور تفسیر RFQ سازه‌مارکت.

این ماژول فقط شامل داده‌های مرجع ایستا و منطق بدون‌حالت (stateless) است؛
داده‌های واقعی و پایدار (کاربران، پروژه‌ها، استعلام‌ها، پیشنهادها، موجودی و
فروش) در app/models.py روی پایگاه‌داده نگه‌داری می‌شوند.
"""
import itertools
import random

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

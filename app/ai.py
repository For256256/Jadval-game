# -*- coding: utf-8 -*-
"""تحلیل هوشمند درخواست خرید (RFQ) با مدل Claude — جایگزین واقعی موتور حدسی قبلی.

این ماژول متن آزاد خریدار (فارسی/عربی/انگلیسی) را به یک فهرست ساختاریافتهٔ
مصالح (BOM) تبدیل می‌کند؛ تخمین مقادیر بر اساس دانش مهندسی برآورد ساخت‌وساز
توسط خود مدل انجام می‌شود، نه فرمول‌های ثابت محلی.
"""
import os

from anthropic import Anthropic

from app import data

MODEL = "claude-sonnet-4-6"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY تنظیم نشده است")
        _client = Anthropic(api_key=api_key)
    return _client


MATERIAL_IDS = list(data.MATERIALS.keys())
CITY_NAMES_FA = [c["fa"] for c in data.CITIES]

UNIT_TRI = {
    "تن": data.tri("تن", "طن", "ton"),
    "کیسه": data.tri("کیسه", "كيس", "bag"),
    "متر": data.tri("متر", "متر", "m"),
    "عدد": data.tri("عدد", "قطعة", "pcs"),
    "کیلوگرم": data.tri("کیلوگرم", "كيلوغرام", "kg"),
}

SYSTEM_PROMPT = f"""تو یک مهندس برآورد مصالح ساختمانی برای «سازه‌مارکت» (بازار دیجیتال مصالح ساختمانی ایران) هستی.
کاربر نیاز پروژهٔ خود را به زبان فارسی، عربی یا انگلیسی توضیح می‌دهد و وظیفهٔ تو استخراج فهرست دقیق مصالح (BOM) از طریق تابع submit_bom است.

قوانین برآورد:
۱. اگر کاربر مقدار یا سایز مشخصی ذکر کرده (مثلاً «۲۰۰۰ کیسه سیمان» یا «میلگرد ۱۴ و ۱۶»)، همان مقادیر دقیق را استخراج کن، نه تخمین.
۲. اگر فقط متراژ زیربنا ذکر شده و مقدار کالا مشخص نیست، با استانداردهای مرسوم برآورد ساخت‌وساز در ایران تخمین بزن:
   - میلگرد سازه‌ای: حدود ۶۰ تا ۶۵ کیلوگرم به ازای هر متر مربع زیربنا برای سازهٔ بتنی مسکونی معمولی.
   - تیرآهن (در صورت ذکر اسکلت فلزی): حدود ۱۸ تا ۲۲ کیلوگرم به ازای هر متر مربع.
   - سیمان: حدود ۰.۴ تا ۰.۵ کیسهٔ ۵۰ کیلوگرمی به ازای هر متر مربع برای ملات و نازک‌کاری.
   - گچ ساختمانی: حدود ۰.۳ کیسه به ازای هر متر مربع برای سفیدکاری.
   - ورق فولادی و پروفیل: بر اساس کاربرد ذکرشده در متن، تخمین مهندسی منطقی بزن.
۳. شهر تحویل را فقط در صورتی برگردان که دقیقاً یکی از این شهرها در متن ذکر شده باشد: {"، ".join(CITY_NAMES_FA)}. در غیر این صورت آن را خالی (null) بگذار.
۴. واحد هر قلم را متناسب با نوع کالا انتخاب کن (تن برای فولاد/میلگرد/تیرآهن/ورق/پروفیل، کیسه برای سیمان/گچ).
۵. اگر متن هیچ کالای ساختمانی شناخته‌شده‌ای ندارد، حداقل یک قلم منطقی و محتاطانه (مثلاً میلگرد پایه) پیشنهاد بده تا فهرست خالی نباشد.
۶. همیشه و فقط از طریق تابع submit_bom پاسخ بده؛ هیچ متن آزاد دیگری ننویس."""

TOOL_SCHEMA = {
    "name": "submit_bom",
    "description": "ثبت فهرست مصالح ساختمانی استخراج‌شده از متن درخواست خریدار",
    "input_schema": {
        "type": "object",
        "properties": {
            "area_sqm": {
                "type": "integer",
                "description": "متراژ زیربنای پروژه به متر مربع؛ اگر در متن ذکر نشده 0 بفرست",
            },
            "city_fa": {
                "type": ["string", "null"],
                "enum": CITY_NAMES_FA + [None],
                "description": "نام شهر تحویل به فارسی؛ اگر ذکر نشده null",
            },
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "material_id": {"type": "string", "enum": MATERIAL_IDS},
                        "spec": {"type": "string", "description": "مشخصات فنی مانند سایز/گرید/ضخامت، مثلاً 'A3 - #14' یا 'IPE 16'"},
                        "qty": {"type": "number"},
                        "unit_fa": {"type": "string", "enum": list(UNIT_TRI.keys())},
                    },
                    "required": ["material_id", "spec", "qty", "unit_fa"],
                },
            },
        },
        "required": ["area_sqm", "items"],
    },
}


def parse_rfq_text(text: str) -> dict:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_bom"},
    )

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if not tool_use:
        raise RuntimeError("پاسخ نامعتبر از سرویس هوش مصنوعی")

    args = tool_use.input
    city = data.find_city_by_fa(args.get("city_fa")) if args.get("city_fa") else None

    bom = []
    for item in args.get("items", []):
        material_id = item.get("material_id")
        material = data.MATERIALS.get(material_id)
        if not material:
            continue
        bom.append({
            "id": data.next_id(),
            "material_id": material_id,
            "material": material,
            "spec": item.get("spec") or "",
            "qty": float(item.get("qty") or 0),
            "unit": UNIT_TRI.get(item.get("unit_fa"), UNIT_TRI["عدد"]),
        })

    return {
        "area_sqm": int(args.get("area_sqm") or 0),
        "city": city,
        "bom": bom,
    }

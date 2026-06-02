# -*- coding: utf-8 -*-
"""
بک‌اند بازی جدول کلمات فارسی.
"""
import os
import secrets as pysecrets
from flask import Flask, jsonify, request, session, render_template

from app.crossword import build_level, LEVELS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = os.environ.get("SECRET_KEY", pysecrets.token_hex(32))

# کش مراحل ساخته‌شده برای هر بازیکن (بر اساس seed ثابت تا تازه‌سازی صفحه جدول را عوض نکند)
_LEVEL_CACHE = {}


def get_level(level_index, seed):
    key = (level_index, seed)
    if key not in _LEVEL_CACHE:
        _LEVEL_CACHE[key] = build_level(level_index, seed=seed)
    return _LEVEL_CACHE[key]


def public_payload(data):
    """نسخه‌ای از داده جدول که پاسخ‌ها در آن نیست (برای ارسال به کلاینت)."""
    grid = []
    for row in data["grid"]:
        grow = []
        for cell in row:
            if cell is None:
                grow.append(None)
            else:
                grow.append({"num": cell["num"]})  # حرف راه‌حل ارسال نمی‌شود
        grid.append(grow)

    def strip(clues):
        return [{"num": c["num"], "clue": c["clue"], "row": c["row"],
                 "col": c["col"], "len": c["len"]} for c in clues]

    secret = data.get("secret")
    secret_pub = None
    if secret:
        secret_pub = {
            "length": secret["length"],
            "key_cells": [{"row": k["row"], "col": k["col"]} for k in secret["key_cells"]],
            "hint": secret["hint"],
        }
    return {
        "level": data["level"], "name": data["name"],
        "rows": data["rows"], "cols": data["cols"],
        "grid": grid,
        "across": strip(data["across"]),
        "down": strip(data["down"]),
        "word_count": data["word_count"],
        "total_levels": len(LEVELS),
        "secret": secret_pub,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/level/<int:level_num>")
def api_level(level_num):
    idx = level_num - 1
    if idx < 0 or idx >= len(LEVELS):
        return jsonify({"error": "مرحله نامعتبر"}), 404
    # seed ثابت برای هر بازیکن و هر مرحله
    if "seed" not in session:
        session["seed"] = pysecrets.randbelow(10_000_000)
    data = get_level(idx, session["seed"])
    return jsonify(public_payload(data))


@app.route("/api/check", methods=["POST"])
def api_check():
    """بررسی یک کلمه واردشده توسط بازیکن."""
    body = request.get_json(force=True)
    level_num = int(body.get("level", 1))
    direction = body.get("dir")
    num = int(body.get("num"))
    answer = (body.get("answer") or "").strip()
    answer = answer.replace("ي", "ی").replace("ك", "ک").replace("\u200c", "").replace(" ", "")

    idx = level_num - 1
    if idx < 0 or idx >= len(LEVELS):
        return jsonify({"error": "مرحله نامعتبر"}), 404
    seed = session.get("seed", 0)
    data = get_level(idx, seed)
    clues = data["across"] if direction == "across" else data["down"]
    target = next((c for c in clues if c["num"] == num), None)
    if not target:
        return jsonify({"correct": False, "error": "کلمه یافت نشد"})
    correct = (answer == target["answer"])
    return jsonify({"correct": correct, "len": target["len"]})


@app.route("/api/check_secret", methods=["POST"])
def api_check_secret():
    """بررسی کلمه رمز مرحله."""
    body = request.get_json(force=True)
    level_num = int(body.get("level", 1))
    guess = (body.get("answer") or "").strip()
    guess = guess.replace("ي", "ی").replace("ك", "ک").replace("\u200c", "").replace(" ", "")
    idx = level_num - 1
    if idx < 0 or idx >= len(LEVELS):
        return jsonify({"error": "مرحله نامعتبر"}), 404
    seed = session.get("seed", 0)
    data = get_level(idx, seed)
    secret = data.get("secret")
    if not secret:
        return jsonify({"correct": False})
    return jsonify({"correct": guess == secret["answer"]})


@app.route("/api/reveal", methods=["POST"])
def api_reveal():
    """نمایش یک حرف کمکی برای یک کلمه (راهنما)."""
    body = request.get_json(force=True)
    level_num = int(body.get("level", 1))
    direction = body.get("dir")
    num = int(body.get("num"))
    pos = int(body.get("pos", 0))
    idx = level_num - 1
    seed = session.get("seed", 0)
    data = get_level(idx, seed)
    clues = data["across"] if direction == "across" else data["down"]
    target = next((c for c in clues if c["num"] == num), None)
    if not target or pos >= target["len"]:
        return jsonify({"error": "نامعتبر"}), 400
    return jsonify({"letter": target["answer"][pos]})


@app.route("/manifest.webmanifest")
def manifest():
    return jsonify({
        "name": "جدول کلمات فارسی",
        "short_name": "جدول",
        "description": "بازی جدول کلمات متقاطع فارسی با مراحل آسان تا سخت",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f2a30",
        "theme_color": "#0f2a30",
        "dir": "rtl",
        "lang": "fa",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


@app.route("/sw.js")
def service_worker():
    resp = app.send_static_file("sw.js")
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/health")
def health():
    return jsonify({"status": "ok", "levels": len(LEVELS)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 65535)))

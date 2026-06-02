# -*- coding: utf-8 -*-
"""
سازنده جدول کلمات متقاطع.
کلمات را به صورت افقی (across) و عمودی (down) روی شبکه قرار می‌دهد
به طوری که در نقاط تقاطع حرف مشترک داشته باشند.
"""
import random
from app.words import CLEAN_WORDS

ACROSS = "across"  # افقی
DOWN = "down"      # عمودی


class Crossword:
    def __init__(self, size, words_pool):
        self.size = size
        # فقط کلماتی که در شبکه جا می‌شوند
        fitting = [(w, c) for (w, c) in words_pool if len(w) <= size]
        # مرتب‌سازی کلمات از بلند به کوتاه برای جای‌گذاری بهتر
        self.pool = sorted(fitting, key=lambda x: -len(x[0]))
        self.grid = [[None] * size for _ in range(size)]
        self.placed = []  # هر آیتم: dict(word, clue, row, col, dir)

    def _fits(self, word, row, col, direction):
        n = len(word)
        if direction == ACROSS:
            if col < 0 or col + n > self.size:
                return False, 0
        else:
            if row < 0 or row + n > self.size:
                return False, 0
        crossings = 0
        for i, ch in enumerate(word):
            r = row + (i if direction == DOWN else 0)
            c = col + (i if direction == ACROSS else 0)
            cell = self.grid[r][c]
            if cell is not None:
                if cell != ch:
                    return False, 0
                crossings += 1
            else:
                # سلول‌های مجاور (عمود بر جهت کلمه) نباید پر باشند
                if direction == ACROSS:
                    if r > 0 and self.grid[r - 1][c] is not None:
                        return False, 0
                    if r < self.size - 1 and self.grid[r + 1][c] is not None:
                        return False, 0
                else:
                    if c > 0 and self.grid[r][c - 1] is not None:
                        return False, 0
                    if c < self.size - 1 and self.grid[r][c + 1] is not None:
                        return False, 0
        # سلول‌های قبل و بعد از کلمه باید خالی باشند
        if direction == ACROSS:
            if col > 0 and self.grid[row][col - 1] is not None:
                return False, 0
            if col + n < self.size and self.grid[row][col + n] is not None:
                return False, 0
        else:
            if row > 0 and self.grid[row - 1][col] is not None:
                return False, 0
            if row + n < self.size and self.grid[row + n][col] is not None:
                return False, 0
        return True, crossings

    def _place(self, word, clue, row, col, direction):
        for i, ch in enumerate(word):
            r = row + (i if direction == DOWN else 0)
            c = col + (i if direction == ACROSS else 0)
            self.grid[r][c] = ch
        self.placed.append({
            "word": word, "clue": clue,
            "row": row, "col": col, "dir": direction
        })

    def generate(self, target_count):
        if not self.pool:
            return
        # اولین کلمه را وسط افقی قرار بده (کلمه‌ای که حتماً جا شود)
        first_w, first_c = self.pool[0]
        start_col = max(0, (self.size - len(first_w)) // 2)
        start_row = self.size // 2
        self._place(first_w, first_c, start_row, start_col, ACROSS)
        used = {first_w}

        attempts = 0
        max_attempts = target_count * 400
        while len(self.placed) < target_count and attempts < max_attempts:
            attempts += 1
            word, clue = random.choice(self.pool)
            if word in used:
                continue
            best = None
            # تلاش برای تقاطع با کلمات موجود
            for letter_idx, ch in enumerate(word):
                for p in self.placed:
                    pw = p["word"]
                    for pi, pch in enumerate(pw):
                        if pch != ch:
                            continue
                        if p["dir"] == ACROSS:
                            # کلمه جدید عمودی می‌شود
                            row = p["row"] - letter_idx
                            col = p["col"] + pi
                            ok, cr = self._fits(word, row, col, DOWN)
                            if ok and cr > 0:
                                if best is None or cr > best[3]:
                                    best = (row, col, DOWN, cr)
                        else:
                            row = p["row"] + pi
                            col = p["col"] - letter_idx
                            ok, cr = self._fits(word, row, col, ACROSS)
                            if ok and cr > 0:
                                if best is None or cr > best[3]:
                                    best = (row, col, ACROSS, cr)
            if best:
                self._place(word, clue, best[0], best[1], best[2])
                used.add(word)

    def trim(self):
        """حذف ردیف/ستون‌های خالی اطراف و فشرده‌سازی شبکه."""
        rows = [r for r in range(self.size)
                if any(self.grid[r][c] is not None for c in range(self.size))]
        cols = [c for c in range(self.size)
                if any(self.grid[r][c] is not None for r in range(self.size))]
        if not rows or not cols:
            return
        r0, r1 = min(rows), max(rows)
        c0, c1 = min(cols), max(cols)
        new_grid = [[self.grid[r][c] for c in range(c0, c1 + 1)]
                    for r in range(r0, r1 + 1)]
        self.grid = new_grid
        self.size_rows = r1 - r0 + 1
        self.size_cols = c1 - c0 + 1
        for p in self.placed:
            p["row"] -= r0
            p["col"] -= c0

    def export(self):
        self.trim()
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows else 0
        # شماره‌گذاری خانه‌های شروع
        starts = {}
        num = 0
        cells = {}
        for p in self.placed:
            cells[(p["row"], p["col"])] = True
        # شماره‌گذاری استاندارد جدول: از بالا-راست به پایین
        numbering = {}
        n = 0
        for r in range(rows):
            for c in range(cols):
                if self.grid[r][c] is None:
                    continue
                starts_here = False
                for p in self.placed:
                    if p["row"] == r and p["col"] == c:
                        starts_here = True
                if starts_here:
                    n += 1
                    numbering[(r, c)] = n
        across_clues = []
        down_clues = []
        for p in sorted(self.placed, key=lambda x: numbering[(x["row"], x["col"])]):
            num = numbering[(p["row"], p["col"])]
            entry = {
                "num": num, "clue": p["clue"], "row": p["row"],
                "col": p["col"], "len": len(p["word"]),
                "answer": p["word"]
            }
            if p["dir"] == ACROSS:
                across_clues.append(entry)
            else:
                down_clues.append(entry)
        # ساخت نقشه سلول‌ها
        grid_meta = []
        for r in range(rows):
            row_meta = []
            for c in range(cols):
                if self.grid[r][c] is None:
                    row_meta.append(None)
                else:
                    row_meta.append({
                        "sol": self.grid[r][c],
                        "num": numbering.get((r, c), 0)
                    })
            grid_meta.append(row_meta)
        return {
            "rows": rows, "cols": cols,
            "grid": grid_meta,
            "across": across_clues,
            "down": down_clues,
            "word_count": len(self.placed)
        }


# پیکربندی مراحل: (اندازه شبکه, تعداد کلمات هدف, نام مرحله)
LEVELS = [
    (7, 6, "آسان"),
    (9, 9, "ساده"),
    (11, 12, "مبتدی"),
    (13, 16, "متوسط"),
    (16, 20, "پیشرفته"),
    (19, 25, "دشوار"),
    (22, 30, "چالش"),
    (25, 36, "حرفه‌ای"),
    (28, 42, "استاد"),
    (30, 50, "افسانه‌ای"),
]


def build_level(level_index, seed=None):
    if seed is not None:
        random.seed(seed)
    size, count, name = LEVELS[level_index]
    # برای شبکه‌های بزرگ به کلمات بیشتری نیاز داریم؛ کل مجموعه استفاده می‌شود
    cw = Crossword(size, list(CLEAN_WORDS))
    cw.generate(count)
    data = cw.export()
    data["level"] = level_index + 1
    data["name"] = name
    data["target_size"] = size
    data["secret"] = _build_secret(data)
    return data


def _build_secret(data):
    """
    مرحله کشف رمز: چند خانه از جدولِ حل‌شده مشخص می‌شوند.
    حروف این خانه‌ها به ترتیب، یک «کلمه رمز» می‌سازند که بازیکن باید آن را کشف کند.
    کلمه رمز از میان همان کلمات جدول انتخاب می‌شود.
    """
    placed_words = data["across"] + data["down"]
    if not placed_words:
        return None
    # یک کلمه از جدول را به عنوان رمز انتخاب کن (ترجیحاً ۳ تا ۶ حرفی)
    candidates = [w for w in placed_words if 3 <= w["len"] <= 6]
    if not candidates:
        candidates = placed_words
    secret_entry = random.choice(candidates)
    secret = secret_entry["answer"]

    # برای هر حرف رمز، یک خانه در شبکه پیدا کن که آن حرف را داشته باشد
    # و آن خانه را به عنوان «خانه کلیدی» علامت بزن
    rows, cols = data["rows"], data["cols"]
    letter_positions = {}
    for r in range(rows):
        for c in range(cols):
            cell = data["grid"][r][c]
            if cell:
                letter_positions.setdefault(cell["sol"], []).append((r, c))

    key_cells = []
    used = set()
    ok = True
    for ch in secret:
        pos_list = letter_positions.get(ch, [])
        chosen = None
        for pos in pos_list:
            if pos not in used:
                chosen = pos
                break
        if chosen is None:
            ok = False
            break
        used.add(chosen)
        key_cells.append({"row": chosen[0], "col": chosen[1], "letter": ch})

    if not ok:
        # اگر نشد، حروف رمز را مستقیم از خانه‌های متوالی یک کلمه بگیر
        key_cells = []
        e = secret_entry
        for i, ch in enumerate(e["answer"]):
            r = e["row"] + (i if e in data["down"] else 0)
            c = e["col"] + (i if e in data["across"] else 0)
            key_cells.append({"row": r, "col": c, "letter": ch})

    return {
        "answer": secret,
        "length": len(secret),
        "key_cells": key_cells,
        "hint": f"کلمه رمز {len(secret)} حرفی است و در میان کلمات همین جدول پنهان شده است."
    }

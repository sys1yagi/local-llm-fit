"""日付の部品。

西暦・和暦・相対表現・期間・月末を扱う。
生成器は「先に日付を決めて、それを文面に書き起こす」ので、
1つの日付から複数の書き方を作れることが必要になる。
"""

from __future__ import annotations

import datetime
import random

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
REIWA_ORIGIN = 2018  # 令和1年 = 2019年


def pick(rng: random.Random, year: int = 2026,
         months: tuple[int, int] = (1, 12)) -> datetime.date:
    month = rng.randint(*months)
    return datetime.date(year, month, rng.randint(1, 28))


def month_end(year: int, month: int) -> datetime.date:
    if month == 12:
        return datetime.date(year, 12, 31)
    return datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)


def add_days(d: datetime.date, n: int) -> datetime.date:
    return d + datetime.timedelta(days=n)


def add_months(d: datetime.date, n: int) -> datetime.date:
    """月末をまたぐときは、その月の末日に丸める。"""
    total = (d.year * 12 + d.month - 1) + n
    year, month = divmod(total, 12)
    month += 1
    last = month_end(year, month).day
    return datetime.date(year, month, min(d.day, last))


def iso(d: datetime.date) -> str:
    return d.isoformat()


def ja(d: datetime.date) -> str:
    return f"{d.year}年{d.month}月{d.day}日"


def slash(d: datetime.date) -> str:
    return f"{d.year}/{d.month:02d}/{d.day:02d}"


def dot(d: datetime.date) -> str:
    return f"{d.year}.{d.month}.{d.day}"


def wareki(d: datetime.date) -> str:
    return f"令和{d.year - REIWA_ORIGIN}年{d.month}月{d.day}日"


def md(d: datetime.date) -> str:
    return f"{d.month}/{d.day}"


def weekday_ja(d: datetime.date) -> str:
    return WEEKDAYS[d.weekday()]


def with_weekday(d: datetime.date) -> str:
    return f"{ja(d)}（{weekday_ja(d)}）"


def next_weekday(base: datetime.date, weekday: int, weeks: int = 0) -> datetime.date:
    """base を含む週の次に来る指定曜日。weeks を足すとその週数ぶん先。

    weekday は月曜0〜日曜6。base 当日は含めない。
    """
    ahead = (weekday - base.weekday()) % 7 or 7
    return base + datetime.timedelta(days=ahead + 7 * weeks)


def relative_phrase(base: datetime.date, target: datetime.date) -> str | None:
    """base から見た target の言い方。うまく言えなければ None。"""
    delta = (target - base).days
    if delta == 1:
        return "明日"
    if delta == 2:
        return "明後日"
    same_week = next_weekday(base, target.weekday(), 0) == target
    next_week = next_weekday(base, target.weekday(), 1) == target
    if same_week:
        return f"今週{weekday_ja(target)}曜"
    if next_week:
        return f"来週{weekday_ja(target)}曜"
    return None

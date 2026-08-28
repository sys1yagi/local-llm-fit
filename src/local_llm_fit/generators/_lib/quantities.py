"""数量の部品。個数・面積・時間・点数。"""

from __future__ import annotations

import random

UNITS = ["個", "枚", "本", "式", "台", "件"]


def count(rng: random.Random, lo: int = 1, hi: int = 30) -> int:
    return rng.randint(lo, hi)


def unit(rng: random.Random) -> str:
    return rng.choice(UNITS)


def area_sqm(rng: random.Random, lo: int = 20, hi: int = 120) -> float:
    """平米。小数第2位まで。"""
    return round(rng.uniform(lo, hi), 2)


def sqm_to_tsubo(sqm: float) -> float:
    return round(sqm / 3.30578, 2)


def hours(rng: random.Random, lo: float = 0.5, hi: float = 12.0) -> float:
    """0.5時間刻み。"""
    steps = int((hi - lo) / 0.5)
    return lo + 0.5 * rng.randint(0, steps)


def points(rng: random.Random, lo: int = 50, hi: int = 900) -> int:
    """診療報酬の点数。"""
    return rng.randrange(lo, hi, 1)


def days(rng: random.Random, choices: list[int] | None = None) -> int:
    """規程に出てくる日数。"""
    return rng.choice(choices or [3, 5, 7, 10, 14, 20, 30, 60, 90])

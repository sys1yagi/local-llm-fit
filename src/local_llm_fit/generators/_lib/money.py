"""金額の部品。円・カンマ区切り・税込税抜・負数。"""

from __future__ import annotations

import random

TAX_RATE = 0.10


def yen(rng: random.Random, lo: int, hi: int, step: int = 100) -> int:
    return rng.randrange(lo, hi, step)


def comma(n: int) -> str:
    return f"{n:,}"


def plain(n: int) -> str:
    return str(n)


def with_unit(n: int) -> str:
    return f"{n:,}円"


def yen_mark(n: int) -> str:
    return f"¥{n:,}"


def tax(subtotal: int, rate: float = TAX_RATE) -> int:
    """消費税。1円未満は切り捨てる。"""
    return int(subtotal * rate)


def with_tax(subtotal: int, rate: float = TAX_RATE) -> int:
    return subtotal + tax(subtotal, rate)


def signed(n: int) -> str:
    """出金を負数で書くときの表記。"""
    return f"-{n:,}" if n < 0 else f"{n:,}"


def paren_negative(n: int) -> str:
    """会計でよくある、負数を括弧で書く形。"""
    return f"({abs(n):,})" if n < 0 else f"{n:,}"

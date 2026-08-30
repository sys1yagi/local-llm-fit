"""電話番号の部品。市外局番・携帯・内線と、現場に出てくる書き方。

書き方（ハイフン・括弧・全角）を変えても同じ1本の番号なので、
伏せ字にするタスクでは、書き方だけを行ごとに変えて正解を動かさずに済む。
"""

from __future__ import annotations

import random

AREA_CODES = ["03", "045", "06", "052", "092", "011", "022", "075", "082", "048"]
MOBILE_HEADS = ["090", "080", "070"]


def landline(rng: random.Random) -> tuple[str, str, str]:
    """(市外局番, 市内局番, 加入者番号)。"""
    return (rng.choice(AREA_CODES),
            f"{rng.randint(1000, 9999)}",
            f"{rng.randint(1000, 9999)}")


def mobile(rng: random.Random) -> tuple[str, str, str]:
    return (rng.choice(MOBILE_HEADS),
            f"{rng.randint(1000, 9999)}",
            f"{rng.randint(1000, 9999)}")


def formats(parts: tuple[str, str, str]) -> list[str]:
    """同じ番号の書き方。どれも指す先は同じ。"""
    a, b, c = parts
    return [f"{a}-{b}-{c}", f"({a}){b}-{c}", f"{a}({b}){c}", f"{a}{b}{c}"]


def written(rng: random.Random, parts: tuple[str, str, str]) -> str:
    return rng.choice(formats(parts))


def extension(rng: random.Random) -> str:
    return f"{rng.randint(1000, 9999)}"

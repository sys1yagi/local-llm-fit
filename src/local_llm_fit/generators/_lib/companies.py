"""社名の部品。前株・後株・法人格の有無・屋号。

正規化のタスクで使うので、1つの社名に対して
「正しい書き方」と「現場に出てくる崩れた書き方」の両方を作れるようにする。
"""

from __future__ import annotations

import random

BASE = [
    "あおぞら商会", "みどり製作所", "新和システムズ", "青葉物流",
    "つばさデザイン", "山下テクノ", "北斗サービス", "大和電機",
    "ひかり工業", "中央産業", "松風硝子", "寺岡テック",
    "早川精機", "西口ロジ", "南部化成", "東雲メディカル",
    "藤島鋼材", "小暮フーズ", "白岩印刷", "神明トラスト",
    "篠塚エンジ", "湊屋", "五十嵐興業", "音羽情報",
]

# 法人格を前に付けるか後ろに付けるか。社名ごとに固定する。
FRONT, BACK = "front", "back"


def base_name(rng: random.Random) -> str:
    return rng.choice(BASE)


def distinct(rng: random.Random, n: int) -> list[str]:
    return rng.sample(BASE, n)


def canonical(base: str, position: str) -> str:
    """正しい書き方。「株式会社」を漢字で、指定の位置に置く。"""
    return f"株式会社{base}" if position == FRONT else f"{base}株式会社"


def variants(base: str, position: str) -> list[str]:
    """現場に出てくる書き方。正規化するとすべて canonical に落ちる。"""
    marks = ["株式会社", "（株）", "(株)", "㈱"]
    out = []
    for m in marks:
        out.append(f"{m}{base}" if position == FRONT else f"{base}{m}")
    # 法人格と社名の間に空白が入るもの
    out.append(f"㈱ {base}" if position == FRONT else f"{base} ㈱")
    return out


def pick_with_position(rng: random.Random, n: int) -> list[tuple[str, str]]:
    """(社名の本体, 法人格の位置) を n 件。位置は社名ごとに固定する。"""
    return [(b, rng.choice([FRONT, BACK])) for b in distinct(rng, n)]

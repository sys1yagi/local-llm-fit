"""住所の部品。都道府県〜番地、政令市の区、郵便番号、建物名。

伏せ字にするタスクで使うので、1つの住所を「1続きの文字列」として
取り出せるようにする。途中で切れると、どこまでを伏せるかが決まらない。
"""

from __future__ import annotations

import random

# (郵便番号の上3桁, 都道府県, 市区, 町名)
PLACES = [
    ("101", "東京都", "千代田区", "神田小川町"),
    ("105", "東京都", "港区", "芝公園"),
    ("150", "東京都", "渋谷区", "道玄坂"),
    ("220", "神奈川県", "横浜市西区", "北幸"),
    ("530", "大阪府", "大阪市北区", "堂島"),
    ("460", "愛知県", "名古屋市中区", "栄"),
    ("812", "福岡県", "福岡市博多区", "博多駅前"),
    ("060", "北海道", "札幌市中央区", "大通西"),
    ("980", "宮城県", "仙台市青葉区", "一番町"),
    ("600", "京都府", "京都市下京区", "四条通"),
    ("730", "広島県", "広島市中区", "紙屋町"),
    ("330", "埼玉県", "さいたま市大宮区", "桜木町"),
]

BUILDINGS = ["あおぞらビル", "第2中央ビル", "みなとテラス", "新和ビルディング",
             "サンライズ館", "駅前プラザ"]


def town(rng: random.Random) -> tuple[str, str, str, str]:
    return rng.choice(PLACES)


def postal(rng: random.Random, head: str | None = None) -> str:
    head = head or rng.choice(PLACES)[0]
    return f"〒{head}-{rng.randint(0, 9999):04d}"


def street(rng: random.Random) -> str:
    """番地。丁目-番-号。"""
    return f"{rng.randint(1, 9)}-{rng.randint(1, 30)}-{rng.randint(1, 20)}"


def building(rng: random.Random) -> str:
    return f"{rng.choice(BUILDINGS)}{rng.randint(2, 12)}階"


def full(rng: random.Random, with_building: bool = False) -> str:
    """1続きの住所。都道府県から番地まで、間に空白を入れない。"""
    _, pref, city, area = town(rng)
    got = f"{pref}{city}{area}{street(rng)}"
    return f"{got}{building(rng)}" if with_building else got

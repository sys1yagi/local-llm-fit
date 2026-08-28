"""人名の部品。姓名・敬称・読み仮名。"""

from __future__ import annotations

import random

SURNAMES = [
    ("山下", "やました"), ("北村", "きたむら"), ("大和田", "おおわだ"),
    ("篠原", "しのはら"), ("青木", "あおき"), ("中川", "なかがわ"),
    ("藤井", "ふじい"), ("小島", "こじま"), ("森田", "もりた"),
    ("岩瀬", "いわせ"), ("浜口", "はまぐち"), ("柏木", "かしわぎ"),
    ("都築", "つづき"), ("宮下", "みやした"), ("瀬戸", "せと"),
    ("久保", "くぼ"), ("神田", "かんだ"), ("東", "ひがし"),
]

GIVEN = [
    ("直樹", "なおき"), ("彩", "あや"), ("健一", "けんいち"),
    ("千夏", "ちなつ"), ("真由", "まゆ"), ("翔", "しょう"),
    ("美和", "みわ"), ("拓也", "たくや"), ("結衣", "ゆい"),
    ("大介", "だいすけ"), ("志保", "しほ"), ("涼", "りょう"),
]

HONORIFICS = ["さん", "様", ""]


def surname(rng: random.Random) -> str:
    return rng.choice(SURNAMES)[0]


def full(rng: random.Random) -> str:
    return f"{rng.choice(SURNAMES)[0]} {rng.choice(GIVEN)[0]}"


def full_with_kana(rng: random.Random) -> tuple[str, str]:
    s, sk = rng.choice(SURNAMES)
    g, gk = rng.choice(GIVEN)
    return f"{s} {g}", f"{sk} {gk}"


def honorific(rng: random.Random) -> str:
    return rng.choice(HONORIFICS)


def distinct_surnames(rng: random.Random, n: int) -> list[str]:
    return [s for s, _ in rng.sample(SURNAMES, n)]

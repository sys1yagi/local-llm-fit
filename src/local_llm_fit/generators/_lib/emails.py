"""メールアドレスの部品。社内・社外の別。

姓のローマ字から作れるようにしてあるので、本文に出てくる人名と
つながったアドレスを置ける。
"""

from __future__ import annotations

import random

EXTERNAL_DOMAINS = ["example.co.jp", "example.com", "sample-corp.jp",
                    "example.ne.jp", "example.or.jp"]
INTERNAL_DOMAIN = "example-inc.co.jp"

# 姓のローマ字。_lib.people の姓と対応させてある。
SURNAME_ROMAJI = {
    "山下": "yamashita", "北村": "kitamura", "大和田": "owada",
    "篠原": "shinohara", "青木": "aoki", "中川": "nakagawa",
    "藤井": "fujii", "小島": "kojima", "森田": "morita",
    "岩瀬": "iwase", "浜口": "hamaguchi", "柏木": "kashiwagi",
    "都築": "tsuzuki", "宮下": "miyashita", "瀬戸": "seto",
    "久保": "kubo", "神田": "kanda", "東": "higashi",
    "早川": "hayakawa", "篠塚": "shinozuka", "小暮": "kogure",
    "白岩": "shiraiwa", "藤島": "fujishima", "寺岡": "teraoka",
    "五十嵐": "igarashi",
}


def romaji(surname: str) -> str:
    return SURNAME_ROMAJI.get(surname, "tanaka")


def external(rng: random.Random, surname: str | None = None) -> str:
    local = romaji(surname) if surname else rng.choice(list(SURNAME_ROMAJI.values()))
    return f"{local}{rng.randint(1, 99)}@{rng.choice(EXTERNAL_DOMAINS)}"


def internal(rng: random.Random, surname: str | None = None) -> str:
    local = romaji(surname) if surname else rng.choice(list(SURNAME_ROMAJI.values()))
    return f"{local}.{rng.choice('abcdefghijk')}@{INTERNAL_DOMAIN}"

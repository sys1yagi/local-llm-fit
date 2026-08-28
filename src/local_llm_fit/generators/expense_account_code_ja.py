"""経費申請を1件合成する。勘定科目は、渡した規程から一意に決まる。

摘要を見て科目を当てるだけでは足りないようにしてある。
飲食は同席者と1人あたりの金額で分かれ、物品は金額で分かれるので、
規程の条件を当てはめないと正解にならない。
境目ちょうどの金額（1人あたり5,000円、1件10万円）を混ぜている。
"""

from __future__ import annotations

import random

from ._lib import depts, money

MEAL_LIMIT = 5000      # 1人あたりがこの額を超えると交際費
ASSET_LIMIT = 100000   # 1件がこの額以上なら備品費

# (種別, 摘要, 社外の同席)
CASES = [
    ("meal", "取引先との会食", True),
    ("meal", "候補者との懇談会", True),
    ("meal", "協力会社との打ち上げ", True),
    ("meal", "社内定例の弁当代", False),
    ("meal", "部内の打ち合わせ用コーヒー", False),
    ("meal", "残業時の夜食", False),
    ("travel", "新幹線 東京-新大阪 往復", None),
    ("travel", "出張時の宿泊費", None),
    ("travel", "タクシー代（終電後の帰宅）", None),
    ("goods", "ノート型PCの購入", None),
    ("goods", "デスクチェアの購入", None),
    ("goods", "文具の購入", None),
    ("goods", "モニターアームの購入", None),
    ("comm", "携帯電話の基本料", None),
    ("comm", "郵便切手の購入", None),
    ("comm", "回線使用料", None),
    ("book", "業界誌の定期購読", None),
    ("book", "技術書の購入", None),
    ("fee", "銀行の振込手数料", None),
    ("fee", "登記に伴う司法書士報酬", None),
    ("ad", "求人広告の掲載料", None),
    ("ad", "展示会のブース出展料", None),
]

FIXED = {"travel": "旅費交通費", "comm": "通信費", "book": "新聞図書費",
         "fee": "支払手数料", "ad": "広告宣伝費"}


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/eac/truth/{index}")
    kind, note, external = CASES[rng.randrange(len(CASES))]
    dept = depts.division(rng)
    people_count = None

    if kind == "meal":
        people_count = rng.randint(2, 8)
        # 境目ちょうどを3割ほど混ぜる
        if rng.random() < 0.3:
            per_head = MEAL_LIMIT + rng.choice([-1, 0, 1])
        else:
            per_head = money.yen(rng, 1500, 12000, 100)
        amount = per_head * people_count
        account = "交際費" if (external and per_head > MEAL_LIMIT) else "会議費"
    elif kind == "goods":
        if rng.random() < 0.3:
            amount = ASSET_LIMIT + rng.choice([-200, 0, 200])
        else:
            amount = money.yen(rng, 3000, 260000, 100)
        account = "備品費" if amount >= ASSET_LIMIT else "消耗品費"
    else:
        amount = money.yen(rng, 800, 90000, 100)
        account = FIXED[kind]

    return {"kind": kind, "note": note, "external": external, "dept": dept,
            "people": people_count, "amount": amount, "account": account}


FORMATS = [money.comma, money.with_unit, money.yen_mark]


def _render(t: dict, template: int, fmt) -> str:
    attend = ""
    if t["kind"] == "meal":
        who = "あり" if t["external"] else "なし（社内のみ）"
        attend = f"社外の同席: {who}／人数: {t['people']}名"

    if template == 0:
        lines = ["［経費精算申請］",
                 f"申請部署: {t['dept']}",
                 f"摘要: {t['note']}",
                 f"金額: {fmt(t['amount'])}"]
        if attend:
            lines.append(attend)
        return "\n".join(lines)

    lines = [f"{t['dept']}です。下記の経費を精算いたします。",
             "",
             f"・内容: {t['note']}",
             f"・金額: {fmt(t['amount'])}"]
    if attend:
        lines.append(f"・{attend}")
    lines += ["", "ご確認をお願いいたします。"]
    return "\n".join(lines)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, row % 2, FORMATS[row % len(FORMATS)]),
            "truth": {"account": t["account"], "items": []},
        })
    return out

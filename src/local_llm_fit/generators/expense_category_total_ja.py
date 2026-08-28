"""経費の明細を合成し、カテゴリごとの合計を出させる。

カテゴリは明細に書いてあるので、判定は要らない。測るのは加算だけ。
20〜30行を分類しながら足すので、どこかで1件落とすと合計が合わない。

正解はカテゴリごとの合計。行番号によらず同じ。
表の型・金額の書き方・明細の並び順だけを行ごとに変える。
並び順を変えても合計は変わらないので、正解は動かない。
"""

from __future__ import annotations

import random

from ._lib import depts, money
from ._lib import items as items_lib

# 出力するときの並び順。プロンプトにも同じ順で書く。
ORDER = ["旅費交通費", "会議費", "交際費", "消耗品費",
         "通信費", "支払手数料", "新聞図書費", "広告宣伝費"]


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/ect/truth/{index}")
    used = rng.sample(ORDER, rng.randint(4, 6))
    n = rng.randint(20, 30)

    lines = []
    for _ in range(n):
        account = rng.choice(used)
        lines.append({
            "note": items_lib.account_sample(rng, account),
            "account": account,
            "dept": depts.division(rng),
            "amount": money.yen(rng, 800, 180_000, 100),
        })

    totals = {}
    for ln in lines:
        totals[ln["account"]] = totals.get(ln["account"], 0) + ln["amount"]

    return {
        "lines": lines,
        "totals": [{"category": c, "total": totals[c]} for c in ORDER if c in totals],
    }


FORMATS = [money.comma, money.plain, money.with_unit]


def _render(lines: list[dict], template: int, fmt, show_dept: bool) -> str:
    out = []
    if template == 0:
        out.append("No\t科目\t摘要\t部署\t金額" if show_dept else "No\t科目\t摘要\t金額")
        out.append("-" * 60)
        for i, ln in enumerate(lines, 1):
            cells = [str(i), ln["account"], ln["note"]]
            if show_dept:
                cells.append(ln["dept"])
            cells.append(fmt(ln["amount"]))
            out.append("\t".join(cells))
    else:
        out.append("【経費明細】")
        for i, ln in enumerate(lines, 1):
            dept = f"（{ln['dept']}）" if show_dept else ""
            out.append(f"{i}. [{ln['account']}] {ln['note']}{dept} … {fmt(ln['amount'])}")
    return "\n".join(out)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        rng = random.Random(f"{seed}/ect/surface/{i}/{row}")
        shuffled = list(t["lines"])
        rng.shuffle(shuffled)
        out.append({
            "id": f"{i:03d}",
            "input": _render(shuffled, (i + row) % 2,
                             FORMATS[(i + row) % len(FORMATS)],
                             (i + row) % 2 == 0),
            "truth": {"items": t["totals"]},
        })
    return out

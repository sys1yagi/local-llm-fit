"""銀行の取引明細を合成し、全行を構造化させる。

難所は2つ。振込人の名前が摘要欄の中に他の語と一緒に入っているので、
行から名前だけを取り出す必要がある。入金と出金は別の列に書かれるので、
出金を負の数にして1つの項目にまとめ直す必要がある。

正解は全行の日付・金額・相手先。行番号によらず同じ。
表の型・日付と金額の書き方・摘要の飾り語だけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import companies, dates, money, people

# 摘要欄で名前の前後に付く語。名前そのものではない。
PREFIX_IN = ["振込", "フリコミ", "入金", "口座振替", "ATM振込"]
PREFIX_OUT = ["振込", "支払", "自動引落", "カード決済", "ATM出金"]
SUFFIX = ["", " 手数料込", " 取扱", " 定期", " 当月分", " ﾃｽｳﾘｮｳ"]


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/bs/truth/{index}")
    n = rng.randint(8, 10)
    start = dates.pick(rng, months=(1, 11)).replace(day=1)

    names = [companies.canonical(b, p)
             for b, p in companies.pick_with_position(rng, min(12, n))]
    names += [people.full(rng) for _ in range(4)]

    rows = []
    day = 0
    for _ in range(n):
        day += rng.randint(1, 3)
        d = dates.add_days(start, min(day, 27))
        incoming = rng.random() < 0.55
        amount = money.yen(rng, 3_000, 900_000, 1_000)
        rows.append({
            "date": dates.iso(d),
            "raw_date": d,
            "incoming": incoming,
            "abs_amount": amount,
            "amount": amount if incoming else -amount,
            "counterparty": rng.choice(names),
        })
    return {"rows": rows}


DATE_FORMATS = [dates.slash, dates.md, dates.dot]
MONEY_FORMATS = [money.comma, money.plain]


def _render(t: dict, template: int, dfmt, mfmt, rng: random.Random) -> str:
    # 日付が月日だけで書かれることがあるので、対象の年月を見出しに出す
    first = t["rows"][0]["raw_date"]
    out = [f"口座取引明細　{first.year}年{first.month}月分", ""]
    if template == 0:
        out.append("日付\t摘要\t入金\t出金")
        out.append("-" * 70)
        for r in t["rows"]:
            pre = rng.choice(PREFIX_IN if r["incoming"] else PREFIX_OUT)
            note = f"{pre} {r['counterparty']}{rng.choice(SUFFIX)}"
            cells = [dfmt(r["raw_date"]), note]
            cells += ([mfmt(r["abs_amount"]), ""] if r["incoming"]
                      else ["", mfmt(r["abs_amount"])])
            out.append("\t".join(cells))
    else:
        out.append("【入出金明細】")
        for r in t["rows"]:
            pre = rng.choice(PREFIX_IN if r["incoming"] else PREFIX_OUT)
            note = f"{pre} {r['counterparty']}{rng.choice(SUFFIX)}"
            kind = "入金" if r["incoming"] else "出金"
            out.append(f"{dfmt(r['raw_date'])}  {note}  [{kind}] {mfmt(r['abs_amount'])}")
    return "\n".join(out)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        rng = random.Random(f"{seed}/bs/surface/{i}/{row}")
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, (i + row) % 2,
                             DATE_FORMATS[(i + row) % len(DATE_FORMATS)],
                             MONEY_FORMATS[(i + row) % len(MONEY_FORMATS)], rng),
            "truth": {
                "items": [{"date": r["date"], "amount": r["amount"],
                           "counterparty": r["counterparty"]} for r in t["rows"]],
            },
        })
    return out

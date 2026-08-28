"""取引先リストを合成する。社名の書き方だけが崩れている。

正解は「正しい書き方に直した全文」。先に正しい全文を作り、そこから
社名の表記だけを崩して入力の文面にする。崩し方は行ごとに引き直すので、
同じ正解に対して行ごとに別の文面が出る。

崩すのは法人格の書き方（株式会社 / （株）/ (株) / ㈱ と、間の空白）だけで、
社名の本体・担当者名・並び順・ラベルは触らない。
"""

from __future__ import annotations

import random

from ._lib import companies, people

ROWS = 5


def _truth(seed: int, index: int) -> dict:
    """正しい書き方の取引先リスト。行番号によらず同じ。"""
    rng = random.Random(f"{seed}/cnn/truth/{index}")
    picked = companies.pick_with_position(rng, ROWS)
    return {
        "template": index % 2,
        "records": [
            {
                "base": base,
                "position": pos,
                "name": companies.canonical(base, pos),
                "owner": people.full(rng),
            }
            for base, pos in picked
        ],
    }


def _render(records: list[dict], template: int, names: list[str]) -> str:
    lines = []
    if template == 0:
        lines.append("【取引先一覧】")
        for n, (r, name) in enumerate(zip(records, names), 1):
            lines.append(f"・取引先{n}: {name}（担当: {r['owner']}）")
    else:
        lines.append("取引先\t担当")
        lines.append("-" * 40)
        for r, name in zip(records, names):
            lines.append(f"{name}\t{r['owner']}")
    return "\n".join(lines)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        # 崩し方の組み合わせを行番号から桁上がりで決める。
        # 乱数で選ぶと行どうしで同じ組み合わせを引くことがあり、
        # 同じ文面を投げ直すことになってしまう。
        rng = random.Random(f"{seed}/cnn/surface/{i}")
        written = []
        for k, r in enumerate(t["records"]):
            forms = companies.variants(r["base"], r["position"])
            base = rng.randrange(len(forms))
            written.append(forms[(base + row // len(forms) ** k) % len(forms)])

        correct = [r["name"] for r in t["records"]]
        out.append({
            "id": f"{i:03d}",
            "input": _render(t["records"], t["template"], written),
            "truth": {
                "text": _render(t["records"], t["template"], correct),
                "items": [],
            },
        })
    return out

"""明細表を合成し、一部の金額をわざと間違える。

検算は紙に書かれている値だけで閉じるようにする。
  明細行 … 数量 × 単価 が金額と合うか
  小計   … 明細の金額の合計と合うか
  消費税 … 小計の10%（1円未満切り捨て）と合うか
  合計   … 小計 + 消費税 と合うか
明細の金額を崩した場合でも、小計は「紙に書かれた金額の合計」で印字するので、
どの行が誤りかは一意に決まる。

正解は「誤っている行と、そこに入るべき値」。行番号によらず同じ。
文面の型と数字の書き方だけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import items as items_lib
from ._lib import money

TAX_LABEL = "消費税"
SUBTOTAL_LABEL = "小計"
TOTAL_LABEL = "合計"


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/lta/truth/{index}")
    n = rng.randint(4, 7)
    lines = []
    for name, unit_price in items_lib.mixed(rng, n):
        qty = rng.randint(1, 20) if unit_price < 5000 else rng.randint(1, 4)
        lines.append({"name": name, "qty": qty, "unit_price": unit_price,
                      "amount": qty * unit_price})

    # 崩す場所を選ぶ。0〜2箇所。
    spots = [str(i) for i in range(1, n + 1)] + [SUBTOTAL_LABEL, TAX_LABEL, TOTAL_LABEL]
    n_bad = rng.choices([0, 1, 2], weights=[3, 5, 2])[0]
    broken = set(rng.sample(spots, n_bad))

    def skew(v: int) -> int:
        """桁の入れ違い・端数の切り上げ・単純な足し間違いのどれかを起こす。

        必ず元の値と違い、かつ負にならないようにする。
        """
        kind = rng.choice(["digit", "round", "off"])
        if kind == "digit" and v >= 1000:
            return v * 10 if rng.random() < 0.5 else v // 10
        if kind == "round":
            return v + (10 - v % 10 if v % 10 else 7)
        choices = [100, 1000] if v < 2000 else [-1000, -100, 100, 1000]
        return v + rng.choice(choices)

    printed = []
    for i, ln in enumerate(lines, 1):
        shown = skew(ln["amount"]) if str(i) in broken else ln["amount"]
        printed.append({**ln, "shown": shown})

    sum_shown = sum(p["shown"] for p in printed)
    subtotal_shown = skew(sum_shown) if SUBTOTAL_LABEL in broken else sum_shown
    tax_right = int(subtotal_shown * money.TAX_RATE)
    tax_shown = skew(tax_right) if TAX_LABEL in broken else tax_right
    total_right = subtotal_shown + tax_shown
    total_shown = skew(total_right) if TOTAL_LABEL in broken else total_right

    wrong = []
    for i, p in enumerate(printed, 1):
        if p["shown"] != p["amount"]:
            wrong.append({"row": str(i), "correct": p["amount"]})
    if subtotal_shown != sum_shown:
        wrong.append({"row": SUBTOTAL_LABEL, "correct": sum_shown})
    if tax_shown != tax_right:
        wrong.append({"row": TAX_LABEL, "correct": tax_right})
    if total_shown != total_right:
        wrong.append({"row": TOTAL_LABEL, "correct": total_right})

    return {
        "lines": printed,
        "subtotal": subtotal_shown,
        "tax": tax_shown,
        "total": total_shown,
        "wrong": wrong,
    }


FORMATS = [money.comma, money.plain, money.yen_mark]


def _render(t: dict, template: int, fmt) -> str:
    lines_out = []
    if template == 0:
        lines_out.append("No  品名                              数量      単価        金額")
        lines_out.append("-" * 66)
        for i, p in enumerate(t["lines"], 1):
            lines_out.append(
                f"{i:<4}{p['name']:<32}{p['qty']:>4}{fmt(p['unit_price']):>11}{fmt(p['shown']):>13}")
        lines_out.append("-" * 66)
        for label, v in ((SUBTOTAL_LABEL, t["subtotal"]), (TAX_LABEL, t["tax"]),
                         (TOTAL_LABEL, t["total"])):
            lines_out.append(f"{label:>50}{fmt(v):>13}")
    else:
        lines_out.append("【ご請求明細】")
        for i, p in enumerate(t["lines"], 1):
            lines_out.append(
                f"({i}) {p['name']} / 数量 {p['qty']} / 単価 {fmt(p['unit_price'])} "
                f"/ 金額 {fmt(p['shown'])}")
        lines_out.append("")
        lines_out.append(f"{SUBTOTAL_LABEL} {fmt(t['subtotal'])}")
        lines_out.append(f"{TAX_LABEL} {fmt(t['tax'])}")
        lines_out.append(f"{TOTAL_LABEL} {fmt(t['total'])}")
    return "\n".join(lines_out)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        # 型と数字の書き方の組み合わせを行番号から決める。乱数だと行どうしで
        # 同じ組み合わせを引くことがある。
        template = row % 2
        fmt = FORMATS[row % len(FORMATS)]
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, template, fmt),
            "truth": {"items": t["wrong"]},
        })
    return out

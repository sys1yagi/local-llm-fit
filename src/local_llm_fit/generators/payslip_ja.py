"""給与明細を合成する。

先に金額を決めて明細を組み立てるので、書かれている数字と正解が必ず合う。
控除は正解では負の数に統一し、文面ではその月の書き方で書く。

行ごとに変えるのは表層だけ。
  - 項目の呼び名（残業手当 / 超過勤務手当 のような揺れ）
  - 控除の書き方（18,458 / ▲18,458 / (18,458) / -18,458）
  - 対象月の書き方（2026年6月分 / 2026/06 / 令和8年6月度）
  - 明細の型（表 / 1行）
どれも (サンプル番号 + 行番号) で回すので、1行の中の構成比はどの行でも
同じになる。行によって難しい書き方が偏ることがない。

難所は2つ。呼び名の揺れを決められた項目名に寄せること、
控除を負の数に直すこと。文面では正の数で書かれていることの方が多い。
"""

from __future__ import annotations

import random

from ._lib import dates, depts, money, people

# 正解で使う項目名と、文面に出てくる呼び名。先頭が正解の表記。
PAYMENTS = {
    "基本給": ["基本給", "基準内給与", "本給"],
    "役職手当": ["役職手当", "職位手当", "管理職手当"],
    "時間外手当": ["時間外手当", "残業手当", "超過勤務手当"],
    "住宅手当": ["住宅手当", "家賃補助", "住居手当"],
    "通勤手当": ["通勤手当", "交通費", "通勤費"],
}
DEDUCTIONS = {
    "健康保険料": ["健康保険料", "健保", "健康保険"],
    "厚生年金保険料": ["厚生年金保険料", "厚生年金", "厚年"],
    "雇用保険料": ["雇用保険料", "雇用保険", "雇保"],
    "所得税": ["所得税", "源泉所得税", "源泉税"],
    "住民税": ["住民税", "市県民税", "特別徴収住民税"],
}

TITLES = ["給与支給明細書", "給与明細書", "給 与 明 細", "給与明細"]

HEALTH_RATE = 0.0499
PENSION_RATE = 0.0915
EMPLOYMENT_RATE = 0.006
INCOME_TAX_RATE = 0.0511


def _truth(seed: int, index: int) -> dict:
    """正解。(seed, サンプル番号) だけで決まるので、行番号によらず同じ。"""
    rng = random.Random(f"{seed}/payslip/truth/{index}")

    base = money.yen(rng, 220_000, 480_000, 1000)
    pays = [("基本給", base)]
    if rng.random() < 0.6:
        pays.append(("役職手当", money.yen(rng, 15_000, 60_000, 5000)))
    hourly = int(base / 160 * 1.25)
    pays.append(("時間外手当", hourly * rng.randint(1, 40)))
    if rng.random() < 0.5:
        pays.append(("住宅手当", money.yen(rng, 10_000, 30_000, 5000)))
    pays.append(("通勤手当", money.yen(rng, 6_000, 35_000, 10)))

    total_payment = sum(a for _, a in pays)
    health = int(total_payment * HEALTH_RATE)
    pension = int(total_payment * PENSION_RATE)
    employment = int(total_payment * EMPLOYMENT_RATE)
    taxable = total_payment - health - pension - employment
    deducts = [
        ("健康保険料", health),
        ("厚生年金保険料", pension),
        ("雇用保険料", employment),
        ("所得税", int(taxable * INCOME_TAX_RATE)),
        ("住民税", money.yen(rng, 8_000, 40_000, 100)),
    ]
    total_deduction = sum(a for _, a in deducts)

    month = dates.pick(rng, months=(1, 12))
    items = [{"name": n, "amount": a} for n, a in pays]
    items += [{"name": n, "amount": -a} for n, a in deducts]
    return {
        "employee": people.full(rng),
        "pay_month": f"{month.year}-{month.month:02d}",
        "items": items,
        "total_payment": total_payment,
        "total_deduction": total_deduction,
        "net_payment": total_payment - total_deduction,
        # 正解には入らないが、文面を書くのに要るもの
        "_year": month.year,
        "_month": month.month,
        "_dept": depts.with_section(rng),
        "_employee_no": f"{rng.randint(10000, 99999)}",
    }


def _month_written(t: dict, turn: int) -> str:
    if turn == 0:
        return f"{t['_year']}年{t['_month']}月分"
    if turn == 1:
        return f"{t['_year']}/{t['_month']:02d}"
    era = t["_year"] - dates.REIWA_ORIGIN
    return f"令和{era}年{t['_month']}月度"


def _label(names: dict[str, list[str]], canonical: str, turn: int) -> str:
    forms = names[canonical]
    return forms[turn % len(forms)]


def _deduction_written(amount: int, turn: int) -> str:
    """控除の書き方。指す額はどれも同じ。"""
    plain = money.comma(amount)
    return [plain, f"▲{plain}", f"({plain})", f"-{plain}"][turn % 4]


def _rows(t: dict, turn: int) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    pays, deducts = [], []
    for n, item in enumerate(t["items"]):
        amount = item["amount"]
        if amount >= 0:
            pays.append((_label(PAYMENTS, item["name"], turn + n),
                         money.comma(amount)))
        else:
            deducts.append((_label(DEDUCTIONS, item["name"], turn + n),
                            _deduction_written(-amount, turn)))
    return pays, deducts


def _render_table(t: dict, turn: int) -> str:
    pays, deducts = _rows(t, turn)
    lines = [
        f"{TITLES[turn % len(TITLES)]:^30}",
        "",
        (f"対象月: {_month_written(t, turn % 3)}"
         f"        社員番号: {t['_employee_no']}"),
        f"氏名: {t['employee']} 様        所属: {t['_dept']}",
        "",
        "【支給】",
    ]
    lines += [f"  {label:<16}{value:>12}" for label, value in pays]
    lines.append(f"  {'支給合計':<16}{money.comma(t['total_payment']):>12}")
    lines += ["", "【控除】"]
    lines += [f"  {label:<16}{value:>12}" for label, value in deducts]
    lines.append(f"  {'控除合計':<16}"
                 f"{_deduction_written(t['total_deduction'], turn):>12}")
    lines += ["", f"  {'差引支給額':<16}{money.comma(t['net_payment']):>12}"]
    return "\n".join(lines)


def _render_lines(t: dict, turn: int) -> str:
    pays, deducts = _rows(t, turn)
    pay_text = " / ".join(f"{label}={value}" for label, value in pays)
    ded_text = " / ".join(f"{label}={value}" for label, value in deducts)
    return "\n".join([
        f"{TITLES[turn % len(TITLES)]}  {_month_written(t, turn % 3)}",
        f"氏名 {t['employee']}（{t['_dept']}） 社員番号 {t['_employee_no']}",
        "",
        f"支給: {pay_text}",
        f"   支給合計 {money.comma(t['total_payment'])}",
        f"控除: {ded_text}",
        f"   控除合計 {_deduction_written(t['total_deduction'], turn)}",
        "",
        f"差引支給額 {money.comma(t['net_payment'])}",
    ])


RENDERERS = [_render_table, _render_lines]


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        turn = i + row
        render = RENDERERS[turn % len(RENDERERS)]
        truth = {k: v for k, v in t.items() if not k.startswith("_")}
        out.append({
            "id": f"{i:03d}",
            "input": render(t, turn),
            "truth": truth,
        })
    return out

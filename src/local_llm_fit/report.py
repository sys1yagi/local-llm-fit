"""同時実行数ごとの結果表を作る。

各行は「その同時実行数で測ったときの応答時間と正答率」で、
判定の列にはタスク定義に書いた基準のうち、どれを割ったかを書く。
"""

from __future__ import annotations

import math

# 95%区間に使う標準正規分布の値
Z_95 = 1.959963984540054

VERDICT_OK = "基準を満たす"
VERDICT_SLOW = "応答が遅い"
VERDICT_LOW_ACCURACY = "正答率が足りない"
VERDICT_BOTH = "正答率・応答とも足りない"
VERDICT_ERROR = "エラーが出た"


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """正答率の95%区間（Wilsonスコア区間）。

    件数が少ないと正答率は粗くなる。48件なら1件が約2ポイント、12件なら8ポイント。
    「基準を割った」と読める行が、実は件数不足で判断できないだけなのかを
    見分けるために添える。閉じた式なので追加の依存も乱数も要らない。
    """
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def percentile(values: list[float], q: float) -> float | None:
    """最近傍順位法。値が少ないときに補間で嘘の滑らかさを出さない。"""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = max(1, round(q * len(vals)))
    return vals[min(k, len(vals)) - 1]


def summarize_level(level: dict, graded: list[dict], slo: dict) -> dict:
    calls = level["calls"]
    n = len(calls)
    errors = [c for c in calls if c.error]
    ok_calls = [c for c in calls if not c.error]

    ttfts = [c.ttft_s for c in ok_calls if c.ttft_s is not None]
    e2es = [c.e2e_s for c in ok_calls if c.e2e_s is not None]
    total_out = sum(c.output_tokens for c in ok_calls)

    passed = sum(1 for g in graded if g["ok"])
    pass_rate = passed / n if n else 0.0
    error_rate = len(errors) / n if n else 0.0

    row = {
        "concurrency": level["concurrency"],
        "requests": n,
        "wall_s": round(level["wall_s"], 2),
        "ttft_p50_s": _r(percentile(ttfts, 0.50)),
        "ttft_p95_s": _r(percentile(ttfts, 0.95)),
        "e2e_p50_s": _r(percentile(e2es, 0.50)),
        "e2e_p95_s": _r(percentile(e2es, 0.95)),
        "output_tokens": total_out,
        "throughput_tok_s": _r(total_out / level["wall_s"] if level["wall_s"] else 0),
        "pass_rate": round(pass_rate, 3),
        "passed": passed,
        "error_rate": round(error_rate, 3),
        "errors": len(errors),
    }
    lo, hi = wilson_interval(passed, n)
    row["pass_rate_lo"] = round(lo, 3)
    row["pass_rate_hi"] = round(hi, 3)
    row["verdict"] = verdict(row, slo)
    # 点推定では基準を割っているが、区間の上端は基準を超えている行。
    # 「足りない」と断定するには件数が足りない。
    row["accuracy_inconclusive"] = (
        row["verdict"] in (VERDICT_LOW_ACCURACY, VERDICT_BOTH)
        and hi >= slo.get("pass_rate", 1.0)
    )
    return row


def _r(v):
    return None if v is None else round(v, 3)


def verdict(row: dict, slo: dict) -> str:
    """どの基準を割ったのかを、そのまま言葉にして返す。

    正答率と応答時間は落ちる理由が違う。ひとまとめの判定にすると、
    モデルを替えるべきなのか機材を足すべきなのかが読めなくなる。
    """
    low_accuracy = row["pass_rate"] < slo.get("pass_rate", 1.0)
    over_ttft = row["ttft_p95_s"] is not None and row["ttft_p95_s"] > slo.get("ttft_p95_s", 1e9)
    over_e2e = row["e2e_p95_s"] is not None and row["e2e_p95_s"] > slo.get("e2e_p95_s", 1e9)
    slow = over_ttft or over_e2e

    if row["error_rate"] > slo.get("error_rate", 0.0):
        return VERDICT_ERROR
    if low_accuracy and slow:
        return VERDICT_BOTH
    if low_accuracy:
        return VERDICT_LOW_ACCURACY
    if slow:
        return VERDICT_SLOW
    return VERDICT_OK


def judge_levels(rows: list[dict], slo: dict) -> tuple[list[int], list[int]]:
    """基準に照らして、同時本数を2つに仕分ける。

    返すのは (満たした本数, 判断できない本数)。
    2つめは、応答時間は基準内で、正答率の点推定は基準を割っているものの、
    95%区間の上端が基準を超えている行（表の `※`）。件数が足りないだけで
    実は満たしているかもしれないので、満たしたとは数えず別に見せる。

    判定は測ったときの基準ではなく、渡した基準でやり直す。
    タスク定義の `slo` はあとから書き換わることがあり、
    いま並べて比べるなら同じ物差しを当てる必要があるため。
    """
    met: list[int] = []
    unsure: list[int] = []
    for row in rows:
        got = verdict(row, slo)
        if got == VERDICT_OK:
            met.append(row["concurrency"])
        elif (got == VERDICT_LOW_ACCURACY
              and row.get("pass_rate_hi") is not None
              and row["pass_rate_hi"] >= slo.get("pass_rate", 1.0)):
            unsure.append(row["concurrency"])
    return met, unsure


def to_markdown(rows: list[dict]) -> str:
    head = ("| 同時に投げた本数 | 最初の文字が出るまで | 返り終わるまで | 1秒あたりの生成量 | 正答率（95%区間） | 判定 |\n"
            "|---:|---:|---:|---:|---:|:--|")
    lines = [head]
    for r in rows:
        mark = " ※" if r.get("accuracy_inconclusive") else ""
        lines.append(
            f"| {r['concurrency']} "
            f"| {_s(r['ttft_p95_s'])} | {_s(r['e2e_p95_s'])} "
            f"| {r['throughput_tok_s']:.0f} トークン "
            f"| {r['passed']}/{r['requests']} {r['pass_rate'] * 100:.0f}% "
            f"({r['pass_rate_lo'] * 100:.0f}〜{r['pass_rate_hi'] * 100:.0f}%) "
            f"| {r['verdict']}{mark} |"
        )
    lines.append("")
    if rows:
        n = rows[0]["requests"]
        rank = n - max(1, round(0.95 * n)) + 1
        lines.append(f"時間はいずれも p95（{n}件のうち遅い方から{rank}件目の値）。")
    if any(r.get("accuracy_inconclusive") for r in rows):
        lines.append("※ 正答率の95%区間の上端が基準を超えている行。"
                     "基準を割ったと断定するには件数が足りない。")
    return "\n".join(lines)


def _s(v) -> str:
    return "-" if v is None else f"{v:.2f}秒"


def max_ok_concurrency(rows: list[dict]) -> int | None:
    """基準をすべて満たした最大の同時実行数。"""
    ok = [r["concurrency"] for r in rows if r["verdict"] == VERDICT_OK]
    return max(ok) if ok else None

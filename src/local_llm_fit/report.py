"""同時実行数ごとの結果表を作る。

各行は「その同時実行数で測ったときの応答時間と正答率」で、
判定の列にはタスク定義に書いた基準のうち、どれを割ったかを書く。
"""

from __future__ import annotations

VERDICT_OK = "基準を満たす"
VERDICT_SLOW = "応答が遅い"
VERDICT_LOW_ACCURACY = "正答率が足りない"
VERDICT_BOTH = "正答率・応答とも足りない"
VERDICT_ERROR = "エラーが出た"


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
    row["verdict"] = _verdict(row, slo)
    return row


def _r(v):
    return None if v is None else round(v, 3)


def _verdict(row: dict, slo: dict) -> str:
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


def to_markdown(rows: list[dict]) -> str:
    head = ("| 同時に投げた本数 | 最初の文字が出るまで | 返り終わるまで | 1秒あたりの生成量 | 正答率 | 判定 |\n"
            "|---:|---:|---:|---:|---:|:--|")
    lines = [head]
    for r in rows:
        lines.append(
            f"| {r['concurrency']} "
            f"| {_s(r['ttft_p95_s'])} | {_s(r['e2e_p95_s'])} "
            f"| {r['throughput_tok_s']:.0f} トークン "
            f"| {r['passed']}/{r['requests']} ({r['pass_rate'] * 100:.0f}%) "
            f"| {r['verdict']} |"
        )
    lines.append("")
    if rows:
        n = rows[0]["requests"]
        rank = n - max(1, round(0.95 * n)) + 1
        lines.append(f"時間はいずれも p95（{n}件のうち遅い方から{rank}件目の値）。")
    return "\n".join(lines)


def _s(v) -> str:
    return "-" if v is None else f"{v:.2f}秒"


def max_ok_concurrency(rows: list[dict]) -> int | None:
    """基準をすべて満たした最大の同時実行数。"""
    ok = [r["concurrency"] for r in rows if r["verdict"] == VERDICT_OK]
    return max(ok) if ok else None

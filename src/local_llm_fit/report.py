"""判定マトリクスを作る。

同時実行数ごとに「応答時間」と「品質の合格率」を並べ、
タスク定義に書いた合否の線に照らして 載る / 応答遅延 / 載らない を出す。
"""

from __future__ import annotations

VERDICT_FIT = "載る"
VERDICT_SLOW = "応答遅延"
VERDICT_LOW_QUALITY = "品質不足"
VERDICT_UNFIT = "載らない"


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
    """どの線を割ったのかが分かる形で返す。

    品質と応答時間は別の理由で落ちる。まとめて「載らない」にすると、
    モデルを替えるべきなのか機材を足すべきなのかが読めなくなる。
    """
    low_quality = row["pass_rate"] < slo.get("pass_rate", 1.0)
    over_ttft = row["ttft_p95_s"] is not None and row["ttft_p95_s"] > slo.get("ttft_p95_s", 1e9)
    over_e2e = row["e2e_p95_s"] is not None and row["e2e_p95_s"] > slo.get("e2e_p95_s", 1e9)
    slow = over_ttft or over_e2e

    if row["error_rate"] > slo.get("error_rate", 0.0):
        return VERDICT_UNFIT
    if low_quality and slow:
        return VERDICT_UNFIT
    if low_quality:
        return VERDICT_LOW_QUALITY
    if slow:
        return VERDICT_SLOW
    return VERDICT_FIT


def to_markdown(rows: list[dict]) -> str:
    head = ("| 同時実行 | TTFT p50 | TTFT p95 | 応答完了 p95 | スループット | 合格率 | エラー | 判定 |\n"
            "|---:|---:|---:|---:|---:|---:|---:|:--|")
    lines = [head]
    for r in rows:
        lines.append(
            f"| {r['concurrency']} "
            f"| {_s(r['ttft_p50_s'])} | {_s(r['ttft_p95_s'])} | {_s(r['e2e_p95_s'])} "
            f"| {r['throughput_tok_s']:.1f} tok/s "
            f"| {r['pass_rate'] * 100:.0f}% ({r['passed']}/{r['requests']}) "
            f"| {r['errors']} "
            f"| {r['verdict']} |"
        )
    return "\n".join(lines)


def _s(v) -> str:
    return "-" if v is None else f"{v:.2f}s"


def max_fit_concurrency(rows: list[dict]) -> int | None:
    """判定が「載る」で通った最大の同時実行数。"""
    fits = [r["concurrency"] for r in rows if r["verdict"] == VERDICT_FIT]
    return max(fits) if fits else None

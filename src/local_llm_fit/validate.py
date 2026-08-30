"""持ち寄られた結果JSONを点検する。

見るのは3つ。
  1. 形（必要なキーがあり、型が合っているか）
  2. タスクの version が、いま手元にあるタスク定義と同じか
  3. 数字が辻褄の合う範囲にあるか（正答数≦件数、時間が負でない、等）

**見つけても落としません。** 結果は測った人の環境で1回きり得られたもので、
こちらの点検で弾くと測り直しを強いることになります。おかしな点は
警告として並べるだけにして、読む人が事情を判断できるようにします。

version の無い旧形式は、version の照合だけ飛ばして点検します。
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

LEVEL_SCHEMA = {
    "type": "object",
    "required": ["concurrency", "requests", "passed", "pass_rate", "errors"],
    "properties": {
        "concurrency": {"type": "integer", "minimum": 1},
        "requests": {"type": "integer", "minimum": 1},
        "passed": {"type": "integer", "minimum": 0},
        "errors": {"type": "integer", "minimum": 0},
        "pass_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "error_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "pass_rate_lo": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "pass_rate_hi": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "wall_s": {"type": "number", "minimum": 0},
        "ttft_p50_s": {"type": ["number", "null"], "minimum": 0},
        "ttft_p95_s": {"type": ["number", "null"], "minimum": 0},
        "e2e_p50_s": {"type": ["number", "null"], "minimum": 0},
        "e2e_p95_s": {"type": ["number", "null"], "minimum": 0},
        "output_tokens": {"type": "integer", "minimum": 0},
        "throughput_tok_s": {"type": "number", "minimum": 0},
        "timeouts": {"type": "integer", "minimum": 0},
        "empty_responses": {"type": "integer", "minimum": 0},
        "verdict": {"type": "string"},
    },
}

RESULT_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "run_id", "measured_at", "task", "model",
                 "slo", "levels"],
    "properties": {
        "schema_version": {"type": "integer", "minimum": 1},
        "run_id": {"type": "string", "minLength": 1},
        "measured_at": {"type": "string", "minLength": 1},
        "model": {"type": "string", "minLength": 1},
        "endpoint": {"type": "string"},
        "server_label": {"type": ["string", "null"]},
        "max_ok_concurrency": {"type": ["integer", "null"]},
        "task": {
            "type": "object",
            "required": ["name", "samples_per_level", "seed"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "file": {"type": "string"},
                "version": {"type": ["integer", "null"], "minimum": 1},
                "samples_per_level": {"type": "integer", "minimum": 1},
                "seed": {"type": "integer"},
            },
        },
        "environment": {
            "type": "object",
            "properties": {
                "server": {"type": "string"},
                "quantization": {"type": "string"},
                "server_concurrency": {"type": "string"},
                "power": {"type": "string"},
                "request_timeout_s": {"type": ["number", "null"], "minimum": 0},
            },
        },
        "slo": {
            "type": "object",
            "properties": {
                "pass_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "ttft_p95_s": {"type": "number", "minimum": 0},
                "e2e_p95_s": {"type": "number", "minimum": 0},
                "error_rate": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "levels": {"type": "array", "minItems": 1, "items": LEVEL_SCHEMA},
    },
}


def _task_version(tasks_dir: Path, summary: dict) -> tuple[int | None, str]:
    """いまのタスク定義の version と、読んだファイル名。"""
    task = summary.get("task") or {}
    name = task.get("file") or f"{task.get('name')}.yaml"
    path = tasks_dir / name
    if not path.exists():
        return None, name
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None, name
    return loaded.get("version"), name


def _check_numbers(summary: dict) -> list[str]:
    out = []
    for row in summary.get("levels") or []:
        head = f"同時{row.get('concurrency')}本"
        n = row.get("requests")
        if not isinstance(n, int) or n < 1:
            continue
        passed = row.get("passed")
        if isinstance(passed, int) and passed > n:
            out.append(f"{head}: 正答 {passed}件が件数 {n}件を超えています")
        errors = row.get("errors")
        if isinstance(errors, int) and errors > n:
            out.append(f"{head}: エラー {errors}件が件数 {n}件を超えています")
        rate = row.get("pass_rate")
        if isinstance(passed, int) and isinstance(rate, int | float) \
                and abs(rate - passed / n) > 0.01:
            out.append(f"{head}: 正答率 {rate} が {passed}/{n} と合いません")
        lo, hi = row.get("pass_rate_lo"), row.get("pass_rate_hi")
        if isinstance(lo, int | float) and isinstance(hi, int | float) and lo > hi:
            out.append(f"{head}: 95%区間の下端 {lo} が上端 {hi} を上回っています")
        ttft, e2e = row.get("ttft_p95_s"), row.get("e2e_p95_s")
        if isinstance(ttft, int | float) and isinstance(e2e, int | float) and ttft > e2e:
            out.append(f"{head}: 最初の文字まで {ttft}秒 が"
                       f" 返り終わるまで {e2e}秒 を上回っています")
        wall = row.get("wall_s")
        if isinstance(wall, int | float) and wall <= 0:
            out.append(f"{head}: かかった時間が {wall}秒 になっています")

    levels = [r.get("concurrency") for r in summary.get("levels") or []]
    if len(set(levels)) != len(levels):
        out.append("同じ同時本数の行が複数あります")

    counts = {r.get("requests") for r in summary.get("levels") or []}
    if len(counts) > 1:
        out.append(f"行ごとに件数が違います（{sorted(c for c in counts if c)}）。"
                   "行をまたいで正答率を比べられません")
    return out


def check(summary: dict, tasks_dir: Path) -> list[str]:
    """点検して、警告の文言を並べて返す。問題が無ければ空。"""
    out: list[str] = []
    try:
        jsonschema.validate(summary, RESULT_SCHEMA)
    except jsonschema.ValidationError as e:
        where = "/".join(str(p) for p in e.absolute_path) or "（最上位）"
        return [f"形が合っていません: {where}: {e.message}"]

    recorded = (summary.get("task") or {}).get("version")
    current, filename = _task_version(tasks_dir, summary)
    if recorded is None:
        pass  # version を刻む前の旧形式。照合しない
    elif current is None:
        out.append(f"tasks/{filename} が見つからないか version がありません。"
                   f"結果には version {recorded} が入っています")
    elif recorded != current:
        out.append(f"タスクの version が違います（結果 {recorded} / "
                   f"いまの tasks/{filename} は {current}）。"
                   "生成器・採点・指示文のどれかが変わっているので、"
                   "この結果は他の測定と並べて比べられません")

    out += _check_numbers(summary)
    return out


def check_file(path: Path, tasks_dir: Path) -> list[str]:
    if not path.exists():
        return ["ファイルが見つかりません"]
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"JSONとして読めません: {e}"]
    if not isinstance(summary, dict):
        return ["JSONの最上位がオブジェクトではありません"]
    return check(summary, tasks_dir)

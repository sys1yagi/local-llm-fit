"""採点。決定論的に合否を出す。LLMには採点させない。

1件が合格になるのは、次の3つをすべて満たしたときだけ。
  1. 応答から JSON が取り出せる
  2. スキーマを満たす
  3. 採点対象の値がすべて正解と一致する
"""

from __future__ import annotations

import json
import re
from typing import Any

import jsonschema

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> tuple[dict | None, str | None]:
    """応答本文から JSON を1つ取り出す。取れなければ理由を返す。"""
    if not text or not text.strip():
        return None, "empty_response"

    candidates = []
    for m in FENCE.finditer(text):
        candidates.append(m.group(1))
    # コードブロックが無い場合は、最初の { から最後の } までを見る
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])

    for c in candidates:
        try:
            parsed = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed, None
    return None, "json_parse_failed"


def _norm_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip().replace("　", " ")


def _norm_int(v: Any) -> int | None:
    """「1,200円」「¥1200」なども整数として読む。読めなければ None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    if isinstance(v, str):
        s = re.sub(r"[,\s¥円]", "", v)
        if re.fullmatch(r"-?\d+", s):
            return int(s)
    return None


WHITESPACE = re.compile(r"[\s　]+")


def _str_normalizer(grading: dict):
    """文字列比較の前にかける処理を、タスクの設定から組み立てる。

    collapse_whitespace を立てると、比べる前に両辺の空白を全部落とす。
    「名刺印刷100枚」と「名刺印刷 100枚」を同じものとして扱いたい、
    つまり測りたいのが抽出であって表記合わせではない場合に使う。
    既定は落とさない（表記まで含めて合わせたい業務があるため）。
    """
    collapse = bool(grading.get("collapse_whitespace", False))

    def norm(v: Any) -> str:
        s = _norm_str(v)
        return WHITESPACE.sub("", s) if collapse else s

    return norm


def _cmp(got: Any, want: Any, norm) -> bool:
    if isinstance(want, int):
        return _norm_int(got) == want
    return norm(got) == norm(want)


def grade(content: str, truth: dict, schema: dict, grading: dict) -> dict:
    """1件を採点する。"""
    result: dict[str, Any] = {"ok": False, "reason": None, "mismatches": []}
    norm = _str_normalizer(grading)

    parsed, err = extract_json(content)
    if parsed is None:
        result["reason"] = err
        return result

    try:
        jsonschema.validate(parsed, schema)
    except jsonschema.ValidationError as e:
        result["reason"] = "schema_violation"
        result["mismatches"].append(e.message[:200])
        return result

    for field in grading["scalar_fields"]:
        if not _cmp(parsed.get(field), truth[field], norm):
            result["mismatches"].append(
                f"{field}: got={parsed.get(field)!r} want={truth[field]!r}"
            )

    got_items = parsed.get("items") or []
    want_items = truth["items"]
    if len(got_items) != len(want_items):
        result["mismatches"].append(
            f"items: got {len(got_items)} rows, want {len(want_items)}"
        )
    else:
        for n, (g, w) in enumerate(zip(got_items, want_items)):
            for field in grading["item_fields"]:
                if not _cmp(g.get(field), w[field], norm):
                    result["mismatches"].append(
                        f"items[{n}].{field}: got={g.get(field)!r} want={w[field]!r}"
                    )

    if result["mismatches"]:
        result["reason"] = "value_mismatch"
    else:
        result["ok"] = True
    return result

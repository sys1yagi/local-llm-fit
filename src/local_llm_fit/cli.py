from __future__ import annotations

import argparse
import importlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import yaml

from . import grade as grading_mod
from . import report as report_mod
from . import run as run_mod

DEFAULT_BASE_URL = "http://localhost:1234/v1"
ROOT = Path(__file__).resolve().parents[2]


def _load_task(name_or_path: str) -> tuple[dict, Path]:
    p = Path(name_or_path)
    if not p.exists():
        p = ROOT / "tasks" / f"{name_or_path}.yaml"
    if not p.exists():
        sys.exit(f"タスク定義が見つかりません: {name_or_path}")
    return yaml.safe_load(p.read_text(encoding="utf-8")), p


def _machine() -> dict:
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
    }
    if platform.system() == "Darwin":
        try:
            info["cpu"] = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5, check=False,
            ).stdout.strip()
            mem = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5, check=False,
            ).stdout.strip()
            if mem.isdigit():
                info["memory_gb"] = round(int(mem) / 1024 ** 3)
        except (OSError, subprocess.SubprocessError):
            pass
    return info


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="fit",
        description="同じ仕事を何本も同時に投げて、答えの正しさと待ち時間を一緒に測る",
    )
    ap.add_argument("--task", default="invoice-json-ja", help="タスク名または YAML のパス")
    ap.add_argument("--model", required=False, help="モデル ID（未指定なら接続先の一覧から選べない旨を表示）")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI 互換エンドポイント")
    ap.add_argument("--concurrency", default="1,2,4,8", help="振る同時実行数（カンマ区切り）")
    ap.add_argument("--samples", type=int, default=None, help="サンプル数（タスク定義を上書き）")
    ap.add_argument("--seed", type=int, default=None, help="乱数 seed（タスク定義を上書き）")
    ap.add_argument("--timeout", type=float, default=300.0, help="1リクエストのタイムアウト秒")
    ap.add_argument("--label", default=None, help="機材の表示名（結果ファイル名に使う）")
    ap.add_argument("--dry-run", action="store_true", help="入力を1件表示して終わる")
    args = ap.parse_args()

    task, task_path = _load_task(args.task)
    gen_cfg = task["generator"]
    samples_n = args.samples or gen_cfg["samples"]
    seed = args.seed if args.seed is not None else gen_cfg["seed"]

    generator = importlib.import_module(
        f"local_llm_fit.generators.{gen_cfg['module']}"
    )
    # module / samples / seed 以外のキーは、そのまま生成器の引数として渡す。
    # 長さのような、タスクごとに変えたい値を YAML で持てるようにするため。
    gen_extra = {k: v for k, v in gen_cfg.items()
                 if k not in ("module", "samples", "seed")}
    samples = generator.generate(samples_n, seed, **gen_extra)

    if args.dry_run:
        print(f"タスク: {task['name']}  サンプル {samples_n} 件 / seed {seed}\n")
        print(samples[0]["input"])
        print("\n--- 正解 ---")
        print(json.dumps(samples[0]["truth"], ensure_ascii=False, indent=2))
        return

    if not args.model:
        sys.exit("--model を指定してください。接続先のモデル ID は "
                 f"curl {args.base_url}/models で確認できます。")

    levels = [int(x) for x in args.concurrency.split(",") if x.strip()]
    slo = task["slo"]

    print(f"タスク : {task['name']} ({samples_n} 件 / seed {seed})")
    print(f"モデル : {args.model}")
    print(f"接続先 : {args.base_url}")
    print(f"同時実行: {levels}\n")

    raw_by_level: dict[int, list] = {}
    rows: list[dict] = []

    def on_level(level_result: dict) -> None:
        graded = []
        for call in level_result["calls"]:
            truth = next(s["truth"] for s in samples if s["id"] == call.sample_id)
            if call.error:
                graded.append({"ok": False, "reason": "request_error",
                               "mismatches": [call.error]})
            else:
                graded.append(grading_mod.grade(
                    call.content, truth, task["schema"], task["grading"]))
        row = report_mod.summarize_level(level_result, graded, slo)
        rows.append(row)
        raw_by_level[level_result["concurrency"]] = list(
            zip(level_result["calls"], graded)
        )
        print(f"  {row['concurrency']:>3}本同時: "
              f"最初の文字まで {report_mod._s(row['ttft_p95_s'])} / "
              f"返り終わるまで {report_mod._s(row['e2e_p95_s'])} / "
              f"毎秒{row['throughput_tok_s']:.0f}トークン / "
              f"正答 {row['passed']}/{row['requests']} / "
              f"{row['verdict']}")

    run_mod.sweep(
        base_url=args.base_url.rstrip("/"),
        model=args.model,
        samples=samples,
        prompt_template=task["prompt"],
        levels=levels,
        request_opts=task.get("request", {}),
        timeout_s=args.timeout,
        on_level=on_level,
    )

    print("\n" + report_mod.to_markdown(rows) + "\n")
    fit = report_mod.max_ok_concurrency(rows)
    if fit is None:
        print("基準をすべて満たした同時実行数はありませんでした。")
    else:
        print(f"基準をすべて満たした最大の同時実行数: {fit}本")

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    label = args.label or _machine().get("cpu", platform.machine()).replace(" ", "-")
    slug = f"{label}_{args.model.replace('/', '-')}_{stamp}"

    summary = {
        "schema_version": 1,
        "run_id": slug,
        "measured_at": datetime.now(UTC).isoformat(),
        "task": {"name": task["name"], "file": task_path.name,
                 "samples": samples_n, "seed": seed},
        "model": args.model,
        "endpoint": args.base_url,
        "machine": _machine(),
        "slo": slo,
        "levels": rows,
        "max_ok_concurrency": fit,
    }
    out = ROOT / "results" / f"{slug}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    raw_dir = ROOT / "runs" / slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    with (raw_dir / "calls.jsonl").open("w", encoding="utf-8") as f:
        for concurrency, pairs in raw_by_level.items():
            for call, graded in pairs:
                record = asdict(call)
                record["concurrency"] = concurrency
                record["graded"] = graded
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n結果   : {out.relative_to(ROOT)}")
    print(f"全応答 : {(raw_dir / 'calls.jsonl').relative_to(ROOT)}")

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from . import grade as grading_mod
from . import htmlout
from . import report as report_mod
from . import run as run_mod
from . import validate as validate_mod

DEFAULT_BASE_URL = "http://localhost:1234/v1"
ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
RUNS = ROOT / "runs"


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


def _power_state() -> str:
    """電源につながっているか、バッテリーで動いているか。

    ノートPCをバッテリーで動かすと、機材によっては性能に上限がかかる。
    結果を見比べるときに要る情報なので、取れる環境では自動で記録する。
    """
    if platform.system() != "Darwin":
        return "unknown"
    try:
        out = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if "'AC Power'" in out:
        return "電源に接続"
    if "'Battery Power'" in out:
        return "バッテリー駆動"
    return "unknown"


def _quantization_from_api(base_url: str, model: str) -> str | None:
    """/v1/models が量子化を返すサーバなら、そこから読む。返さなければ None。

    OpenAI 互換の仕様には無い項目なので、返さないサーバの方が多い。
    その場合は --quantization で受け取る。
    """
    try:
        resp = httpx.get(f"{base_url}/models", timeout=5.0)
        if resp.status_code != 200:
            return None
        for entry in resp.json().get("data") or []:
            if entry.get("id") == model:
                quant = entry.get("quant") or entry.get("quantization")
                return str(quant) if quant else None
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    return None


def _read_calls(run_id: str) -> list[dict] | None:
    """runs/ に生データが残っていれば読む。無ければ None。"""
    path = RUNS / run_id / "calls.jsonl"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_report(summary: dict, with_raw: bool = True) -> Path:
    calls = _read_calls(summary["run_id"]) if with_raw else None
    html = htmlout.render_report(summary, calls, method_href="../METHOD.md")
    out = RESULTS / f"{summary['run_id']}.html"
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "report":
        return _cmd_report(argv[1:])
    if argv and argv[0] == "pages":
        return _cmd_pages(argv[1:])
    if argv and argv[0] == "check":
        return _cmd_check(argv[1:])
    return _cmd_measure(argv)


def _cmd_report(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(
        prog="fit report",
        description="測定結果のJSONから、単体で開けるHTMLのレポートを作る",
    )
    ap.add_argument("json_files", nargs="+", help="results/ のJSON（複数可）")
    args = ap.parse_args(argv)

    for name in args.json_files:
        path = Path(name)
        if not path.exists():
            sys.exit(f"見つかりません: {name}")
        summary = json.loads(path.read_text(encoding="utf-8"))
        out = _write_report(summary)
        raw = "あり" if _read_calls(summary["run_id"]) else "なし"
        print(f"{out.relative_to(ROOT)}（生データ: {raw}）")


def _cmd_pages(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(
        prog="fit pages",
        description="results/ と tasks/ から、シナリオ・モデル・機材で引けるサイトを作る",
    )
    ap.add_argument("outdir", nargs="?", default="site", help="出力先（既定 site）")
    args = ap.parse_args(argv)

    out = Path(args.outdir)
    if not out.is_absolute():
        out = ROOT / out

    from . import site
    got = site.build(ROOT, out)
    where = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"{where} に {len(got['pages'])}ページ書き出しました"
          f"（シナリオ {got['scenarios']} / 測定 {got['results']} / "
          f"モデル {got['models']} / 機材 {got['machines']}）")


def _cmd_check(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(
        prog="fit check",
        description="results/ のJSONを点検する。おかしな点は警告として並べ、"
                    "終了コードは0のままにする",
    )
    ap.add_argument("json_files", nargs="+", help="results/ のJSON（複数可）")
    ap.add_argument("--github", action="store_true",
                    help="GitHub Actions の警告注釈の形で出す")
    args = ap.parse_args(argv)

    as_annotation = args.github or os.environ.get("GITHUB_ACTIONS") == "true"
    total = 0
    for name in args.json_files:
        path = Path(name)
        warnings = validate_mod.check_file(path, ROOT / "tasks")
        total += len(warnings)
        rel = path.relative_to(ROOT) if path.is_absolute() and path.is_relative_to(ROOT) else path
        if not warnings:
            print(f"{rel}: 問題なし")
            continue
        for w in warnings:
            if as_annotation:
                print(f"::warning file={rel}::{w}")
            else:
                print(f"{rel}: {w}")

    print(f"\n{len(args.json_files)}件を点検し、警告 {total}件。")
    if total:
        print("警告は投稿を止めるものではありません。"
              "心当たりがなければそのまま送ってください。")


def _cmd_measure(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(
        prog="fit",
        description="同じ仕事を何本も同時に投げて、答えの正しさと待ち時間を一緒に測る",
        epilog="サブコマンド: report <json...> / pages [出力先]",
    )
    ap.add_argument("--task", default="invoice-json-ja", help="タスク名または YAML のパス")
    ap.add_argument("--model", required=False, help="モデル ID")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI 互換エンドポイント")
    ap.add_argument("--concurrency", default="1,2,4,8", help="振る同時実行数（カンマ区切り）")
    ap.add_argument("--samples", type=int, default=None, help="サンプル数（タスク定義を上書き）")
    ap.add_argument("--seed", type=int, default=None, help="乱数 seed（タスク定義を上書き）")
    ap.add_argument("--timeout", type=float, default=300.0, help="1リクエストのタイムアウト秒")
    ap.add_argument("--label", default=None, help="機材の表示名（結果ファイル名に使う）")
    ap.add_argument("--server-label", default=None,
                    help="推論サーバの種別を自由記述で残す（例: LM Studio 0.3 / vLLM 0.9）。"
                         "自動では判別しない")
    ap.add_argument("--quantization", default=None,
                    help="量子化の表記（例: Q4_K_M / MLX 4bit / BF16）。"
                         "APIが返すサーバなら省略できる")
    ap.add_argument("--server-concurrency", default=None,
                    help="推論サーバ側で設定した同時処理数（例: 4）。"
                         "APIからは取れないので、設定した値を書き添える")
    ap.add_argument("--power", default=None,
                    help="電源の状態（例: 電源に接続 / バッテリー駆動）。"
                         "macOS では省略すると自動で記録する")
    ap.add_argument("--dry-run", action="store_true", help="入力を1件表示して終わる")
    args = ap.parse_args(argv)

    task, task_path = _load_task(args.task)
    gen_cfg = task["generator"]
    samples_n = args.samples or gen_cfg["samples"]
    seed = args.seed if args.seed is not None else gen_cfg["seed"]
    levels = [int(x) for x in args.concurrency.split(",") if x.strip()]

    generator = importlib.import_module(
        f"local_llm_fit.generators.{gen_cfg['module']}"
    )
    # module / samples / seed 以外のキーは、そのまま生成器の引数として渡す。
    # 長さのような、タスクごとに変えたい値を YAML で持てるようにするため。
    gen_extra = {k: v for k, v in gen_cfg.items()
                 if k not in ("module", "samples", "seed")}

    if args.dry_run:
        samples = generator.generate_row(samples_n, seed, 0, **gen_extra)
        print(f"タスク: {task['name']}  サンプル {samples_n} 件 / seed {seed}\n")
        print(samples[0]["input"])
        print("\n--- 正解 ---")
        print(json.dumps(samples[0]["truth"], ensure_ascii=False, indent=2))
        return

    if not args.model:
        sys.exit("--model を指定してください。接続先のモデル ID は "
                 f"curl {args.base_url}/models で確認できます。")

    # 同時本数の行ごとに、同じ正解を別の文面で描き直したものを投げる。
    # 正解を行間で固定するのは、行ごとの正答率を並べて比べられるようにするため。
    # 文面を行ごとに変えるのは、同じ文面を投げ直すと推論サーバが前回読んだ
    # 内容を覚えていて、後の行ほど速く見えてしまうため。
    samples_by_level = [generator.generate_row(samples_n, seed, r, **gen_extra)
                        for r in range(len(levels))]
    # 正解は行によらず同じなので、1行目から引ければ足りる。
    truth_by_id = {s["id"]: s["truth"] for s in samples_by_level[0]}
    slo = task["slo"]

    print(f"タスク : {task['name']} ({samples_n} 件 × {len(levels)}行 / seed {seed})")
    print(f"モデル : {args.model}")
    print(f"接続先 : {args.base_url}")
    print(f"同時実行: {levels}（行ごとに同じ正解・別の文面）\n")

    raw_by_level: dict[int, list] = {}
    rows: list[dict] = []

    def on_level(level_result: dict) -> None:
        graded = []
        for call in level_result["calls"]:
            truth = truth_by_id[call.sample_id]
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
        samples_by_level=samples_by_level,
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

    # 後から結果どうしを比べられるようにするための情報。
    # 分からないものは "unknown" で埋めて、測定そのものは止めない。
    environment = {
        "server": args.server_label or "unknown",
        "quantization": (args.quantization
                         or _quantization_from_api(args.base_url.rstrip("/"), args.model)
                         or "unknown"),
        "server_concurrency": args.server_concurrency or "unknown",
        "power": args.power or _power_state(),
        "request_timeout_s": args.timeout,
    }

    summary = {
        "schema_version": 2,
        "run_id": slug,
        "measured_at": datetime.now(UTC).isoformat(),
        "task": {"name": task["name"], "file": task_path.name,
                 "version": task.get("version"),
                 "samples_per_level": samples_n, "seed": seed,
                 "same_truth_different_wording_per_level": True},
        "model": args.model,
        "endpoint": args.base_url,
        "server_label": args.server_label,
        "environment": environment,
        "machine": _machine(),
        "slo": slo,
        "levels": rows,
        "max_ok_concurrency": fit,
    }
    out = RESULTS / f"{slug}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    raw_dir = RUNS / slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    with (raw_dir / "calls.jsonl").open("w", encoding="utf-8") as f:
        for concurrency, pairs in raw_by_level.items():
            for call, graded in pairs:
                record = asdict(call)
                record["concurrency"] = concurrency
                record["graded"] = graded
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    html = _write_report(summary)

    print(f"\n結果    : {out.relative_to(ROOT)}")
    print(f"全応答  : {(raw_dir / 'calls.jsonl').relative_to(ROOT)}")
    print(f"レポート: {html.relative_to(ROOT)}")

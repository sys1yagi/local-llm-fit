"""results/ と tasks/ から、シナリオ・モデル・機材で引けるサイトを組み立てる。

載せる文章はすべてリポジトリの中にあるものを引いてくる。
ここで新しく文章を書き起こさない。

ページの種類:
  index.html          シナリオ50件の一覧
  s-<id>.html         シナリオ1件。定義・指示・入力の実物・そのシナリオの全実測
  m-<slug>.html       モデル1つ。シナリオ×機材
  h-<slug>.html       機材1つ。シナリオ×モデル
  r-<run_id>.html     測定1回。一次のレコード
  method.html         測定条件（METHOD.md）と、実行から結果の送付までの手順
  catalog.html        業務シナリオのカタログ（CATALOG.md）
"""

from __future__ import annotations

import importlib
import json
import re
from html import escape
from pathlib import Path

import yaml

from . import htmlout, mdlite
from .docsrc import Docs

LINK_MAP = {
    "METHOD.md": "method.html",
    "tasks/invoice-json-ja.yaml": "s-invoice-json-ja.html",
    "https://nejumi.ai": "https://nejumi.ai",
}


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-").lower() or "unknown"


def _machine_label(summary: dict) -> str:
    m = summary.get("machine") or {}
    parts = [m.get("cpu") or m.get("arch") or "不明"]
    if m.get("memory_gb"):
        parts.append(f"メモリ{m['memory_gb']}GB")
    return " / ".join(parts)


def _fit_text(summary: dict) -> str:
    fit = summary.get("max_ok_concurrency")
    return f"{fit}本" if fit else "なし"


def _nav(current: str, extra: list[tuple[str, str]] | None = None) -> str:
    links = [("シナリオ一覧", "index.html"), ("測り方", "method.html"),
             ("カタログ", "catalog.html")]
    links += extra or []
    got = "".join(
        f'<a href="{escape(h, quote=True)}">{escape(t)}</a>' if h != current
        else f"<span>{escape(t)}</span>"
        for t, h in links)
    return f'<p class="nav">{got}</p>'


def _p95_rank(samples: int) -> int:
    return samples - max(1, round(0.95 * samples)) + 1


def _retarget(text: str, samples: int | None) -> str:
    """引用の中の件数を、そのページのサンプル数に合わせる。

    合わせられないページ（複数のシナリオが混ざる一覧）では、
    件数の具体例を落として引用する。意味は変えない。
    """
    if samples:
        return (text.replace("48件のうち遅い方から3件目", f"{samples}件のうち遅い方から{_p95_rank(samples)}件目")
                    .replace("48件なら遅い方から3件目", f"{samples}件なら遅い方から{_p95_rank(samples)}件目")
                    .replace("48件のうち、", f"{samples}件のうち、")
                    .replace("同じ48件の正解", f"同じ{samples}件の正解"))
    return (text.replace("48件のうち遅い方から3件目の値（p95）", "p95の値")
                .replace("（48件なら遅い方から3件目）", "")
                .replace("48件のうち、", "")
                .replace("同じ48件の正解", "同じ正解"))


def _legend(docs: Docs, samples: int | None = None) -> str:
    """表の列が何を指すかの説明。README と METHOD からそのまま引く。

    引用するのは用語の定義だけで、特定のタスクの基準値に触れた段は載せない。
    """
    only_terms = "\n".join(
        ln for ln in docs.table_legend.split("\n")
        if ln.startswith(("-", " ", "\t")) or not ln.strip())
    body = mdlite.render(_retarget(only_terms, samples), LINK_MAP)
    p95 = ""
    for para in docs.measured_values.split("\n\n"):
        if "p95" in para and "補間" in para:
            p95 = mdlite.render(_retarget(para, samples), LINK_MAP)
            break
    return ('<div class="legend"><p class="note">README「表の読み方」・'
            f"METHOD.md「測っている値」より</p>{body}{p95}</div>")


def _measure_table(rows: list[tuple[str, str, dict]], left: str, right: str) -> str:
    """(左の軸, 右の軸, 測定) の並びを表にする。"""
    if not rows:
        return '<p class="empty">実測なし。</p>'
    body = []
    for a, b, s in rows:
        body.append(
            "<tr>"
            f"<td>{a}</td><td>{b}</td>"
            f"<td>{escape((s.get('measured_at') or '')[:10])}</td>"
            f"<td>{escape(_fit_text(s))}</td>"
            f'<td><a href="r-{escape(s["run_id"], quote=True)}.html">測定を見る</a></td>'
            "</tr>")
    return ("<table><thead><tr>"
            f"<th>{escape(left)}</th><th>{escape(right)}</th><th>測定日</th>"
            "<th>基準を満たす最大本数</th><th></th>"
            "</tr></thead><tbody>" + "".join(body) + "</tbody></table>")


def _sample_of(root: Path, task: dict) -> tuple[str, str] | None:
    """タスク定義から入力の実物を1件作る。作れなければ None。"""
    cfg = task["generator"]
    try:
        gen = importlib.import_module(f"local_llm_fit.generators.{cfg['module']}")
        extra = {k: v for k, v in cfg.items()
                 if k not in ("module", "samples", "seed")}
        sample = gen.generate_row(1, cfg["seed"], 0, **extra)[0]
    except (ImportError, AttributeError, KeyError, TypeError):
        return None
    return sample["input"], json.dumps(sample["truth"], ensure_ascii=False, indent=2)


def _index(docs: Docs, scen: list[dict], counts: dict[str, int]) -> str:
    rows = []
    for s in scen:
        n = counts.get(s["id"], 0)
        rows.append(
            "<tr>"
            f"<td>{escape(s['family_code'])}. {escape(s['family_name'])}</td>"
            f'<td><a href="s-{escape(s["id"], quote=True)}.html">'
            f"{escape(s['work'])}</a>"
            f'<span class="sub-id"><code>{escape(s["id"])}</code></span></td>'
            f"<td>{escape(s['state'])}</td>"
            f"<td>{n}</td>"
            "</tr>")
    body = [
        _nav("index.html"),
        "<h1>local-llm-fit</h1>",
        mdlite.render(docs.readme_opening, LINK_MAP),
        "<h2>シナリオ</h2>",
        "<table><thead><tr><th>族</th><th>シナリオ</th><th>状態</th>"
        "<th>実測（モデル×機材の組数）</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>",
    ]
    return htmlout.document("local-llm-fit", "".join(body))


def _scenario_page(docs: Docs, s: dict, task: dict | None,
                   sample: tuple[str, str] | None,
                   rows: list[tuple[str, str, dict]]) -> str:
    facts = [
        ("族", f"{s['family_code']}. {s['family_name']}"),
        ("状態", s["state"]),
        ("仕事の内容", s["work"]),
        ("採点", s["grading"]),
        ("入力長", s["input_len"]),
        ("出力形", s["output_shape"]),
        ("難所", s["difficulty"]),
        ("使う部品", s["parts"]),
    ]
    meta = "".join(f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in facts)

    body = [
        _nav(""),
        (f"<h1>{escape(s['work'])}<br>"
         f'<span class="sub-id"><code>{escape(s["id"])}</code></span></h1>'),
        ('<p class="note">出典: '
         '<a href="catalog.html">業務シナリオのカタログ</a></p>'),
        f'<dl class="meta">{meta}</dl>',
    ]

    if task:
        slo = task["slo"]
        samples = task["generator"]["samples"]
        body += [
            "<h2>タスク定義</h2>",
            f"<p>{escape(task['title'])}</p>",
            mdlite.render(task.get("description", ""), LINK_MAP),
            "<h2>使う基準</h2>",
            _legend(docs, samples),
            ("<ul>"
             f"<li>正答率 {slo.get('pass_rate', 0) * 100:.0f}% 以上</li>"
             f"<li>最初の文字まで {slo.get('ttft_p95_s')} 秒以内（p95）</li>"
             f"<li>返り終わるまで {slo.get('e2e_p95_s')} 秒以内（p95）</li>"
             f"<li>エラー率 {slo.get('error_rate', 0) * 100:.0f}%</li>"
             "</ul>"),
            "<h2>モデルに渡す指示</h2>",
            f'<pre class="src">{escape(task["prompt"])}</pre>',
        ]
        if sample:
            body += [
                "<h2>入力の実物</h2>",
                (f'<p class="note">seed {task["generator"]["seed"]} の1件目、'
                 f"{len(sample[0]):,}字。</p>"),
                f'<pre class="src">{escape(sample[0])}</pre>',
                "<h2>正解</h2>",
                f'<pre class="src">{escape(sample[1])}</pre>',
            ]
    else:
        anchor = docs.catalog_anchor("パイロットによる採否")
        body += [
            "<h2>タスク定義</h2>",
            '<p class="empty">なし。</p>',
            (f'<p class="note">採否の手順: '
             f'<a href="catalog.html#{escape(anchor, quote=True)}">'
             "カタログ「パイロットによる採否」</a></p>"),
        ]

    body += ["<h2>実測</h2>"]
    if rows and not task:
        body += [_legend(docs)]
    elif rows and task:
        pass  # 上の「使う基準」で説明済み
    body += [_measure_table(rows, "モデル", "機材")]
    return htmlout.document(s["id"], "".join(body))


def _axis_page(docs: Docs, title: str,
               rows: list[tuple[str, str, dict]], right_label: str) -> str:
    body = [
        _nav(""),
        f"<h1>{escape(title)}</h1>",
        f'<p class="lede">測定 {len(rows)}件</p>',
        "<h2>実測</h2>",
        _legend(docs),
        _measure_table(rows, "シナリオ", right_label),
    ]
    return htmlout.document(title, "".join(body))


def _method_page(docs: Docs) -> str:
    body = [
        _nav("method.html"),
        mdlite.render(docs.method_md, LINK_MAP),
        "<hr>",
        '<h1 id="使う">使う</h1>',
        mdlite.render(docs.run_howto, LINK_MAP, heading_shift=1),
        '<h1 id="結果を持ち寄る">結果を持ち寄る</h1>',
        mdlite.render(docs.share_howto, LINK_MAP, heading_shift=1),
    ]
    return htmlout.document("測定条件", "".join(body))


def _catalog_page(docs: Docs, scen: list[dict]) -> str:
    link_map = dict(LINK_MAP)
    for s in scen:
        link_map[f"tasks/{s['id']}.yaml"] = f"s-{s['id']}.html"
    body = [_nav("catalog.html"), mdlite.render(docs.catalog_md, link_map)]
    return htmlout.document("業務シナリオのカタログ", "".join(body))


def build(root: Path, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    docs = Docs(root)
    scen = docs.scenarios

    tasks: dict[str, dict] = {}
    for path in sorted((root / "tasks").glob("*.yaml")):
        task = yaml.safe_load(path.read_text(encoding="utf-8"))
        if task and task.get("name"):
            tasks[task["name"]] = task

    results = [json.loads(p.read_text(encoding="utf-8"))
               for p in sorted((root / "results").glob("*.json"))]
    results.sort(key=lambda s: s.get("measured_at") or "", reverse=True)

    by_task: dict[str, list[dict]] = {}
    by_model: dict[str, list[dict]] = {}
    by_machine: dict[str, list[dict]] = {}
    for s in results:
        by_task.setdefault(s["task"]["name"], []).append(s)
        by_model.setdefault(s.get("model") or "不明", []).append(s)
        by_machine.setdefault(_machine_label(s), []).append(s)

    counts = {k: len({(s.get("model"), _machine_label(s)) for s in v})
              for k, v in by_task.items()}

    model_href = {m: f"m-{_slug(m)}.html" for m in by_model}
    machine_href = {m: f"h-{_slug(m)}.html" for m in by_machine}
    scen_ids = {s["id"] for s in scen}

    def model_cell(s: dict) -> str:
        m = s.get("model") or "不明"
        return f'<a href="{escape(model_href[m], quote=True)}">{escape(m)}</a>'

    def machine_cell(s: dict) -> str:
        m = _machine_label(s)
        return f'<a href="{escape(machine_href[m], quote=True)}">{escape(m)}</a>'

    def scenario_cell(s: dict) -> str:
        name = s["task"]["name"]
        if name in scen_ids:
            return f'<a href="s-{escape(name, quote=True)}.html"><code>{escape(name)}</code></a>'
        return f"<code>{escape(name)}</code>"

    written = []

    (outdir / "index.html").write_text(_index(docs, scen, counts), encoding="utf-8")
    written.append("index.html")

    for s in scen:
        rows = [(model_cell(r), machine_cell(r), r)
                for r in by_task.get(s["id"], [])]
        task = tasks.get(s["id"])
        sample = _sample_of(root, task) if task else None
        page = _scenario_page(docs, s, task, sample, rows)
        (outdir / f"s-{s['id']}.html").write_text(page, encoding="utf-8")
        written.append(f"s-{s['id']}.html")

    for model, rs in by_model.items():
        rows = [(scenario_cell(r), machine_cell(r), r) for r in rs]
        page = _axis_page(docs, model, rows, "機材")
        (outdir / model_href[model]).write_text(page, encoding="utf-8")
        written.append(model_href[model])

    for machine, rs in by_machine.items():
        rows = [(scenario_cell(r), model_cell(r), r) for r in rs]
        page = _axis_page(docs, machine, rows, "モデル")
        (outdir / machine_href[machine]).write_text(page, encoding="utf-8")
        written.append(machine_href[machine])

    legend = _legend(docs)
    for s in results:
        extra = [("シナリオ", f"s-{s['task']['name']}.html"),
                 ("モデル", model_href[s.get("model") or "不明"]),
                 ("機材", machine_href[_machine_label(s)])]
        page = htmlout.render_report(
            s, None, method_href="method.html",
            nav_html=_nav("", extra), legend_html=legend)
        (outdir / f"r-{s['run_id']}.html").write_text(page, encoding="utf-8")
        written.append(f"r-{s['run_id']}.html")

    (outdir / "method.html").write_text(_method_page(docs), encoding="utf-8")
    (outdir / "catalog.html").write_text(_catalog_page(docs, scen), encoding="utf-8")
    written += ["method.html", "catalog.html"]

    return {"pages": written, "scenarios": len(scen), "results": len(results),
            "models": len(by_model), "machines": len(by_machine)}

"""測定結果を見るためのHTMLを組み立てる。

自己完結の1ファイルとして出す。外部のCSS・フォント・スクリプトを参照しないので、
ネットに繋がっていない状態でも、ファイルを開けばそのまま読める。

詳細ページの描画コードは、手元のレポートと持ち寄りページの両方で共有する。
違いは、手元のレポートには runs/ の生データから作った内訳の節が付くことだけ。
"""

from __future__ import annotations

from html import escape

from . import svg

PAGE_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0 auto; padding: 28px 20px 64px; max-width: 900px;
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans",
    "Noto Sans JP", "Yu Gothic", sans-serif;
  color: #1b1f24; background: #fff; line-height: 1.75;
}
h1 { font-size: 22px; margin: 0 0 6px; }
h2 { font-size: 17px; margin: 40px 0 10px; padding-bottom: 6px;
     border-bottom: 1px solid #e4e7ec; }
h3 { font-size: 14px; margin: 24px 0 8px; }
p, li { font-size: 14px; }
a { color: #1d4e86; }
.lede { color: #6b7681; font-size: 13px; margin: 0 0 20px; }
.answer { margin: 18px 0; padding: 14px 16px; background: #f2f6fa;
          border-left: 4px solid #2f6db4; font-size: 15px; font-weight: 600; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }
th, td { border-bottom: 1px solid #e4e7ec; padding: 7px 9px; text-align: right; }
th { background: #f7f9fb; font-weight: 600; white-space: nowrap; }
th:first-child, td:first-child { text-align: right; }
th:last-child, td:last-child { text-align: left; }
tbody tr:hover { background: #fafbfc; }
.meta { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px;
        font-size: 13px; margin: 0 0 8px; }
.meta dt { color: #6b7681; }
.meta dd { margin: 0; }
.note { font-size: 12px; color: #6b7681; margin: 8px 0 0; }
.warn { padding: 12px 14px; background: #fff8e6; border-left: 4px solid #d99a1a;
        font-size: 13px; margin: 16px 0; }
.charts { display: grid; gap: 20px; margin-top: 12px; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 92%;
       background: #f3f5f7; padding: 1px 4px; border-radius: 3px; }
.mark { color: #c2352b; }
.nav { font-size: 12px; color: #6b7681; margin: 0 0 18px; }
.nav a, .nav span { margin-right: 12px; }
.sub-id { display: block; font-size: 11px; color: #6b7681; }
.legend { background: #f7f9fb; border: 1px solid #e4e7ec; border-radius: 4px;
          padding: 10px 16px; margin: 12px 0 16px; font-size: 12.5px; }
.legend ul { margin: 4px 0; padding-left: 20px; }
.legend li { font-size: 12.5px; }
.legend p { font-size: 12.5px; margin: 6px 0; }
.src { display: block; max-height: 420px; overflow: auto; background: #f7f9fb;
       border: 1px solid #e4e7ec; border-radius: 4px; padding: 12px 14px;
       font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
       font-size: 12px; line-height: 1.6; white-space: pre-wrap;
       word-break: break-all; }
.empty { color: #6b7681; font-size: 14px; }
.matrix { table-layout: fixed; }
.matrix th { white-space: normal; font-size: 11px; word-break: break-all;
             text-align: center; }
.matrix td { text-align: center; }
.matrix th:first-child, .matrix td:first-child { text-align: left; width: 22%; }
.matrix .gap { color: #b9c0c7; }
.headline { font-size: 21px; font-weight: 700; margin: 14px 0 2px; color: #16406e; }
.sub { font-size: 12px; color: #6b7681; margin: 0 0 12px; }
.reading { font-size: 15px; margin: 0 0 6px; padding: 12px 14px;
           background: #f2f6fa; border-left: 4px solid #2f6db4; }
"""


def document(title: str, body: str) -> str:
    """1ページぶんのHTML。外部の参照を持たない自己完結の形にする。"""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ja"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>{PAGE_CSS}{svg.CSS}</style>\n"
        f"</head><body>\n{body}\n</body></html>\n"
    )


def _doc(title: str, body: str) -> str:
    return document(title, body)


def _sec(v) -> str:
    return "-" if v is None else f"{v:.2f}秒"


def _pct(v: float) -> str:
    return f"{v:.0f}%"


def _tok(v: float) -> str:
    return f"{v:.0f}"


def _task_label(summary: dict) -> str:
    t = summary["task"]
    n = t.get("samples_per_level") or t.get("samples")
    ver = f" / 定義 version {t['version']}" if t.get("version") else ""
    return f"{t['name']}（{n}件 × {len(summary['levels'])}行 / seed {t['seed']}{ver}）"


def _charts(summary: dict) -> str:
    levels = summary["levels"]
    slo = summary["slo"]
    x = [r["concurrency"] for r in levels]

    ttft = svg.chart(
        title="最初の文字が出るまで（p95）",
        x_values=x, y_values=[r["ttft_p95_s"] or 0.0 for r in levels],
        y_label="秒", fmt=lambda v: f"{v:.1f}",
        slo=slo.get("ttft_p95_s"),
        slo_text=f"基準 {slo.get('ttft_p95_s')}秒",
    )
    e2e = svg.chart(
        title="返り終わるまで（p95）",
        x_values=x, y_values=[r["e2e_p95_s"] or 0.0 for r in levels],
        y_label="秒", fmt=lambda v: f"{v:.1f}",
        slo=slo.get("e2e_p95_s"),
        slo_text=f"基準 {slo.get('e2e_p95_s')}秒",
    )
    thr = svg.chart(
        title="1秒あたりの生成量（縦軸は0起点）",
        x_values=x, y_values=[r["throughput_tok_s"] for r in levels],
        y_label="トークン/秒", fmt=_tok, y_min=0.0,
    )

    bars: list[tuple[float, float] | None] = []
    for r in levels:
        if r.get("pass_rate_lo") is None or r.get("pass_rate_hi") is None:
            bars.append(None)
        else:
            bars.append((r["pass_rate_lo"] * 100, r["pass_rate_hi"] * 100))
    acc = svg.chart(
        title="正答率（縦棒は95%区間）",
        x_values=x, y_values=[r["pass_rate"] * 100 for r in levels],
        y_label="正答率", fmt=_pct, y_min=0.0, y_max=100.0,
        slo=slo.get("pass_rate", 0) * 100,
        slo_text=f"基準 {slo.get('pass_rate', 0) * 100:.0f}%",
        error_bars=bars,
    )
    return f'<div class="charts">{ttft}{e2e}{thr}{acc}</div>'


def _table(summary: dict) -> str:
    rows = []
    for r in summary["levels"]:
        mark = ' <span class="mark">※</span>' if r.get("accuracy_inconclusive") else ""
        band = ""
        if r.get("pass_rate_lo") is not None:
            band = (f"<br><small>{r['pass_rate_lo'] * 100:.0f}〜"
                    f"{r['pass_rate_hi'] * 100:.0f}%</small>")
        rows.append(
            "<tr>"
            f"<td>{r['concurrency']}</td>"
            f"<td>{_sec(r['ttft_p95_s'])}</td>"
            f"<td>{_sec(r['e2e_p95_s'])}</td>"
            f"<td>{r['throughput_tok_s']:.0f}</td>"
            f"<td>{r['passed']}/{r['requests']} {r['pass_rate'] * 100:.0f}%{band}</td>"
            f"<td>{r['errors']}</td>"
            f"<td>{escape(r['verdict'])}{mark}</td>"
            "</tr>"
        )
    footnote = ""
    if any(r.get("accuracy_inconclusive") for r in summary["levels"]):
        footnote = ('<p class="note"><span class="mark">※</span> '
                    "正答率の95%区間の上端が基準を超えている行。"
                    "基準を割ったと断定するには件数が足りない。</p>")
    return (
        "<table><thead><tr>"
        "<th>同時に投げた本数</th><th>最初の文字まで</th><th>返り終わるまで</th>"
        "<th>トークン/秒</th><th>正答率（95%区間）</th><th>エラー</th><th>判定</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>" + footnote
    )


def _slo_list(summary: dict) -> str:
    slo = summary["slo"]
    items = [
        f"正答率 {slo.get('pass_rate', 0) * 100:.0f}% 以上",
        f"最初の文字まで {slo.get('ttft_p95_s')} 秒以内（p95）",
        f"返り終わるまで {slo.get('e2e_p95_s')} 秒以内（p95）",
        f"エラー率 {slo.get('error_rate', 0) * 100:.0f}%",
    ]
    return "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


def _failures(calls: list[dict]) -> str:
    """runs/ の生データから、落ちた件の内訳を出す。"""
    by_reason: dict[str, int] = {}
    by_mismatch: dict[str, int] = {}
    by_level: dict[int, int] = {}
    for c in calls:
        g = c.get("graded") or {}
        if g.get("ok"):
            continue
        reason = g.get("reason") or "unknown"
        by_reason[reason] = by_reason.get(reason, 0) + 1
        by_level[c["concurrency"]] = by_level.get(c["concurrency"], 0) + 1
        for m in (g.get("mismatches") or [])[:3]:
            by_mismatch[m] = by_mismatch.get(m, 0) + 1

    if not by_reason:
        return "<p>落ちた件はありませんでした。</p>"

    def rows(d, key_name, limit=None):
        items = sorted(d.items(), key=lambda kv: -kv[1])
        if limit:
            items = items[:limit]
        body = "".join(
            f"<tr><td>{v}</td><td>{escape(str(k))}</td></tr>" for k, v in items
        )
        return (f"<table><thead><tr><th>件数</th><th>{escape(key_name)}</th>"
                f"</tr></thead><tbody>{body}</tbody></table>")

    out = ["<h3>理由の内訳</h3>", rows(by_reason, "理由"),
           "<h3>同時本数ごとの落ちた件数</h3>",
           rows({f"{k}本同時": v for k, v in sorted(by_level.items())}, "行"),
           "<h3>外れた値（多い順・上位15件）</h3>", rows(by_mismatch, "内容", 15)]
    return "".join(out)


def render_report(summary: dict, calls: list[dict] | None = None,
                  method_href: str = "METHOD.md",
                  back_href: str | None = None,
                  nav_html: str = "", legend_html: str = "") -> str:
    """測定1回ぶんの詳細ページ。calls を渡すと落ちた件の内訳が付く。"""
    machine = summary.get("machine") or {}
    fit = summary.get("max_ok_concurrency")
    answer = (f"基準をすべて満たした最大の同時実行数: {fit}本"
              if fit else "基準をすべて満たした同時実行数はありませんでした")

    env = summary.get("environment") or {}
    meta_rows = [
        ("仕事", _task_label(summary)),
        ("モデル", summary.get("model", "-")),
        ("推論サーバ", summary.get("server_label") or "（未記入）"),
        ("接続先", summary.get("endpoint", "-")),
        ("機材", " / ".join(filter(None, [
            machine.get("cpu"),
            f"メモリ {machine['memory_gb']}GB" if machine.get("memory_gb") else None,
            machine.get("os"),
        ])) or "-"),
        ("測定日時", summary.get("measured_at", "-")),
    ]
    # 環境の節は version を刻んだあとの測定にだけ入っている。
    # 旧形式は行ごと出さない（「unknown」が並ぶだけになるため）。
    if env:
        timeout = env.get("request_timeout_s")
        meta_rows += [
            ("量子化", env.get("quantization", "unknown")),
            ("サーバ側の同時処理数", env.get("server_concurrency", "unknown")),
            ("電源", env.get("power", "unknown")),
            ("1件の打ち切り", f"{timeout:.0f}秒" if timeout else "なし"),
        ]
    meta = "".join(f"<dt>{escape(k)}</dt><dd>{escape(str(v))}</dd>"
                   for k, v in meta_rows)

    nav = nav_html or (
        f'<p class="nav"><a href="{escape(back_href)}">← 一覧</a></p>' if back_href else "")

    body = [
        nav,
        f"<h1>{escape(summary['task']['name'])} の測定結果</h1>",
        f'<p class="lede">run id: <code>{escape(summary["run_id"])}</code></p>',
        f'<dl class="meta">{meta}</dl>',
        f'<div class="answer">{escape(answer)}</div>',
        "<h2>結果</h2>", legend_html, _table(summary),
        "<h2>グラフ</h2>",
        ('<p class="note">横軸は同時に投げた本数（対数）。'
         '赤い破線がこの測定で使った基準です。</p>'),
        _charts(summary),
        "<h2>使った基準</h2>",
        ("<p>下の4つをすべて満たした行を「基準を満たす」としています。"
         "この数字はタスク定義に書いてあり、業務ごとに置き直すものです。</p>"),
        _slo_list(summary),
    ]
    if calls:
        body += ["<h2>落ちた件の内訳</h2>",
                 ('<p class="note">手元の <code>runs/</code> の生データから'
                  "作っています。配布用に生成した場合は付きません。</p>"),
                 _failures(calls)]
    body += [
        "<h2>この数字の前提</h2>",
        ("<p>揃えている条件・揃えていない条件・この測り方では分からないことは"
         f'<a href="{escape(method_href)}">測定条件</a>にまとめてあります。'
         "別の測定と見比べるときは先に読んでください。</p>"),
    ]
    return _doc(f"{summary['task']['name']} の測定結果", "".join(body))

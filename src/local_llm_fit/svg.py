"""グラフをインラインSVGとして組み立てる。

外部のライブラリもCDNも使わない。生成したHTMLは、ネットに繋がっていない
状態でもそのまま開ける。

描くのは results/*.json に入っている値だけで、ここでは計算し直さない。
単位の変換（割合→パーセント）だけは行う。
"""

from __future__ import annotations

import math
from html import escape

W, H = 620, 320
PAD_L, PAD_R, PAD_T, PAD_B = 74, 28, 36, 50

INK = "#1b1f24"
MUTED = "#6b7681"
GRID = "#e4e7ec"
LINE = "#2f6db4"
POINT = "#1d4e86"
SLO = "#c2352b"


def _xs(values: list[float]) -> list[float]:
    """横軸は同時本数。1, 2, 4, 8 ... を等間隔に置くので底2の対数を使う。"""
    lo = math.log2(min(values))
    hi = math.log2(max(values))
    span = (hi - lo) or 1.0
    inner = W - PAD_L - PAD_R
    return [PAD_L + (math.log2(v) - lo) / span * inner for v in values]


def _y(v: float, lo: float, hi: float) -> float:
    inner = H - PAD_T - PAD_B
    t = (v - lo) / ((hi - lo) or 1.0)
    return PAD_T + inner - t * inner


def _ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    return [lo + (hi - lo) * i / (count - 1) for i in range(count)]


def chart(*, title: str, x_values: list[int], y_values: list[float],
          y_label: str, fmt, y_min: float = 0.0, y_max: float | None = None,
          slo: float | None = None, slo_text: str | None = None,
          error_bars: list[tuple[float, float] | None] | None = None) -> str:
    """折れ線1本のグラフ。SLOの水平線と、任意でエラーバーを添える。"""
    span_values = list(y_values)
    if slo is not None:
        span_values.append(slo)
    if error_bars:
        for band in error_bars:
            if band:
                span_values.extend(band)
    if y_max is None:
        top = max(span_values)
        y_max = top * 1.18 if top > 0 else 1.0
    y_max = max(y_max, y_min + 1e-9)

    px = _xs([float(v) for v in x_values])
    py = [_y(v, y_min, y_max) for v in y_values]

    out: list[str] = [
        (f'<svg class="chart" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'role="img" xmlns="http://www.w3.org/2000/svg">'),
        f"<title>{escape(title)}</title>",
        f'<text x="{PAD_L}" y="20" class="t-title">{escape(title)}</text>',
    ]

    # 横のグリッドと目盛り
    for t in _ticks(y_min, y_max):
        y = _y(t, y_min, y_max)
        out.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{PAD_L - 8}" y="{y + 4:.1f}" class="t-tick" '
                   f'text-anchor="end">{escape(fmt(t))}</text>')

    # 縦軸の名前と横軸の目盛り
    out.append(f'<text x="6" y="{PAD_T - 14}" class="t-axis">{escape(y_label)}</text>')
    base = H - PAD_B
    for x, v in zip(px, x_values):
        out.append(f'<text x="{x:.1f}" y="{base + 20}" class="t-tick" '
                   f'text-anchor="middle">{v}</text>')
    out.append(f'<text x="{(PAD_L + W - PAD_R) / 2:.0f}" y="{base + 40}" '
               f'class="t-axis" text-anchor="middle">同時に投げた本数</text>')

    # SLOの線
    if slo is not None and y_min <= slo <= y_max:
        y = _y(slo, y_min, y_max)
        out.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{W - PAD_R}" y2="{y:.1f}" '
                   f'stroke="{SLO}" stroke-width="1.5" stroke-dasharray="6 4"/>')
        label = slo_text or f"基準 {fmt(slo)}"
        out.append(f'<text x="{W - PAD_R}" y="{y - 6:.1f}" class="t-slo" '
                   f'text-anchor="end">{escape(label)}</text>')

    # エラーバー
    if error_bars:
        for x, band in zip(px, error_bars):
            if not band:
                continue
            lo, hi = band
            y1, y2 = _y(lo, y_min, y_max), _y(hi, y_min, y_max)
            out.append(f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" '
                       f'stroke="{POINT}" stroke-width="1.2"/>')
            for y in (y1, y2):
                out.append(f'<line x1="{x - 5:.1f}" y1="{y:.1f}" x2="{x + 5:.1f}" '
                           f'y2="{y:.1f}" stroke="{POINT}" stroke-width="1.2"/>')

    # 折れ線と点
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(px, py))
    out.append(f'<polyline points="{path}" fill="none" stroke="{LINE}" stroke-width="2"/>')
    for x, y, v in zip(px, py, y_values):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{POINT}"/>')
        out.append(f'<text x="{x:.1f}" y="{y - 11:.1f}" class="t-value" '
                   f'text-anchor="middle">{escape(fmt(v))}</text>')

    out.append("</svg>")
    return "\n".join(out)


CSS = f"""
.chart {{ max-width: 100%; height: auto; }}
.chart .t-title {{ font-size: 13px; font-weight: 600; fill: {INK}; }}
.chart .t-tick  {{ font-size: 11px; fill: {MUTED}; }}
.chart .t-axis  {{ font-size: 11px; fill: {MUTED}; }}
.chart .t-value {{ font-size: 10px; fill: {POINT}; }}
.chart .t-slo   {{ font-size: 11px; fill: {SLO}; }}
"""

"""リポジトリの Markdown をHTMLに変換する。

サイトに載せる文章はすべてリポジトリの中にあるものなので、
そこで使われている書き方だけを扱えればよい。
見出し・表・箇条書き・コードブロック・水平線と、
太字・コード片・リンクの3つだけを解釈する。外部のライブラリは使わない。
"""

from __future__ import annotations

import re
from html import escape

HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
TABLE_SEP = re.compile(r"^\|[\s:|-]+\|$")
BULLET = re.compile(r"^(\s*)[-*]\s+(.*)$")
ORDERED = re.compile(r"^(\s*)\d+\.\s+(.*)$")
FENCE = re.compile(r"^```")

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*(.+?)\*\*")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def slug(text: str) -> str:
    plain = re.sub(r"[`*\[\]()]", "", text).strip()
    plain = re.sub(r"\s+", "-", plain)
    return re.sub(r"[^\w\-ぁ-んァ-ヶ一-龥ー]", "", plain)


def inline(text: str, link_map: dict[str, str] | None = None) -> str:
    out = escape(text)
    out = INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)

    def link(m: re.Match) -> str:
        href = m.group(2)
        if link_map:
            href = link_map.get(href, href)
        return f'<a href="{escape(href, quote=True)}">{m.group(1)}</a>'

    return LINK.sub(link, out)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render(md: str, link_map: dict[str, str] | None = None,
           heading_shift: int = 0) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if FENCE.match(line):
            block = []
            i += 1
            while i < n and not FENCE.match(lines[i]):
                block.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + escape("\n".join(block)) + "</code></pre>")
            continue

        if not line.strip():
            i += 1
            continue

        if line.strip() in ("---", "***", "___"):
            out.append("<hr>")
            i += 1
            continue

        m = HEADING.match(line)
        if m:
            level = min(6, len(m.group(1)) + heading_shift)
            text = m.group(2)
            out.append(f'<h{level} id="{escape(slug(text), quote=True)}">'
                       f"{inline(text, link_map)}</h{level}>")
            i += 1
            continue

        # 表
        if line.startswith("|") and i + 1 < n and TABLE_SEP.match(lines[i + 1]):
            header = _cells(line)
            aligns = []
            for spec in _cells(lines[i + 1]):
                if spec.endswith(":") and spec.startswith(":"):
                    aligns.append("center")
                elif spec.endswith(":"):
                    aligns.append("right")
                else:
                    aligns.append("left")
            i += 2
            body = []
            while i < n and lines[i].startswith("|"):
                body.append(_cells(lines[i]))
                i += 1
            head_html = "".join(
                f'<th style="text-align:{a}">{inline(c, link_map)}</th>'
                for c, a in zip(header, aligns))
            rows_html = []
            for row in body:
                cells = "".join(
                    f'<td style="text-align:{a}">{inline(c, link_map)}</td>'
                    for c, a in zip(row, aligns + ["left"] * len(row)))
                rows_html.append(f"<tr>{cells}</tr>")
            out.append(f"<table><thead><tr>{head_html}</tr></thead>"
                       f"<tbody>{''.join(rows_html)}</tbody></table>")
            continue

        # 箇条書き（続きの行はぶら下げる）
        if BULLET.match(line) or ORDERED.match(line):
            ordered = bool(ORDERED.match(line))
            pattern = ORDERED if ordered else BULLET
            body = []
            while i < n:
                m2 = pattern.match(lines[i])
                if m2:
                    body.append([m2.group(2)])
                    i += 1
                elif body and lines[i].startswith(("  ", "\t")) and lines[i].strip():
                    body[-1].append(lines[i].strip())
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            got = "".join(f"<li>{inline(' '.join(x), link_map)}</li>" for x in body)
            out.append(f"<{tag}>{got}</{tag}>")
            continue

        # 段落
        para = []
        while i < n and lines[i].strip() and not lines[i].startswith(("|", "#", "```")) \
                and not BULLET.match(lines[i]) and not ORDERED.match(lines[i]) \
                and lines[i].strip() not in ("---", "***", "___"):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f"<p>{inline(''.join(para), link_map)}</p>")

    return "\n".join(out)

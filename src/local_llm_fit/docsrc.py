"""リポジトリの文書から、サイトに載せる部分を切り出す。

サイトのために新しく文章を書かない。載せるのは
CATALOG.md / README.md / METHOD.md / tasks/*.yaml にあるものだけで、
ここはその切り出し口になる。
"""

from __future__ import annotations

import re
from pathlib import Path

FAMILY = re.compile(r"^## ([A-Z])\. (.+?)（\d+件）\s*$")
HEADING = re.compile(r"^(#{1,4})\s+(.*)$")

COLUMNS = ["id", "work", "grading", "input_len", "output_shape",
           "difficulty", "parts", "state"]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def scenarios(catalog_md: str) -> list[dict]:
    """CATALOG.md の族ごとの表から、シナリオ50件を読む。"""
    out: list[dict] = []
    family_code = family_name = ""
    lines = catalog_md.split("\n")
    for line in lines:
        m = FAMILY.match(line)
        if m:
            family_code, family_name = m.group(1), m.group(2)
            continue
        if not line.startswith("| `"):
            continue
        cells = _cells(line)
        if len(cells) != len(COLUMNS):
            continue
        row = dict(zip(COLUMNS, cells))
        row["id"] = row["id"].strip("`")
        row["state"] = row["state"].strip("*")
        row["family_code"] = family_code
        row["family_name"] = family_name
        out.append(row)
    return out


def section(md: str, heading_text: str) -> str:
    """指定した見出しの本文を、次の同レベル以上の見出しまで返す。"""
    lines = md.split("\n")
    start = None
    level = 0
    for n, line in enumerate(lines):
        m = HEADING.match(line)
        if m and m.group(2).strip() == heading_text:
            start = n + 1
            level = len(m.group(1))
            break
    if start is None:
        return ""
    body = []
    for line in lines[start:]:
        m = HEADING.match(line)
        if m and len(m.group(1)) <= level:
            break
        body.append(line)
    return "\n".join(body).strip("\n")


def heading_slug(md: str, heading_text: str) -> str:
    from . import mdlite
    for line in md.split("\n"):
        m = HEADING.match(line)
        if m and m.group(2).strip() == heading_text:
            return mdlite.slug(m.group(2))
    return ""


def opening(readme_md: str, paragraphs: int = 2) -> str:
    """README の書き出し。何を測るものかを述べている部分。"""
    lines = readme_md.split("\n")
    body: list[list[str]] = []
    started = False
    for line in lines:
        if line.startswith("# "):
            started = True
            continue
        if not started:
            continue
        if line.startswith("## "):
            break
        if line.strip():
            if not body or body[-1] == []:
                body.append([])
            body[-1].append(line.strip())
        elif body and body[-1]:
            body.append([])
        if len([b for b in body if b]) > paragraphs:
            break
    kept = [b for b in body if b][:paragraphs]
    return "\n\n".join("".join(b) for b in kept)


class Docs:
    """サイトの生成で使う文書をまとめて持つ。"""

    def __init__(self, root: Path):
        self.root = root
        self.catalog_md = (root / "tasks" / "CATALOG.md").read_text(encoding="utf-8")
        self.readme_md = (root / "README.md").read_text(encoding="utf-8")
        self.method_md = (root / "METHOD.md").read_text(encoding="utf-8")

    @property
    def scenarios(self) -> list[dict]:
        return scenarios(self.catalog_md)

    @property
    def readme_opening(self) -> str:
        return opening(self.readme_md)

    @property
    def table_legend(self) -> str:
        """表の列が何を指すかの説明。README の「表の読み方」から。"""
        return section(self.readme_md, "表の読み方")

    @property
    def run_howto(self) -> str:
        return section(self.readme_md, "使う")

    @property
    def share_howto(self) -> str:
        return section(self.readme_md, "結果を持ち寄る")

    @property
    def measured_values(self) -> str:
        """p95 や区間の定義。METHOD.md の「測っている値」から。"""
        return section(self.method_md, "測っている値")

    def catalog_anchor(self, heading_text: str) -> str:
        return heading_slug(self.catalog_md, heading_text)

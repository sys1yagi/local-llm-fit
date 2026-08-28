"""日本語の請求書を合成する。

実データは使わない。seed を固定すれば、誰の手元でも同じ入力が出る。
出力は (人が読む請求書テキスト, 正解の構造化データ) の組。
正解は先に作り、そこから文面を組み立てるので、正解が必ず本文と一致する。
"""

from __future__ import annotations

import random

PREFIX = ["株式会社", "合同会社", ""]
SUFFIX = ["株式会社", "商事", "工業", ""]
NAME_A = ["あおぞら", "みどり", "新和", "青葉", "つばさ", "山下", "北斗", "大和", "ひかり", "中央"]
NAME_B = ["商会", "製作所", "システムズ", "物流", "デザイン", "テクノ", "サービス", "電機"]

ITEMS = [
    ("A4コピー用紙（500枚）", 480),
    ("トナーカートリッジ 黒", 12800),
    ("ノート型PC 保守費用", 38000),
    ("会議室 レンタル料", 15000),
    ("Webサイト運用費", 120000),
    ("配送料", 800),
    ("名刺印刷 100枚", 2200),
    ("クラウド利用料（月額）", 46200),
    ("デスクチェア", 24800),
    ("翻訳費用（英日）", 9500),
    ("保守作業 人件費", 55000),
    ("段ボール箱 Lサイズ", 320),
]

TAX_RATE = 0.10


def _company(rng: random.Random) -> str:
    a = rng.choice(NAME_A)
    b = rng.choice(NAME_B)
    if rng.random() < 0.5:
        return f"{rng.choice(PREFIX)}{a}{b}".strip()
    return f"{a}{b}{rng.choice(SUFFIX)}".strip()


def _date(rng: random.Random) -> tuple[str, str]:
    """発行日と支払期限。支払期限は翌月末に寄せる。"""
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    issue = f"2026-{month:02d}-{day:02d}"
    due_month = month + 1
    due_year = 2026
    if due_month > 12:
        due_month = 1
        due_year = 2027
    last = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[due_month]
    due = f"{due_year}-{due_month:02d}-{last:02d}"
    return issue, due


def _record(rng: random.Random, index: int) -> dict:
    n_items = rng.randint(1, 4)
    picked = rng.sample(ITEMS, n_items)
    items = []
    for name, unit_price in picked:
        qty = rng.randint(1, 30) if unit_price < 5000 else rng.randint(1, 5)
        items.append({
            "name": name,
            "quantity": qty,
            "unit_price": unit_price,
            "amount": qty * unit_price,
        })
    subtotal = sum(i["amount"] for i in items)
    tax = int(subtotal * TAX_RATE)
    issue, due = _date(rng)
    return {
        "invoice_number": f"INV-2026-{index + 1:04d}",
        "issue_date": issue,
        "due_date": due,
        "customer": _company(rng),
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
    }


def _yen(n: int) -> str:
    return f"{n:,}"


def _render_table(r: dict, issuer: str) -> str:
    lines = [
        "請 求 書",
        "",
        f"{r['customer']} 御中",
        "",
        f"請求書番号: {r['invoice_number']}",
        f"発行日: {r['issue_date']}",
        f"お支払期限: {r['due_date']}",
        "",
        "品名                              数量      単価        金額",
        "-" * 62,
    ]
    for i in r["items"]:
        lines.append(f"{i['name']:<32}{i['quantity']:>4}{_yen(i['unit_price']):>10}{_yen(i['amount']):>12}")
    lines += [
        "-" * 62,
        f"{'小計':>44}{_yen(r['subtotal']):>12}",
        f"{'消費税(10%)':>42}{_yen(r['tax']):>12}",
        f"{'合計':>44}{_yen(r['total']):>12}",
        "",
        f"発行元: {issuer}",
    ]
    return "\n".join(lines)


def _render_lines(r: dict, issuer: str) -> str:
    lines = [
        f"{issuer}",
        f"請求書 No.{r['invoice_number']}",
        f"{r['issue_date']} 発行 / お支払期限 {r['due_date']}",
        "",
        f"宛先: {r['customer']} 様",
        "",
        "【ご請求明細】",
    ]
    for n, i in enumerate(r["items"], 1):
        lines.append(
            f"({n}) {i['name']} … {i['quantity']}個 × {_yen(i['unit_price'])}円 = {_yen(i['amount'])}円"
        )
    lines += [
        "",
        f"小計 {_yen(r['subtotal'])}円",
        f"消費税 {_yen(r['tax'])}円",
        f"ご請求金額 {_yen(r['total'])}円",
    ]
    return "\n".join(lines)


def _render_labeled(r: dict, issuer: str) -> str:
    body = [
        "=== 請求書 ===",
        f"[発行元] {issuer}",
        f"[請求先] {r['customer']}御中",
        f"[番号] {r['invoice_number']}",
        f"[発行日] {r['issue_date']}",
        f"[期限] {r['due_date']}",
        "",
        "[明細]",
    ]
    for i in r["items"]:
        body.append(
            f"  品名={i['name']} / 数量={i['quantity']} / 単価={_yen(i['unit_price'])} / 金額={_yen(i['amount'])}"
        )
    body += [
        "",
        f"[小計] {_yen(r['subtotal'])}",
        f"[税] {_yen(r['tax'])}",
        f"[総額] {_yen(r['total'])}",
    ]
    return "\n".join(body)


RENDERERS = [_render_table, _render_lines, _render_labeled]


def generate(samples: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for i in range(samples):
        record = _record(rng, i)
        issuer = _company(rng)
        render = RENDERERS[i % len(RENDERERS)]
        out.append({
            "id": f"{i:03d}",
            "input": render(record, issuer),
            "truth": record,
        })
    return out

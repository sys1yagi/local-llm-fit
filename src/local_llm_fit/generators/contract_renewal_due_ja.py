"""契約の一覧と基準日を合成し、期限が近いものを挙げさせる。

難所は自動更新の扱い。自動更新のある契約は、満了日そのものではなく
「満了日の◯日前」が判断の期限になる。満了日だけを見て90日以内かを
判定すると、自動更新のある契約を取りこぼす。

正解は期限が基準日から90日以内の契約。行番号によらず同じ。
表の型・日付の書き方・添えものの列だけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import companies, dates

WINDOW_DAYS = 90
NOTICE_CHOICES = [30, 60, 90, 120]
KINDS = ["業務委託", "賃貸借", "保守", "ライセンス", "売買基本"]


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/crd/truth/{index}")
    basis = dates.pick(rng, months=(2, 9))
    n = rng.randint(18, 22)

    rows = []
    for base, pos in companies.pick_with_position(rng, n):
        auto = rng.random() < 0.55
        notice = rng.choice(NOTICE_CHOICES) if auto else 0
        # 期限が基準日の前後に散らばるように満了日を置く
        offset = rng.randint(-30, 260)
        expiry = dates.add_days(basis, offset + (notice if auto else 0))
        deadline = dates.add_days(expiry, -notice) if auto else expiry
        rows.append({
            "party": companies.canonical(base, pos),
            "kind": rng.choice(KINDS),
            "expiry": expiry,
            "auto": auto,
            "notice": notice,
            "deadline": deadline,
        })

    limit = dates.add_days(basis, WINDOW_DAYS)
    hit = [r for r in rows if basis <= r["deadline"] <= limit]
    hit.sort(key=lambda r: (r["deadline"], rows.index(r)))

    return {"basis": basis, "rows": rows, "hit": hit}


DATE_FORMATS = [dates.ja, dates.slash, dates.dot]


def _render(t: dict, template: int, dfmt, show_kind: bool) -> str:
    head = f"基準日: {dfmt(t['basis'])}"
    out = [head, ""]
    if template == 0:
        cols = "契約先\t種別\t満了日\t自動更新\t通知期間" if show_kind \
            else "契約先\t満了日\t自動更新\t通知期間"
        out.append(cols)
        out.append("-" * 60)
        for r in t["rows"]:
            auto = f"あり（{r['notice']}日前までに通知）" if r["auto"] else "なし"
            cells = [r["party"]]
            if show_kind:
                cells.append(r["kind"])
            cells += [dfmt(r["expiry"]), auto.split("（")[0],
                      f"{r['notice']}日前" if r["auto"] else "-"]
            out.append("\t".join(cells))
    else:
        out.append("【契約一覧】")
        for n, r in enumerate(t["rows"], 1):
            kind = f"／種別 {r['kind']}" if show_kind else ""
            auto = (f"自動更新あり（満了の{r['notice']}日前までに不更新の通知が必要）"
                    if r["auto"] else "自動更新なし")
            out.append(f"{n}. {r['party']}{kind}／満了日 {dfmt(r['expiry'])}／{auto}")
    return "\n".join(out)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, (i + row) % 2,
                             DATE_FORMATS[(i + row) % len(DATE_FORMATS)],
                             (i + row) % 2 == 0),
            "truth": {
                "items": [{"party": r["party"], "deadline": dates.iso(r["deadline"])}
                          for r in t["hit"]],
            },
        })
    return out

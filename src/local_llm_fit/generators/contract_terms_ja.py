"""業務委託契約書を合成し、基本条項を拾わせる。

難所は末尾の特約。本則で決めた解約予告の日数や委託料を、特約が上書きする
ことがある。上書きされた場合は特約の値が答えになる。
本則だけを読んで止まると外れ、特約だけを見ても上書きの無い回で外れる。

正解は最終的に適用される6項目。行番号によらず同じ。
条文の型・日付と金額の書き方・埋め草の条の並びだけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import companies, dates, money

NOTICE_CHOICES = [30, 60, 90]

FILLER_CLAUSES = [
    ("秘密保持", ("甲および乙は、本契約に関して知り得た相手方の営業上または技術上の"
                 "情報を、相手方の書面による事前の承諾なく第三者に開示してはならない。"
                 "本条の定めは本契約の終了後も三年間存続する。")),
    ("再委託", ("乙は、甲の書面による事前の承諾を得た場合を除き、本業務の全部または"
               "一部を第三者に再委託してはならない。承諾を得て再委託した場合であっても、"
               "乙は再委託先の行為について甲に対し責任を負う。")),
    ("知的財産権", ("本業務の遂行の過程で生じた成果物に関する著作権その他の知的財産権は、"
                   "委託料の完済をもって乙から甲に移転する。ただし乙が本契約以前から"
                   "保有していた権利はこの限りでない。")),
    ("反社会的勢力の排除", ("甲および乙は、自己または自己の役員が暴力団その他の反社会的"
                           "勢力に該当しないことを表明し、将来にわたって該当しないことを"
                           "確約する。これに反した場合、相手方は催告を要せず直ちに本契約を"
                           "解除することができる。")),
    ("損害賠償", ("甲または乙が本契約に違反し相手方に損害を与えた場合、当該当事者は"
                 "その損害を賠償する。ただし賠償の額は、本契約に基づき乙が受領した"
                 "委託料の総額を上限とする。")),
    ("不可抗力", ("天災地変その他当事者の責めに帰すことのできない事由により本業務の"
                 "遂行が困難となった場合、甲乙協議のうえ本契約の取扱いを定める。")),
    ("権利義務の譲渡禁止", ("甲および乙は、相手方の書面による事前の承諾なく、本契約上の"
                           "地位ならびに本契約から生じる権利および義務を第三者に譲渡し、"
                           "または担保に供してはならない。")),
    ("管轄", ("本契約に関して生じた紛争については、甲の本店所在地を管轄する地方裁判所を"
             "第一審の専属的合意管轄裁判所とする。")),
]

WORK_ITEMS = [
    "受注管理システムの保守および運用支援",
    "販売代理店向け資料の制作および更新",
    "社内ヘルプデスクの一次対応",
    "検査工程の記録データの整理および報告",
    "採用サイトの企画および運用",
]


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/ct/truth/{index}")
    (a_base, a_pos), (b_base, b_pos) = companies.pick_with_position(rng, 2)
    start = dates.pick(rng, months=(1, 10))
    start = start.replace(day=1)
    end = dates.add_days(dates.add_months(start, 12), -1)

    base_fee = money.yen(rng, 200_000, 1_500_000, 10_000)
    base_notice = rng.choice(NOTICE_CHOICES)

    # 特約による上書き。なし / 解約予告 / 委託料 のいずれか。
    override = rng.choices(["none", "notice", "fee"], weights=[4, 4, 3])[0]
    fee, notice = base_fee, base_notice
    if override == "notice":
        notice = rng.choice([n for n in NOTICE_CHOICES if n != base_notice])
    elif override == "fee":
        fee = money.yen(rng, 200_000, 1_500_000, 10_000)
        while fee == base_fee:
            fee = money.yen(rng, 200_000, 1_500_000, 10_000)

    return {
        "party_a": companies.canonical(a_base, a_pos),
        "party_b": companies.canonical(b_base, b_pos),
        "start": start,
        "end": end,
        "base_fee": base_fee,
        "base_notice": base_notice,
        "override": override,
        "fee": fee,
        "notice": notice,
        "work": rng.choice(WORK_ITEMS),
        "fillers": rng.sample(FILLER_CLAUSES, 7),
    }


DATE_FORMATS = [dates.ja, dates.wareki, dates.slash]
MONEY_FORMATS = [money.comma, money.with_unit, money.plain]


def _render(t: dict, template: int, dfmt, mfmt) -> str:
    a, b = t["party_a"], t["party_b"]
    body = [
        ("目的", (f"{a}（以下「甲」という。）と{b}（以下「乙」という。）とは、"
                  "甲が乙に委託する業務について、以下のとおり業務委託契約を締結する。")),
        ("委託業務", f"甲は乙に対し、{t['work']}を委託し、乙はこれを受託する。"),
        ("契約期間", f"本契約の期間は、{dfmt(t['start'])}から{dfmt(t['end'])}までとする。"),
        ("委託料", f"本業務の委託料は月額{mfmt(t['base_fee'])}（消費税別）とする。"),
        ("支払方法", ("甲は前条の委託料を、当月分を翌月末日限り、乙の指定する銀行口座に"
                      "振り込む方法により支払う。振込手数料は甲の負担とする。")),
        ("解約", ("甲または乙は、本契約を解約しようとするときは、"
                  f"{t['base_notice']}日前までに書面により相手方に通知しなければならない。")),
    ]
    body += t["fillers"]

    special = []
    if t["override"] == "notice":
        special.append("解約に関する条の定めにかかわらず、本契約における解約の予告は"
                       f"{t['notice']}日前までとする。")
    elif t["override"] == "fee":
        special.append("委託料に関する条の定めにかかわらず、本契約における委託料は"
                       f"月額{mfmt(t['fee'])}（消費税別）とする。")
    special.append("本契約に定めのない事項および本契約の解釈に疑義を生じた事項については、"
                   "甲乙誠実に協議のうえこれを定める。")

    lines = ["業務委託契約書", ""]
    if template == 0:
        for n, (title, text) in enumerate(body, 1):
            lines += [f"第{n}条（{title}）", text, ""]
        lines += [f"第{len(body) + 1}条（特約）"]
        lines += special + [""]
    else:
        for n, (title, text) in enumerate(body, 1):
            lines += [f"{n}. {title}　{text}", ""]
        lines += [f"{len(body) + 1}. 特約"]
        lines += [f"　　{s}" for s in special] + [""]

    lines += [("以上、本契約の成立を証するため本書二通を作成し、"
               "甲乙記名押印のうえ各一通を保有する。"),
              "", dfmt(t["start"]), f"甲　{a}", f"乙　{b}"]
    return "\n".join(lines)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        # 書き方の割り当ては (サンプル番号 + 行番号) で回す。
        # どの行でも和暦・西暦・スラッシュが同じ比率で混ざり、行ごとの難易度が偏らない。
        dfmt = DATE_FORMATS[(i + row) % len(DATE_FORMATS)]
        mfmt = MONEY_FORMATS[(i + row) % len(MONEY_FORMATS)]
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, (i + row) % 2, dfmt, mfmt),
            "truth": {
                "party_a": t["party_a"],
                "party_b": t["party_b"],
                "start_date": dates.iso(t["start"]),
                "end_date": dates.iso(t["end"]),
                "monthly_fee": t["fee"],
                "termination_notice_days": t["notice"],
                "items": [],
            },
        })
    return out

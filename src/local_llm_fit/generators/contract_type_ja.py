"""契約書の抜粋を合成し、種別を1語で答えさせる。

表題は6割の回でわざと中身と違う種別にしてある。表題を読んだだけでは
当たらないので、定められている義務の内容を見る必要がある。

正解は中身から決まる種別。行番号によらず同じ。
条文の型・当事者の書き方・日付と金額の書き方だけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import companies, dates, money

TYPES = ["売買契約", "業務委託契約", "賃貸借契約", "秘密保持契約", "ライセンス契約"]

# 種別ごとの、それと分かる条文。金額の意味も種別で変える。
CLAUSES = {
    "売買契約": {
        "money": "代金",
        "body": [
            "甲は乙に対し、本商品を売り渡し、乙はこれを買い受ける。",
            "本商品の所有権は、乙が代金の全額を支払った時に甲から乙に移転する。",
            "本商品の引渡しは、甲が乙の指定する場所に搬入する方法により行う。",
            "乙は、引渡しを受けた日から14日以内に検査を行い、数量の不足または品質の不適合を発見したときは直ちに甲に通知する。",
        ],
    },
    "業務委託契約": {
        "money": "委託料",
        "body": [
            "甲は乙に対し、本業務を委託し、乙はこれを受託する。",
            "乙は、善良な管理者の注意をもって本業務を遂行し、毎月末日までに当月の作業内容を甲に報告する。",
            "乙は、甲の書面による事前の承諾なく本業務を第三者に再委託してはならない。",
            "本業務の遂行にあたり乙が使用する者は、乙の指揮命令に服するものとし、甲乙間に雇用関係は生じない。",
        ],
    },
    "賃貸借契約": {
        "money": "賃料",
        "body": [
            "甲は乙に対し、本物件を賃貸し、乙はこれを賃借する。",
            "乙は、本物件を事務所としてのみ使用し、他の用途に使用してはならない。",
            "乙は、本契約の締結時に敷金として賃料の2か月分を甲に預託する。",
            "本契約が終了したときは、乙は自己の費用で本物件を原状に復して甲に明け渡す。",
        ],
    },
    "秘密保持契約": {
        "money": None,
        "body": [
            "甲および乙は、相手方から開示を受けた秘密情報を、本目的以外の目的に使用してはならない。",
            "甲および乙は、秘密情報を相手方の書面による事前の承諾なく第三者に開示または漏洩してはならない。",
            "甲および乙は、相手方の請求があったときは、秘密情報を記録した媒体を速やかに返還または破棄する。",
            "本契約は、秘密情報の開示に関する義務のみを定めるものであり、いずれの当事者にも取引を行う義務を課すものではない。",
        ],
    },
    "ライセンス契約": {
        "money": "実施料",
        "body": [
            "甲は乙に対し、本ソフトウェアを日本国内において使用する非独占的な権利を許諾する。",
            "乙は、本ソフトウェアを複製し、改変し、または逆コンパイルしてはならない。",
            "本ソフトウェアに関する著作権その他の知的財産権は、本契約によって乙に移転するものではなく、引き続き甲に帰属する。",
            "乙は、許諾された使用の範囲を超えて第三者に再許諾してはならない。",
        ],
    },
}

COMMON = [
    "甲および乙は、本契約に関して知り得た相手方の情報を、相手方の承諾なく第三者に開示してはならない。",
    "甲または乙が本契約に違反したときは、相手方は相当の期間を定めて催告のうえ、本契約を解除することができる。",
    "本契約に関して生じた紛争については、甲の本店所在地を管轄する地方裁判所を第一審の専属的合意管轄裁判所とする。",
    "本契約に定めのない事項については、甲乙誠実に協議のうえこれを定める。",
    "甲および乙は、相手方の書面による事前の承諾なく、本契約上の地位ならびに本契約から生じる権利および義務を第三者に譲渡し、または担保に供してはならない。",
    "甲および乙は、自己または自己の役員が暴力団その他の反社会的勢力に該当しないことを表明し、将来にわたって該当しないことを確約する。",
    "天災地変その他当事者の責めに帰すことのできない事由により本契約の履行が困難となった場合、甲乙協議のうえ本契約の取扱いを定める。",
    "本契約の変更は、甲乙が記名押印した書面によらなければ効力を生じない。",
    "甲または乙が本契約に違反し相手方に損害を与えた場合、当該当事者はその損害を賠償する。",
    "本契約の各条項の一部が無効とされた場合であっても、残余の条項の効力は影響を受けない。",
]


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/cty/truth/{index}")
    actual = rng.choice(TYPES)
    # 6割は表題と中身をずらす
    if rng.random() < 0.6:
        title_type = rng.choice([t for t in TYPES if t != actual])
    else:
        title_type = actual

    (a_base, a_pos), (b_base, b_pos) = companies.pick_with_position(rng, 2)
    return {
        "actual": actual,
        "title": title_type,
        "party_a": companies.canonical(a_base, a_pos),
        "party_b": companies.canonical(b_base, b_pos),
        "signed": dates.pick(rng, months=(1, 12)),
        "amount": money.yen(rng, 80_000, 2_000_000, 10_000),
        "commons": rng.sample(COMMON, 7),
    }


DATE_FORMATS = [dates.ja, dates.wareki, dates.slash]
MONEY_FORMATS = [money.comma, money.with_unit, money.plain]


def _render(t: dict, template: int, dfmt, mfmt) -> str:
    spec = CLAUSES[t["actual"]]
    a, b = t["party_a"], t["party_b"]
    body = list(spec["body"])
    if spec["money"]:
        body.insert(2, f"本契約の{spec['money']}は{mfmt(t['amount'])}（消費税別）とする。")

    lines = [f"{t['title']}書", "",
             f"{a}（以下「甲」という。）と{b}（以下「乙」という。）とは、次のとおり契約を締結する。",
             ""]
    clauses = body + t["commons"]
    for n, text in enumerate(clauses, 1):
        if template == 0:
            lines += [f"第{n}条", text, ""]
        else:
            lines += [f"（{n}）{text}"]
    lines += ["", dfmt(t["signed"]), f"甲　{a}", f"乙　{b}"]
    return "\n".join(lines)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, (i + row) % 2,
                             DATE_FORMATS[(i + row) % len(DATE_FORMATS)],
                             MONEY_FORMATS[(i + row) % len(MONEY_FORMATS)]),
            "truth": {"contract_type": t["actual"], "items": []},
        })
    return out

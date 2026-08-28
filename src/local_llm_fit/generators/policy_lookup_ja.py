"""社内規程集を万字ぶん合成し、質問に該当する規程と数値を引かせる。

難所は似た規程の混同。育児休業と介護休業、慶弔休暇と特別休暇のように、
条の並びも言い回しもほとんど同じ規程を隣に置いてある。
数値だけを拾うと、別の規程の同じ位置にある数値を返してしまう。

正解は規程名・条番号・数値の3つ。行番号によらず同じ。
条文の言い回しの型・埋め草の条・規程の並び順だけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import dates, depts, quantities

# (規程名, 対になる紛らわしい規程名)
PAIRS = [
    ("育児休業規程", "介護休業規程"),
    ("慶弔休暇規程", "特別休暇規程"),
    ("国内出張旅費規程", "海外出張旅費規程"),
    ("在宅勤務規程", "サテライトオフィス勤務規程"),
]

# 各規程に共通で並ぶ条の見出し。ここの「申請」条に数値を入れる。
HEADINGS = [
    "目的", "適用範囲", "定義", "申請", "承認", "期間", "給与の取扱い",
    "社会保険の取扱い", "報告", "取消し", "記録の保存", "改廃",
    "業務の引継ぎ", "代替要員", "復帰後の配置", "教育訓練", "相談窓口", "苦情の処理",
]

FILLER = {
    "目的": "本規程は、{name}に関する取扱いを定め、社員の就業と生活の両立を図ることを目的とする。",
    "適用範囲": "本規程は、{dept}を含むすべての部署に所属する社員に適用する。ただし、在籍期間が6か月に満たない者については、会社の承認を得た場合に限り適用する。",
    "定義": "本規程において{name}とは、前条の目的のために会社が認める就業上の取扱いをいう。",
    "承認": "前条の申請を受けた所属長は、業務への影響を確認のうえ、速やかに人事部に回付し、人事部長がこれを承認する。",
    "期間": "本規程に基づく取扱いの期間は、原則として1回につき{months}か月を上限とする。やむを得ない事情があるときは、会社の承認を得て延長することができる。",
    "給与の取扱い": "本規程に基づく期間中の給与は、就業規則および給与規程の定めるところによる。会社は、当該期間中の賃金の支払いについて別途通知する。",
    "社会保険の取扱い": "本規程に基づく期間中の社会保険料の取扱いは、関係法令および保険者の定めるところによる。免除の申出は人事部を通じて行う。",
    "報告": "本規程の適用を受けた社員は、当該事由が終了した日から{report}日以内に、所定の様式により所属長へ報告しなければならない。",
    "取消し": "申請の内容に虚偽があったとき、または申請の前提となる事情が消滅したときは、会社は承認を取り消すことができる。",
    "記録の保存": "会社は、本規程に基づく申請および承認に関する記録を、当該事由の終了後3年間保存する。",
    "改廃": "本規程の改廃は、人事部の起案に基づき、取締役会の決議によって行う。",
    "業務の引継ぎ": "本規程の適用を受ける社員は、その開始前に、担当している業務の状況、関係者の連絡先および未処理の案件を所定の様式に記載し、所属長の指定する者に引き継がなければならない。引継ぎが完了しない場合であっても、開始日を理由なく延期することはできない。",
    "代替要員": "所属長は、本規程の適用により業務に支障が生じるおそれがあるときは、あらかじめ人事部と協議し、部内での配置換えまたは臨時要員の手配その他必要な措置を講じるものとする。措置に要する費用の負担は、当該部署の予算による。",
    "復帰後の配置": "本規程の適用を受けた社員が復帰するときの配置は、原則として適用開始前と同一の職務とする。ただし、組織の改編その他やむを得ない事情があるときは、会社は本人の意向を聴いたうえで、これと異なる職務に配置することができる。",
    "教育訓練": "会社は、本規程の適用を受けた社員が円滑に復帰できるよう、必要に応じて業務上の変更点に関する説明の機会および教育訓練を提供する。当該教育訓練に要する時間は勤務時間として取り扱う。",
    "相談窓口": "本規程に関する相談は人事部に置く相談窓口が受け付ける。相談の内容および相談したことを理由として、当該社員に不利益な取扱いをしてはならない。相談の記録は担当者以外が閲覧できないよう管理する。",
    "苦情の処理": "本規程の運用に関して苦情の申出があったときは、人事部長は事実関係を調査し、申出を受けた日から30日以内に処理の結果を申出人に通知する。調査にあたっては、関係者の秘密に配慮しなければならない。",
}

APPLY = [
    "本規程の適用を受けようとする社員は、その開始を希望する日の{days}日前までに、所定の様式により所属長に申請しなければならない。",
    "社員が本規程の適用を希望するときは、適用開始予定日の{days}日前までに、書面をもって所属長へ申し出るものとする。",
]

QUESTION = "「{name}」の適用を受けるには、開始予定日の何日前までに申請が必要ですか。"


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/pl/truth/{index}")
    pairs = rng.sample(PAIRS, len(PAIRS))
    policies = []
    for a, b in pairs:
        for name in (a, b):
            policies.append({
                "name": name,
                "days": quantities.days(rng, [3, 5, 7, 10, 14, 20, 30, 45, 60]),
                "months": rng.choice([1, 3, 6, 12]),
                "report": rng.choice([3, 5, 7, 10]),
                "dept": depts.division(rng),
                "revised": dates.pick(rng, months=(1, 12)),
            })
    # 同じペアの2本が同じ日数にならないようにする（答えが一意でなくなるため）
    for k in range(0, len(policies), 2):
        while policies[k]["days"] == policies[k + 1]["days"]:
            policies[k + 1]["days"] = quantities.days(
                rng, [3, 5, 7, 10, 14, 20, 30, 45, 60])

    target = rng.choice(policies)
    article = HEADINGS.index("申請") + 1
    return {"policies": policies, "target": target, "article": article}


def _render(t: dict, order: list[int], apply_style: int) -> str:
    out = [QUESTION.format(name=t["target"]["name"]), "",
           "――――― 社内規程集 ―――――", ""]
    for k in order:
        p = t["policies"][k]
        out.append(f"■ {p['name']}")
        out.append("")
        for n, head in enumerate(HEADINGS, 1):
            if head == "申請":
                text = APPLY[apply_style].format(days=p["days"])
            else:
                text = FILLER[head].format(name=p["name"], dept=p["dept"],
                                           months=p["months"], report=p["report"])
            out.append(f"第{n}条（{head}）")
            out.append(text)
            out.append("")
        out.append(f"（{dates.ja(p['revised'])} 改正）")
        out.append("")
    return "\n".join(out)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        rng = random.Random(f"{seed}/pl/surface/{i}/{row}")
        order = list(range(len(t["policies"])))
        rng.shuffle(order)
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, order, (i + row) % len(APPLY)),
            "truth": {
                "policy_name": t["target"]["name"],
                "article": f"第{t['article']}条",
                "days": t["target"]["days"],
                "items": [],
            },
        })
    return out

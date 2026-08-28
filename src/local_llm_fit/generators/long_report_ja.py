"""長い業務日報のまとめを合成する。

実データは使わない。seed を固定すれば、誰の手元でも同じ文書が出る。
出力は (人が読む日報のまとまり, 正解の構造化データ) の組。

狙いは、答えが文書の離れた場所に散らばっている状態を作ること。
先に「決定の内容」を決め、それを本文のどこに置くかを乱数で散らすので、
前の方にあるか後ろの方にあるかで取りこぼしが変わるなら、それが正答率に出る。

紛らわしさは2つの形で入れている。
  1. 同じ案件番号の「当初見積」の行を、決定の行から離れた場所に置く。
     金額も日付も違うので、決定の行を読まずに拾うと外れる
  2. 似た書き方で金額と日付を持つ、無関係な案件の行を大量に混ぜる
"""

from __future__ import annotations

import random

DEPTS = ["営業一部", "営業二部", "管理部", "開発部", "品質保証部",
         "購買部", "人事部", "情報システム部", "物流部", "総務部"]

FAMILY = ["山下", "北村", "大和田", "篠原", "青木", "中川", "藤井", "小島",
          "森田", "岩瀬", "浜口", "柏木", "早乙女", "都築", "宮下"]

STATUSES = ["承認", "条件付き承認", "差し戻し"]

PROJECT_TOPICS = [
    "受注管理システムの改修",
    "倉庫棟の空調更新",
    "採用サイトのリニューアル",
    "検査装置の入れ替え",
    "社内ヘルプデスクの外部委託",
    "配送ルートの見直し",
    "研修プログラムの再構築",
    "会計システムの移行",
    "工場ラインの安全対策",
    "販売代理店向け資料の刷新",
    "在庫管理端末の更新",
    "オフィス移転に伴う什器調達",
]

FILLER_SENTENCES = [
    "午前中は定例会に出席し、前週分の進捗を共有した。",
    "取引先からの問い合わせに対応し、回答期限を翌営業日と伝えた。",
    "見積書の様式が古いという指摘があり、管理部に確認を依頼した。",
    "先方の担当者が交代したため、引き継ぎの場を設けることになった。",
    "検収の日程が先方都合で1週間後ろにずれる見込みとなった。",
    "納品物の一部に軽微な不備が見つかり、差し替えの手配を行った。",
    "月次の集計作業を実施し、想定との差異を洗い出した。",
    "共有フォルダの整理を行い、旧年度の資料を退避した。",
    "新任者向けの手順書を更新し、レビューを依頼した。",
    "設備点検の立ち会いを行い、異常がないことを確認した。",
    "問い合わせ件数が前月比で増えており、要因を分析中である。",
    "外部委託先との定例を実施し、来月の作業計画を確認した。",
    "社内アンケートの回収状況を確認し、未回答部署へ再度依頼した。",
    "経費精算の締め切りについて部内へ周知した。",
    "在庫の実地棚卸を行い、帳簿との差を報告した。",
    "採用面接を2件実施し、評価表を人事部へ提出した。",
    "システムの計画停止について関係部署へ事前連絡を行った。",
    "配送遅延の報告があり、原因の切り分けを進めている。",
    "資料の体裁について指摘を受け、次回までに修正することとした。",
    "安全講習の受講状況を取りまとめ、未受講者へ案内した。",
]


def _person(rng: random.Random) -> str:
    return rng.choice(FAMILY)


def _date_str(rng: random.Random, month_range: tuple[int, int]) -> tuple[str, str]:
    """(正解に入れる YYYY-MM-DD, 本文に書く「2026年5月20日」) を返す。"""
    month = rng.randint(*month_range)
    day = rng.randint(1, 28)
    return f"2026-{month:02d}-{day:02d}", f"2026年{month}月{day}日"


def _yen(n: int) -> str:
    return f"{n:,}"


def _needles(rng: random.Random, count: int) -> list[dict]:
    """先に「決定の内容」を作る。本文はこれを見て書く。"""
    codes = rng.sample(range(1000, 9999), count)
    topics = rng.sample(PROJECT_TOPICS, count)
    out = []
    for code, topic in zip(codes, topics):
        amount = rng.randrange(180_000, 4_800_000, 10_000)
        iso, written = _date_str(rng, (5, 9))
        out.append({
            "code": f"PRJ-{code}",
            "topic": topic,
            "amount": amount,
            "date": iso,
            "date_written": written,
            "status": rng.choice(STATUSES),
            # 当初見積。決定額とは必ず違う値にする
            "draft_amount": amount + rng.randrange(30_000, 900_000, 10_000),
            "draft_written": _date_str(rng, (2, 4))[1],
        })
    return out


def _entry(rng: random.Random, day_index: int, body: list[str]) -> str:
    month = 4 + day_index // 22
    day = day_index % 22 + 1
    head = (f"── 2026年{month}月{day}日 業務日報 "
            f"／ {rng.choice(DEPTS)} ／ 記入者: {_person(rng)} ──")
    return head + "\n" + "\n".join(body) + "\n"


def _filler_body(rng: random.Random) -> list[str]:
    return [rng.choice(FILLER_SENTENCES) for _ in range(rng.randint(4, 7))]


def _decoy_line(rng: random.Random) -> str:
    """無関係な案件の、決定の行とよく似た書き方の1行。"""
    code = f"PRJ-{rng.randint(1000, 9999)}"
    amount = rng.randrange(150_000, 5_000_000, 10_000)
    _, written = _date_str(rng, (5, 9))
    verb = rng.choice(["継続審議となった", "次回に持ち越しとなった",
                       "担当部署へ差し戻された", "資料の追加提出を求められた"])
    return (f"{code}（{rng.choice(PROJECT_TOPICS)}）について、"
            f"想定費用 {_yen(amount)}円、実施時期 {written} の案が示されたが、{verb}。")


def _decision_line(n: dict) -> str:
    return (f"{n['code']}（{n['topic']}）について審議し、"
            f"最終決定額 {_yen(n['amount'])}円、決定実施日 {n['date_written']} で"
            f"{n['status']}となった。")


def _draft_line(n: dict) -> str:
    return (f"{n['code']}（{n['topic']}）の当初見積額は {_yen(n['draft_amount'])}円、"
            f"見積時点の想定実施日は {n['draft_written']} である。"
            f"金額と日程は今後の審議で変わる見込み。")


def _build_document(rng: random.Random, needles: list[dict], doc_chars: int) -> str:
    """埋め草の日報を必要な長さまで並べ、その中に決定の行と見積の行を散らす。"""
    entries: list[list[str]] = []
    total = 0
    day = 0
    while total < doc_chars:
        body = _filler_body(rng)
        if rng.random() < 0.35:
            body.insert(rng.randrange(len(body) + 1), _decoy_line(rng))
        entries.append(body)
        total += sum(len(s) for s in body) + 60
        day += 1

    # 決定の行は文書全体に散らす。前方・中央・後方が seed でばらけるようにする。
    # 並べ替えないので、案件番号を並べた順と本文に出てくる順は一致しない。
    n_entries = len(entries)
    slots = rng.sample(range(n_entries), min(len(needles), n_entries))
    for needle, slot in zip(needles, slots):
        body = entries[slot]
        body.insert(rng.randrange(len(body) + 1), _decision_line(needle))

        # 当初見積の行は、決定の行から離れた場所に置く
        far = [i for i in range(n_entries) if abs(i - slot) > n_entries // 4]
        if far:
            other = entries[rng.choice(far)]
            other.insert(rng.randrange(len(other) + 1), _draft_line(needle))

    return "\n".join(_entry(rng, i, b) for i, b in enumerate(entries))


def generate(samples: int, seed: int, doc_chars: int = 20000,
             needles: int = 6) -> list[dict]:
    rng = random.Random(seed)
    out = []
    for i in range(samples):
        picked = _needles(rng, needles)
        document = _build_document(rng, picked, doc_chars)

        # 抜き出す対象は本文中の案件番号で指定する。
        # 並び順もここで固定するので、採点で順不同を扱う必要がない。
        codes = "\n".join(n["code"] for n in picked)
        body = (f"【対象の案件番号】\n{codes}\n\n"
                f"【業務日報】\n{document}")

        truth = {
            "items": [
                {"code": n["code"], "amount": n["amount"],
                 "date": n["date"], "status": n["status"]}
                for n in picked
            ]
        }
        out.append({
            "id": f"{i:03d}",
            "input": body,
            "truth": truth,
            # 採点には使わない。あとで「答えの位置と正答率」を見るための記録。
            "meta": {"doc_chars": len(document), "needles": len(picked)},
        })
    return out

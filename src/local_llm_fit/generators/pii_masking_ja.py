"""社外に出す前の議事録・記録を合成する。個人情報だけが埋まっている。

正解は「伏せたあとの全文」。先に伏せ字の入った全文を作り、伏せ字の位置に
実際の値を差し込んだものを入力にする。この順序なので、伏せる場所と正解が
食い違わない。

行ごとに引き直すのは、差し込む値（人名・電話番号・メールアドレス・住所）
だけにしてある。どれも正解では同じ伏せ字に潰れるので、行をまたいで正解が
動かない。社名・部署・日付・金額は伏せないので、行によらず同じ。

難所は人名と社名の見分け。本文に出てくる社名は、頭が人の姓と同じもの
（山下テクノ、早川精機など）を選び、同じ姓の人物も一緒に出す。名前らしい
文字列をまとめて伏せると、社名まで潰れて不正解になる。
"""

from __future__ import annotations

import random

from ._lib import addresses, companies, dates, depts, emails, money, people, phones

NAME = "〔氏名〕"
PHONE = "〔電話番号〕"
MAIL = "〔メールアドレス〕"
ADDRESS = "〔住所〕"


def _truth_parts(seed: int, index: int) -> dict:
    """伏せない側。行番号によらず同じ。"""
    rng = random.Random(f"{seed}/pii/truth/{index}")
    surname, base = companies.surname_headed(rng, 1)[0]
    position = rng.choice([companies.FRONT, companies.BACK])
    other = rng.choice([b for b in companies.BASE if b != base])
    meeting = dates.pick(rng)
    return {
        "template": index % 3,
        "surname": surname,
        "company_a": companies.canonical(base, position),
        "company_b": companies.canonical(other, rng.choice(
            [companies.FRONT, companies.BACK])),
        "dept": depts.division(rng),
        "room": depts.meeting_room(rng),
        "date": dates.ja(meeting),
        "due": dates.ja(dates.add_days(meeting, rng.choice([5, 7, 10, 14]))),
        "amount": money.comma(money.yen(rng, 120_000, 3_000_000, 1000)),
    }


def _secrets(seed: int, index: int, row: int, surname: str) -> dict:
    """伏せる側。行ごとに引き直す。正解では同じ伏せ字に潰れる。

    1人目の姓だけは、社名と重ねるために固定する。名は行ごとに変える。
    """
    rng = random.Random(f"{seed}/pii/secret/{index}/{row}")
    given = rng.choice(people.GIVEN)[0]
    third = people.full(rng)
    return {
        "p1": f"{surname} {given}",
        "p2": people.full(rng),
        "p3": third,
        "phone": phones.written(rng, phones.landline(rng)),
        "email": emails.external(rng, third.split(" ")[0]),
        "address": addresses.full(rng, with_building=rng.random() < 0.5),
    }


def _meeting_memo(t: dict, v: dict) -> str:
    return "\n".join([
        f"【打合せメモ】{t['date']}  {t['room']}  記録: {v['p1']}",
        f"出席: {v['p1']}（{t['dept']}）、{t['company_b']} {v['p2']} 様",
        "",
        f"・{t['company_a']} への納品を {t['due']} に前倒しする。",
        f"  先方の担当は {v['p3']} さんで、連絡先は {v['phone']}。",
        f"・請求書の送付先を {v['address']} に変更する。",
        f"  控えは {v['email']} にも送る。",
        f"・見積の改定は次回に持ち越し。金額は {t['amount']}円 のまま。",
        f"・{t['company_b']} 分の条件は変更なし。",
    ])


def _inquiry_log(t: dict, v: dict) -> str:
    return "\n".join([
        f"■問い合わせ記録  受付日: {t['date']}  受付: {v['p1']}（{t['dept']}）",
        "",
        f"差出人: {v['p2']}（{t['company_b']}）",
        f"連絡先: {v['phone']} / {v['email']}",
        f"住所: {v['address']}",
        "",
        f"内容: {t['company_a']} 名義で発注した件について、",
        f"請求書の宛名を直してほしいとの依頼。対象金額は {t['amount']}円。",
        f"当社の {v['p3']} が {t['due']} までに折り返す。",
    ])


def _work_log(t: dict, v: dict) -> str:
    return "\n".join([
        f"# 作業ログ {t['date']}（記録 {v['p1']}）",
        f"担当部署: {t['dept']}",
        "",
        f"- {t['company_a']} の窓口を {v['p2']} さんから {v['p3']} さんに変更。",
        f"  新しい連絡先は {v['phone']}。",
        f"- 通知メールの宛先を {v['email']} に差し替え。",
        f"- 納品先の住所を {v['address']} に更新。反映は {t['due']}。",
        f"- {t['company_b']} 分は変更なし。請求は {t['amount']}円。",
    ])


TEMPLATES = [_meeting_memo, _inquiry_log, _work_log]

MASKED = {"p1": NAME, "p2": NAME, "p3": NAME,
          "phone": PHONE, "email": MAIL, "address": ADDRESS}


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth_parts(seed, i)
        v = _secrets(seed, i, row, t["surname"])
        render = TEMPLATES[t["template"]]
        out.append({
            "id": f"{i:03d}",
            "input": render(t, v),
            "truth": {"text": render(t, MASKED), "items": []},
        })
    return out

"""短い打ち合わせメモを合成する。宿題を引き受けた人と期限を拾わせる。

引き受ける発言は一人称で書く（「では私が」「こちらで巻き取ります」）ので、
誰の宿題かは行頭の話者名からしか分からない。
期限は「今週金曜」のような相対表現で書き、冒頭の日付から絶対の日付に
直させる。

正解は宿題の一覧（担当と期限）。行番号によらず同じ。
言い回し・埋め草の発言・メモの型だけを行ごとに変える。
"""

from __future__ import annotations

import random

from ._lib import dates, people

TOPICS = [
    "見積の再提出", "検収条件の確認", "議事録の共有", "先方への回答",
    "テスト環境の用意", "請求書の差し替え", "要員表の更新",
    "障害の一次報告", "契約書の押印手配", "在庫数の棚卸",
]

TAKE = [
    "では私が{topic}をやります。{when}までに出します。",
    "{topic}はこちらで巻き取ります。{when}までにお送りします。",
    "私の方で{topic}を進めます。{when}まででいかがでしょう。",
]

FILLER = [
    "先方の担当が交代したそうです。",
    "前回の宿題はすべて片付いています。",
    "予算の枠は変わっていません。",
    "共有フォルダの場所は後で貼っておきます。",
    "この件、急ぎではないという認識でよいですか。",
    "念のため、関係部署にも共有しておきます。",
    "資料は前回のものを流用できそうです。",
]


def _truth(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}/mem/truth/{index}")
    # 基準日は月曜か火曜。「今週◯曜」が成り立つようにする。
    base = dates.pick(rng, months=(4, 9))
    while base.weekday() not in (0, 1):
        base = dates.add_days(base, 1)

    speakers = people.distinct_surnames(rng, rng.randint(3, 4))
    n_tasks = rng.randint(2, 3)
    topics = rng.sample(TOPICS, n_tasks)

    tasks = []
    for topic in topics:
        owner = rng.choice(speakers)
        weekday = rng.choice([2, 3, 4])          # 水・木・金
        weeks = rng.choice([0, 0, 1])
        due = dates.next_weekday(base, weekday, weeks)
        phrase = dates.relative_phrase(base, due)
        tasks.append({"owner": owner, "topic": topic,
                      "due": dates.iso(due), "when": phrase})

    return {"base": base, "speakers": speakers, "tasks": tasks}


def _render(t: dict, template: int, rng: random.Random) -> str:
    head = f"{dates.with_weekday(t['base'])} 打ち合わせメモ"
    lines = []
    # 冒頭に埋め草を1つ、そのあと宿題を順に、間に埋め草を挟む。
    # 埋め草は重複しないように取り分けておく。
    pool = rng.sample(FILLER, min(len(FILLER), len(t["tasks"]) + 1))
    order: list[tuple[str, dict | str]] = [("filler", pool.pop())]
    for task in t["tasks"]:
        order.append(("task", task))
        if pool and rng.random() < 0.6:
            order.append(("filler", pool.pop()))

    for kind, payload in order:
        if kind == "task":
            speaker = payload["owner"]
            text = rng.choice(TAKE).format(topic=payload["topic"],
                                           when=payload["when"])
        else:
            speaker = rng.choice(t["speakers"])
            text = payload
        lines.append(f"{speaker}: {text}" if template == 0
                     else f"・（{speaker}）{text}")

    return head + "\n" + ("-" * 30 if template == 1 else "") + \
        ("\n" if template == 1 else "") + "\n".join(lines)


def generate_row(samples: int, seed: int, row: int = 0) -> list[dict]:
    out = []
    for i in range(samples):
        t = _truth(seed, i)
        rng = random.Random(f"{seed}/mem/surface/{i}/{row}")
        out.append({
            "id": f"{i:03d}",
            "input": _render(t, row % 2, rng),
            "truth": {"items": [{"owner": x["owner"], "due": x["due"]}
                                for x in t["tasks"]]},
        })
    return out

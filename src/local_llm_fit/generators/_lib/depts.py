"""部署の部品。部・課・室と、会議室名。"""

from __future__ import annotations

import random

DIVISIONS = [
    "営業一部", "営業二部", "管理部", "開発部", "品質保証部",
    "購買部", "人事部", "情報システム部", "物流部", "総務部",
    "経理部", "法務部", "広報室", "経営企画室", "内部監査室",
]

SECTIONS = ["第一課", "第二課", "業務課", "企画課", "運用課", "採用課"]

MEETING_ROOMS = [
    "会議室A", "会議室B", "大会議室", "応接室1", "応接室2",
    "打合せスペース北", "打合せスペース南", "役員会議室",
]


def division(rng: random.Random) -> str:
    return rng.choice(DIVISIONS)


def with_section(rng: random.Random) -> str:
    return f"{rng.choice(DIVISIONS)} {rng.choice(SECTIONS)}"


def distinct_divisions(rng: random.Random, n: int) -> list[str]:
    return rng.sample(DIVISIONS, n)


def meeting_room(rng: random.Random) -> str:
    return rng.choice(MEETING_ROOMS)


def distinct_rooms(rng: random.Random, n: int) -> list[str]:
    return rng.sample(MEETING_ROOMS, n)

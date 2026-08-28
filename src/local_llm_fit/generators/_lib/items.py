"""品目の部品。商品名・サービス名・勘定科目・診療行為。"""

from __future__ import annotations

import random

# (品名, 標準的な単価)
GOODS = [
    ("A4コピー用紙（500枚）", 480), ("トナーカートリッジ 黒", 12800),
    ("デスクチェア", 24800), ("段ボール箱 Lサイズ", 320),
    ("USBハブ 4ポート", 2980), ("モニターアーム", 8600),
    ("ホワイトボード 900x600", 15400), ("電源タップ 6口", 1780),
]

SERVICES = [
    ("ノート型PC 保守費用", 38000), ("会議室 レンタル料", 15000),
    ("Webサイト運用費", 120000), ("クラウド利用料（月額）", 46200),
    ("翻訳費用（英日）", 9500), ("保守作業 人件費", 55000),
    ("名刺印刷 100枚", 2200), ("配送料", 800),
]

# 勘定科目と、その科目に落ちる典型的な摘要
ACCOUNTS = {
    "旅費交通費": ["新幹線 東京-新大阪 往復", "タクシー代（深夜帰宅）",
                   "出張時の宿泊費", "定期券の払い戻し差額"],
    "会議費": ["社内定例の弁当代", "打ち合わせ用の飲み物", "会議室の利用料"],
    "交際費": ["取引先との会食", "取引先への手土産", "接待時のタクシー代"],
    "消耗品費": ["文具の購入", "プリンタ用紙の補充", "電池の購入"],
    "通信費": ["携帯電話の基本料", "回線使用料", "郵便切手の購入"],
    "支払手数料": ["振込手数料", "登記の司法書士報酬", "各種証明書の発行料"],
    "新聞図書費": ["業界誌の定期購読", "技術書の購入", "調査レポートの購入"],
    "広告宣伝費": ["求人広告の掲載料", "展示会のブース出展料", "パンフレットの印刷"],
}

MEDICAL = [
    ("初診料", 291), ("再診料", 75), ("処方箋料", 68),
    ("血液検査（生化学）", 144), ("胸部X線撮影", 210),
    ("創傷処置", 52), ("特定疾患療養管理料", 225),
]


def goods(rng: random.Random, n: int) -> list[tuple[str, int]]:
    return rng.sample(GOODS, n)


def services(rng: random.Random, n: int) -> list[tuple[str, int]]:
    return rng.sample(SERVICES, n)


def mixed(rng: random.Random, n: int) -> list[tuple[str, int]]:
    return rng.sample(GOODS + SERVICES, n)


def account_names() -> list[str]:
    return list(ACCOUNTS)


def account_sample(rng: random.Random, account: str) -> str:
    return rng.choice(ACCOUNTS[account])


def medical(rng: random.Random, n: int) -> list[tuple[str, int]]:
    return rng.sample(MEDICAL, n)

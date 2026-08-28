"""生成器で使い回す共通部品。

タスクごとの生成器は、ここから「日付」「人名」「社名」などを取り出して
正解を組み立て、そのあとで文面を書き起こす。
どの関数も乱数を引数で受け取るだけで、内部に状態を持たない。
"""

from . import companies, dates, depts, items, money, people, quantities

__all__ = ["companies", "dates", "depts", "items", "money", "people", "quantities"]

"""生成器で使い回す共通部品。

タスクごとの生成器は、ここから「日付」「人名」「社名」などを取り出して
正解を組み立て、そのあとで文面を書き起こす。
どの関数も乱数を引数で受け取るだけで、内部に状態を持たない。
"""

from . import (
    addresses,
    companies,
    dates,
    depts,
    emails,
    items,
    money,
    people,
    phones,
    quantities,
)

__all__ = ["addresses", "companies", "dates", "depts", "emails", "items",
           "money", "people", "phones", "quantities"]

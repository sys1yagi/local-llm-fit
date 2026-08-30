"""同時実行数を振って測る。

負荷のかけ方は closed-loop（同時に C 本を保ち、終わったら次を投げる）。
到着間隔を決めた open-loop の負荷が要るようになったら、この層だけ
GuideLLM のような専用ツールに差し替えられるよう、採点とは分けてある。

同時実行数ごとに別の入力を投げる（samples_by_level）。
同じ入力を投げ直すと、推論サーバが前回読んだ内容を覚えていて読み込みを
省略するため、後の行ほど速く見える。入力2万字のタスクでは、同じ4本同時が
初見59.7秒・2回目0.40秒に分かれた。

1件が返り終わらないまま `--timeout` 秒に達したら、その件は打ち切る。
打ち切った件には印を付けて、誤答とは別に数える。答えの質を測れていない
状態なので、正答率の分子にも「間違えた」の数にも入れない。

「最初の文字が出るまで」は、答えの本文の1文字目が届いた時刻で測る。
推論モデルが思考トークンを先に吐く場合、本文が出るまでの時間がここに乗る。
それは測定の誤りではなく、利用者が実際に待つ時間なので、そのまま測る。
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class Call:
    sample_id: str
    ttft_s: float | None = None
    e2e_s: float | None = None
    output_tokens: int = 0
    content: str = ""
    error: str | None = None
    chunks: int = 0
    usage: dict = field(default_factory=dict)
    timed_out: bool = False


async def _one(client: httpx.AsyncClient, base_url: str, model: str,
               prompt: str, sample_id: str, request_opts: dict,
               timeout_s: float) -> Call:
    call = Call(sample_id=sample_id)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "stream_options": {"include_usage": True},
        **request_opts,
    }
    started = time.perf_counter()
    try:
        # httpx のタイムアウトは、ストリームでは「次の断片が来るまで」にしか
        # 効かない。断片が出続けるかぎり何分でも走るので、1件の総時間の上限は
        # ここで別に掛ける。
        async with asyncio.timeout(timeout_s), client.stream(
            "POST", f"{base_url}/chat/completions", json=body,
            timeout=httpx.Timeout(timeout_s, connect=10.0),
        ) as resp:
            if resp.status_code != 200:
                text = (await resp.aread()).decode(errors="replace")
                call.error = f"http_{resp.status_code}: {text[:200]}"
                call.e2e_s = time.perf_counter() - started
                return call
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if event.get("usage"):
                    call.usage = event["usage"]
                for choice in event.get("choices") or []:
                    piece = (choice.get("delta") or {}).get("content") or ""
                    if piece:
                        if call.ttft_s is None:
                            call.ttft_s = time.perf_counter() - started
                        call.content += piece
                        call.chunks += 1
    except TimeoutError:
        # 打ち切りは、答えの中身が悪かったのではなく待てなかったということ。
        # 誤答と混ぜないよう、印を付けて別に数える。
        call.timed_out = True
        call.error = f"打ち切り: {timeout_s:.0f}秒を超えた"
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        call.timed_out = isinstance(e, httpx.TimeoutException)
        call.error = f"{type(e).__name__}: {e}"[:200]

    call.e2e_s = time.perf_counter() - started
    call.output_tokens = int(call.usage.get("completion_tokens") or call.chunks)
    return call


async def _sweep_level(base_url: str, model: str, samples: list[dict],
                       prompt_template: str, concurrency: int,
                       request_opts: dict, timeout_s: float) -> dict:
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency + 4,
                          max_keepalive_connections=concurrency + 4)

    async with httpx.AsyncClient(limits=limits) as client:
        async def guarded(sample: dict) -> Call:
            async with sem:
                prompt = prompt_template.replace("{input}", sample["input"])
                return await _one(client, base_url, model, prompt,
                                  sample["id"], request_opts, timeout_s)

        wall_start = time.perf_counter()
        calls = await asyncio.gather(*(guarded(s) for s in samples))
        wall = time.perf_counter() - wall_start

    return {"concurrency": concurrency, "wall_s": wall, "calls": calls}


def sweep(base_url: str, model: str, samples_by_level: list[list[dict]],
          prompt_template: str, levels: list[int], request_opts: dict,
          timeout_s: float, on_level=None) -> list[dict]:
    """levels と samples_by_level は同じ長さで、順に対応する。"""
    results = []
    for level, samples in zip(levels, samples_by_level):
        r = asyncio.run(_sweep_level(base_url, model, samples, prompt_template,
                                     level, request_opts, timeout_s))
        results.append(r)
        if on_level:
            on_level(r)
    return results

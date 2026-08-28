# local-llm-fit

手元の機材とローカルLLMで、**その業務が何人の同時利用まで載るか**を測る。
応答速度と出力品質を同時に測り、あらかじめ書いた合否の線に照らして「載る／載らない」を出す。

> Measures whether a local LLM can carry a real business workload on your own
> hardware — output quality and latency together, under concurrency.
> Tasks are defined in Japanese business terms; input is synthesised from a
> fixed seed, so no real data leaves your machine.

## 測った結果

タスク: 日本語の請求書から決められたJSONを抜き出す（12件・seed 42）
機材: Apple M5 Max / 128GB
モデル: `ornith-1.5-35b-a3b`（LM Studio・OpenAI互換エンドポイント）

| 同時実行 | TTFT p50 | TTFT p95 | 応答完了 p95 | スループット | 合格率 | エラー | 判定 |
|---:|---:|---:|---:|---:|---:|---:|:--|
| 1 | 0.03s | 0.04s | 2.47s | 120.7 tok/s | 92% (11/12) | 0 | 品質不足 |
| 2 | 0.06s | 0.07s | 4.97s | 125.5 tok/s | 92% (11/12) | 0 | 品質不足 |
| 4 | 0.12s | 0.12s | 9.02s | 136.5 tok/s | 92% (11/12) | 0 | 品質不足 |
| 8 | 4.81s | 8.03s | 14.28s | 135.3 tok/s | 92% (11/12) | 0 | 載らない |
| 16 | 6.37s | 12.91s | 19.60s | 134.4 tok/s | 92% (11/12) | 0 | 載らない |
| 32 | 4.89s | 12.95s | 20.23s | 134.4 tok/s | 92% (11/12) | 0 | 載らない |

生の結果は [`results/`](results/) に入っている。同じ表が出るコマンドは下の「使う」にある。

合否の線は `tasks/invoice-json-ja.yaml` に書いてある（合格率95%以上、TTFT p95 2秒以内、応答完了 p95 15秒以内、エラー0）。

### この表から分かること

**同時実行を増やしても、機材が処理できる量はほとんど増えない。**
総スループットは 120.7 → 136.5 tok/s（最大でも13%増）で頭打ちになり、
8並列から先は 134〜135 tok/s のまま動かない。
一方で1件が返り終わるまでの時間は 2.47秒 → 20.23秒 と8倍になる。
つまり**並列にしても仕事は増えず、待ち時間だけが伸びる**。
1リクエストあたりの生成速度（tokens/sec）だけを見ていると、この頭打ちは見えない。

**待ち時間が壊れる境目は4並列と8並列の間にある。**
TTFT は4並列までは0.12秒だが、8並列で8.03秒に跳ねる。
これは推論が遅くなったのではなく、順番待ちが始まった時刻。
「何人まで置けるか」を決めているのはこの境目で、GPUの生成速度ではない。

**品質は同時実行数によらず一定で、そして足りていない。**
どの並列数でも 11/12（92%）で、合否の線の95%に届かない。
落ちているのは毎回同じ1件で、品名「名刺印刷 100枚」から「100枚」を落として
`名刺印刷` と読む取り違えを、温度0で毎回再現する。
**速度をいくら測ってもこれは見つからない。逆に品質だけ測っても、8並列で待ち時間が壊れることは見つからない。**
両方を同時に測る理由がここにある。

この機材でこのタスクを回すなら、モデルを替えるか、合格率の線を下げられるか業務側で決める、
のどちらかが先で、機材を足す話はその後になる。

## 使う

必要なのは [uv](https://docs.astral.sh/uv/) と、OpenAI互換のエンドポイントを出すローカル推論環境
（LM Studio、Ollama、vLLM、llama.cpp server など）。

```bash
git clone https://github.com/sys1yagi/local-llm-fit
cd local-llm-fit
uv sync

# 入力と正解を1件だけ見る（推論は走らない）
uv run fit --dry-run

# 測る
uv run fit --model <モデルID> --concurrency 1,2,4,8,16,32
```

接続先の既定は `http://localhost:1234/v1`（LM Studio）。Ollama なら
`--base-url http://localhost:11434/v1` を付ける。
モデルIDは `curl http://localhost:1234/v1/models` で確認できる。

結果は `results/` に要約のJSON、`runs/` に全応答が残る（`runs/` は git 管理外）。

## 自分の業務に合わせる

**合否の線を変える。** `tasks/*.yaml` の `slo` を書き換える。
何%まで許容するか、何秒まで待てるかは業務ごとに違う。ここが各社で決めるところで、
このリポジトリに入っている数字は仮置きにすぎない。

**タスクを足す。** `tasks/` にYAMLを1枚、`src/local_llm_fit/generators/` に入力を作る
Pythonを1本置く。生成器は「先に正解を作り、そこから文面を組み立てる」形にする。
そうすれば正解と本文が必ず一致し、seed を固定すれば誰の手元でも同じ入力になる。

**実データは使わない。** 入力は合成する。守秘に触れず、公開しても差し支えなく、
評価データが学習に取り込まれても作り直せる。配るのはデータではなく生成器。

## 結果を持ち寄る

`results/` に出たJSONをそのままPRで投げてもらえると、機材・モデル・量子化ごとの
比較が溜まっていく。1台で測れる範囲には限りがあるが、持ち寄れば
「この構成なら何並列まで載るか」の表になる。

## やっていないこと

- 負荷のかけ方は closed-loop（同時にN本を保ち、終わったら次を投げる）だけ。
  到着間隔を決めた open-loop の負荷は入れていない。バーストのある業務を測るには足りない
- 測っているのは1タスク・1モデル・1機材。モデル比較表ではない
- 消費電力・VRAM使用量は取っていない
- GPU側のキュー滞留やKVキャッシュの内部状態は見ていない。外から見える時間だけを測る

## 関連するもの

- 負荷と応答時間を測るなら [GuideLLM](https://github.com/vllm-project/guidellm) や
  [llm-optimizer](https://github.com/bentoml/llm-optimizer) の方が作りが厚い。ただし出力の中身は採点しない
- 品質だけなら [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)、
  日本語なら [llm-jp-eval](https://github.com/llm-jp/llm-jp-eval) や
  [Nejumi リーダーボード](https://nejumi.ai)。ただし同時実行時の挙動は測らない
- 両方を1つでやる先行研究に [Bench360](https://github.com/slinusc/bench360) がある。
  こちらは NVIDIA CUDA 専用で、Apple Silicon や llama.cpp は対象外

このリポジトリが埋めているのは、**日本語の業務タスク**、**手元の機材（Apple Silicon を含む）**、
**合否の線に照らした判定**の3つ。

## ライセンス

MIT

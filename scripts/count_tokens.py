from pathlib import Path

import tiktoken

SAMPLE = """
你想年入百万，现实月薪五千。你想半年瘦三十斤，三天就破功。越努力越挫败，越挫败越不想动。

不是你不拼，是你在跟愿望打仗，没跟事实对齐。

毛主席讲实事求是，从实际出发，不从愿望出发。愿望是我想怎样，事实是现在怎样。把愿望当事实，每一步都在踩空。

《改造我们的学习》里批评一种毛病：凭主观想象办事，不顾客观情况。翻译成大白话：脑子里的剧本，和现实不是同一部戏。

延安时期，大生产运动，有人喊口号喊得响，地却不肯下，苗却不肯种，秋后没粮吃。真正活下来的人，是去看土质、看雨水、看种子，按能长出来的东西去种。不是不想丰收，是先承认这块地能长什么。

现代案例。很多年轻人想一夜暴富，All in 某个风口，没调研、没本金、没技能，就凭一腔热血。史玉柱说过，超过认知的钱，会以各种形式流回去。不是机会不存在，是你的出发点是愿望，不是事实。

你明天就能做。拿一张纸，左边写我想要的，右边写我现在有的，包括时间、钱、技能、人脉。中间画箭头，只写三条今年够得着的动作。够不着的先承认，不是放弃，是排期。

实事求是不是泼冷水，是让你把力气打在能落地的地方。

你愿望和现实差最远的那一项是什么？评论区打出来。

关注我，用成事智慧，破开自己人生的局。
"""


def count(text: str, encoding_name: str = "cl100k_base") -> int:
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


def main() -> None:
    text = SAMPLE.strip()
    # 也可：text = Path("samples/manual.txt").read_text(encoding="utf-8")
    tokens = count(text)
    print("chars:", len(text))
    print("tokens:", tokens)
    print("approx_tokens_per_100_chars:", round(tokens / max(len(text), 1) * 100, 2))


if __name__ == "__main__":
    main()
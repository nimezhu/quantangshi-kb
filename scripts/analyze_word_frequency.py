"""P3 字/词频与意象统计。

- 单字频（全库）
- 句内双字组频（不跨句读，古典诗词的实用"词"单位）
- jieba 分词词频（对照参考；jieba 对繁体古文偏弱，以双字组为准）
- 意象词计数（预定义繁体清单）
- 高产诗人签名用字（相对全库的用字倾向 lift）
输出：data/analysis/word_freq.{json,md}
"""
import json
from collections import Counter

from config import ANALYSIS_DIR
from lib_qts import iter_yuding, split_clauses, canonical_author

IMAGERY_CHARS = list("月風花酒春秋山水雲雨雪柳松竹梅鶴雁猿馬舟劍琴夢淚愁客僧蟬霜露煙霞江樓鐘")
IMAGERY_WORDS = ["明月", "春風", "秋風", "白雲", "青山", "故人", "天涯", "江南",
                 "長安", "洛陽", "黃河", "夕陽", "芳草", "落花", "流水", "孤舟",
                 "白髮", "紅塵", "浮雲", "斜陽"]
TOP_POETS = 15


def main():
    char_freq = Counter()
    bigram_freq = Counter()
    word_text_parts = []
    poet_chars = {}          # canonical -> Counter
    poet_poems = Counter()

    for _, poems in iter_yuding():
        for p in poems:
            clauses = split_clauses(p.get("paragraphs", []))
            ac = canonical_author(p["author"])
            poet_poems[ac] += 1
            pc = poet_chars.setdefault(ac, Counter())
            for cl in clauses:
                char_freq.update(cl)
                pc.update(cl)
                bigram_freq.update(cl[i:i+2] for i in range(len(cl) - 1))
                word_text_parts.append(cl)

    total_chars = sum(char_freq.values())

    # jieba 对照（繁体古文仅作参考）
    import jieba
    jieba_freq = Counter()
    for cl in word_text_parts:
        jieba_freq.update(w for w in jieba.cut(cl) if len(w) >= 2)

    full_text = "\n".join(word_text_parts)
    imagery = {c: char_freq[c] for c in IMAGERY_CHARS}
    imagery_w = {w: bigram_freq[w] for w in IMAGERY_WORDS}

    # 签名用字：poet 用字占比 / 全库占比 的 lift，最少出现 20 次
    signatures = {}
    for ac, _ in poet_poems.most_common(TOP_POETS):
        pc = poet_chars[ac]
        ptotal = sum(pc.values())
        lifts = []
        for ch, n in pc.items():
            if n >= 20 and char_freq[ch] >= 50:
                lifts.append((round((n / ptotal) / (char_freq[ch] / total_chars), 2), ch, n))
        lifts.sort(reverse=True)
        signatures[ac] = [{"char": ch, "count": n, "lift": lf} for lf, ch, n in lifts[:10]]

    out = {
        "total_chars": total_chars,
        "distinct_chars": len(char_freq),
        "char_top": char_freq.most_common(300),
        "bigram_top": bigram_freq.most_common(300),
        "jieba_top": jieba_freq.most_common(200),
        "imagery_chars": imagery,
        "imagery_words": imagery_w,
        "poet_signatures": signatures,
        "poet_poem_counts": dict(poet_poems.most_common(TOP_POETS)),
    }
    (ANALYSIS_DIR / "word_freq.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    def table(pairs, n, head):
        rows = [f"| {head} | 次数 |", "|---|---|"]
        rows += [f"| {k} | {v} |" for k, v in pairs[:n]]
        return rows

    lines = ["# P3 字/词频与意象统计", "",
             f"- 正文总字数：**{total_chars:,}**；不同汉字：{len(char_freq):,}", "",
             "## 单字 Top 30", ""] + table(char_freq.most_common(30), 30, "字")
    lines += ["", "## 句内双字组 Top 30（古典诗词实用词单位）", ""] + \
        table(bigram_freq.most_common(30), 30, "双字组")
    lines += ["", "## 意象字（预定义清单，按频次）", ""] + \
        table(sorted(imagery.items(), key=lambda x: -x[1]), 40, "意象字")
    lines += ["", "## 意象词（预定义清单）", ""] + \
        table(sorted(imagery_w.items(), key=lambda x: -x[1]), 20, "意象词")
    lines += ["", f"## 高产诗人签名用字（Top {TOP_POETS}，lift = 相对全库倾向）", ""]
    for ac, sigs in signatures.items():
        sig_str = "、".join(f"{s['char']}({s['lift']}×)" for s in sigs[:6])
        lines.append(f"- **{ac}**（{poet_poems[ac]} 首）：{sig_str}")
    lines += ["", "> jieba 分词结果仅作对照（对繁体古文偏弱），完整数据见 word_freq.json。"]
    (ANALYSIS_DIR / "word_freq.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"word freq: {total_chars:,} chars, {len(char_freq)} distinct; "
          f"top char {char_freq.most_common(3)}")


if __name__ == "__main__":
    main()

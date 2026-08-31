"""P7 简繁映射质检。

御定文本为繁体，前端只需 繁→简（t2s）单向转换。t2s 是多对一、逐字确定的，
理论上安全；本管线量化验证并列出语料中实际存在的多对一折叠组，
为 §7 的"前端 JS 转换 vs opencc 预渲染"决策提供依据。
输出：data/analysis/simp_trad.{json,md}
"""
import json
from collections import Counter, defaultdict

from opencc import OpenCC

from config import ANALYSIS_DIR
from lib_qts import iter_yuding, strip_punct

cc = OpenCC("t2s")


def main():
    char_freq = Counter()
    for _, poems in iter_yuding():
        for p in poems:
            char_freq.update(strip_punct("".join(p.get("paragraphs", []))))
            char_freq.update(strip_punct(p.get("title", "")))

    changed = {}
    groups = defaultdict(list)  # simp -> [trad chars in corpus]
    for ch in char_freq:
        s = cc.convert(ch)
        if s != ch:
            changed[ch] = s
        groups[s].append(ch)

    collisions = {s: sorted(chs, key=lambda c: -char_freq[c])
                  for s, chs in groups.items() if len(chs) > 1}
    total = sum(char_freq.values())
    changed_occ = sum(char_freq[c] for c in changed)
    collision_occ = sum(char_freq[c] for chs in collisions.values() for c in chs)

    out = {"total_chars": total, "distinct_chars": len(char_freq),
           "changed_distinct": len(changed), "changed_occurrences": changed_occ,
           "collision_groups": {s: [[c, char_freq[c]] for c in chs]
                                for s, chs in collisions.items()}}
    (ANALYSIS_DIR / "simp_trad.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    top_coll = sorted(collisions.items(),
                      key=lambda kv: -sum(char_freq[c] for c in kv[1]))
    lines = ["# P7 简繁映射质检报告", "",
             f"- 语料总字次：{total:,}；不同汉字：{len(char_freq):,}",
             f"- t2s 会改写的字：{len(changed):,} 个（{changed_occ:,} 字次，{changed_occ/total:.1%}）",
             f"- 多对一折叠组（语料内实际出现）：**{len(collisions)}** 组（涉及 {collision_occ:,} 字次）",
             "",
             "## 结论与建议", "",
             "- 展示方向是 **繁→简（t2s）**，逐字多对一、无歧义，前端 JS 字表转换即可满足，",
             "  无需 opencc 预渲染双版本。多对一折叠（如 髮/發→发）只损失原文信息量，不产生错字。",
             "- **危险方向是 简→繁（s2t）**：御定数据上游已有过度转换伤痕（方幹/鄭穀/於鵠，见 P1）。",
             "  本项目任何环节都不做 s2t。",
             "- 建议沿用 shiji-kb 的 simp-trad-converter.js；用本报告的折叠组抽查其字表覆盖。",
             "",
             "## 多对一折叠组 Top 30（按字次）", "",
             "| 简体 | 繁体组（字次） |", "|---|---|"]
    for s, chs in top_coll[:30]:
        detail = "、".join(f"{c}({char_freq[c]:,})" for c in chs)
        lines.append(f"| {s} | {detail} |")
    (ANALYSIS_DIR / "simp_trad.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"simp/trad: {len(changed)} chars change, {len(collisions)} collision groups")


if __name__ == "__main__":
    main()

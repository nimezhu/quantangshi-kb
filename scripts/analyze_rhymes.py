"""P5 韵脚与诗体分析。

- 诗体判定（按句读单元字数：五絕/五律/五言排律/七絕/七律/七言古體/四言/六言/雜言）
  —— 纯形式判定，不看平仄粘对，属近似；排律/古體边界尤其粗略，报告中注明。
- 韵脚：偶数句末字；韵母用 pypinyin（普通话近似，非平水韵，仅作分布参考）。
- 平仄覆盖：经 P2 映射到 poet.tang 后，statistics strains 数据可用率。
输出：data/analysis/rhymes.{json,md}
"""
import json
from collections import Counter

from pypinyin import Style, pinyin

from config import ANALYSIS_DIR, POEM_ID_MAP, STRAINS_DIR
from lib_qts import iter_yuding, split_clauses, poem_key


def classify(clauses):
    lens = [len(c) for c in clauses]
    if not lens:
        return "無正文"
    n = len(lens)
    if all(l == 5 for l in lens):
        return {4: "五絕", 8: "五律"}.get(n, "五言排律" if n % 2 == 0 and n > 8 else "五言古體")
    if all(l == 7 for l in lens):
        return {4: "七絕", 8: "七律"}.get(n, "七言古體")
    if all(l == 4 for l in lens):
        return "四言"
    if all(l == 6 for l in lens):
        return "六言"
    return "雜言"


def main():
    forms = Counter()
    rhyme_char_freq = Counter()
    final_freq = Counter()
    per_poem = {}
    final_cache = {}

    for volume, poems in iter_yuding():
        for i, p in enumerate(poems, start=1):
            clauses = split_clauses(p.get("paragraphs", []))
            form = classify(clauses)
            forms[form] += 1
            rhymes = "".join(c[-1] for j, c in enumerate(clauses, 1)
                             if j % 2 == 0 and c)
            rhyme_char_freq.update(rhymes)
            per_poem[poem_key(volume, i)] = [form, rhymes]

    for ch, n in rhyme_char_freq.items():
        if ch not in final_cache:
            f = pinyin(ch, style=Style.FINALS, strict=False)
            final_cache[ch] = f[0][0] if f and f[0] else "?"
        final_freq[final_cache[ch]] += n

    # 平仄（strains）覆盖率：strains 按 id 对齐 poet.tang
    strain_ids = set()
    for f in STRAINS_DIR.glob("poet.tang.*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            if e.get("strains"):
                strain_ids.add(e["id"])
    id_map = json.loads(POEM_ID_MAP.read_text(encoding="utf-8"))
    covered = sum(1 for m in id_map.values() if any(i in strain_ids for i in m["ids"]))

    out = {"form_distribution": dict(forms.most_common()),
           "rhyme_char_top": rhyme_char_freq.most_common(100),
           "final_top": final_freq.most_common(40),
           "strains_available": covered,
           "per_poem": per_poem}
    (ANALYSIS_DIR / "rhymes.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")

    total = sum(forms.values())
    lines = ["# P5 韵脚与诗体报告", "",
             f"- 御定诗总数：{total}；经 P2 映射后 **{covered}** 首（{covered/total:.1%}）有平仄（strains）数据",
             "- 诗体为纯形式判定（字数×句数），排律/古體边界粗略；韵母为普通话近似（非平水韵）",
             "", "## 诗体分布", "", "| 诗体 | 首数 | 占比 |", "|---|---|---|"]
    for fm, n in forms.most_common():
        lines.append(f"| {fm} | {n} | {n/total:.1%} |")
    lines += ["", "## 韵脚字 Top 20", "", "| 字 | 次数 |", "|---|---|"]
    for ch, n in rhyme_char_freq.most_common(20):
        lines.append(f"| {ch} | {n} |")
    lines += ["", "## 韵母（普通话近似）Top 15", "", "| 韵母 | 次数 |", "|---|---|"]
    for fi, n in final_freq.most_common(15):
        lines.append(f"| {fi} | {n} |")
    (ANALYSIS_DIR / "rhymes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rhymes: forms {forms.most_common(5)}; strains coverage {covered}/{total}")


if __name__ == "__main__":
    main()

"""P1 作者别名归一与聚合。

输入：御定全唐詩 900 卷的 author/biography 字段 × authors.tang.json
输出：data/authors_merged.json + data/analysis/authors_report.md
依赖：data/author_aliases.json（人工核对的别名种子表，alias → canonical）
"""
import json
from collections import Counter, defaultdict

from config import AUTHORS_TANG, AUTHORS_MERGED, ANALYSIS_DIR
from lib_qts import iter_yuding, iter_tang_shards, canonical_author


def main():
    # ---- 御定侧聚合 ----
    yd = {}  # canonical -> record
    for volume, poems in iter_yuding():
        for p in poems:
            raw = p["author"].strip()
            key = canonical_author(raw)
            rec = yd.setdefault(key, {
                "yuding_names": Counter(), "volumes": [], "poem_count_yuding": 0,
                "biography": "",
            })
            rec["yuding_names"][raw] += 1
            if not rec["volumes"] or rec["volumes"][-1] != volume:
                rec["volumes"].append(volume)
            rec["poem_count_yuding"] += 1
            if not rec["biography"] and p.get("biography"):
                rec["biography"] = p["biography"]

    # ---- poet.tang 侧 ----
    tang_authors = json.loads(AUTHORS_TANG.read_text(encoding="utf-8"))
    tang_desc = {}  # canonical -> (name, desc)
    for a in tang_authors:
        tang_desc.setdefault(canonical_author(a["name"]), (a["name"], a.get("desc", "")))

    tang_counts = Counter()
    for _, poems in iter_tang_shards():
        for p in poems:
            tang_counts[canonical_author(p["author"])] += 1

    # ---- 合并 ----
    merged = {}
    for key, rec in yd.items():
        display = rec["yuding_names"].most_common(1)[0][0]
        tname, tdesc = tang_desc.get(key, ("", ""))
        merged[key] = {
            "canonical": key,
            "display": display,
            "yuding_names": sorted(rec["yuding_names"]),
            "tang_name": tname,
            "volumes": rec["volumes"],
            "poem_count_yuding": rec["poem_count_yuding"],
            "poem_count_tang": tang_counts.get(key, 0),
            "biography": rec["biography"],
            "desc": tdesc,
        }
    for key, (tname, tdesc) in tang_desc.items():
        if key not in merged:
            merged[key] = {
                "canonical": key, "display": tname, "yuding_names": [],
                "tang_name": tname, "volumes": [],
                "poem_count_yuding": 0, "poem_count_tang": tang_counts.get(key, 0),
                "biography": "", "desc": tdesc,
            }

    AUTHORS_MERGED.write_text(
        json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 报告 ----
    yd_total = len(yd)
    matched = sum(1 for k in yd if k in tang_desc)
    tang_only = [k for k in tang_desc if k not in yd]
    unmatched = sorted((k for k in yd if k not in tang_desc),
                       key=lambda k: -yd[k]["poem_count_yuding"])

    lines = [
        "# P1 作者归一报告", "",
        f"- 御定全唐詩 distinct 作者（归一后）：**{yd_total}**",
        f"- 其中与 authors.tang.json 匹配：**{matched}**（{matched/yd_total:.1%}）",
        f"- 御定独有：{yd_total - matched}；authors.tang 独有：{len(tang_only)}",
        "", "## 御定独有作者 Top 40（按作品数，人工核对别名的候选）", "",
        "| 作者 | 御定作品数 | 卷 |", "|---|---|---|",
    ]
    for k in unmatched[:40]:
        r = yd[k]
        vols = ",".join(str(v) for v in r["volumes"][:5])
        lines.append(f"| {r['yuding_names'].most_common(1)[0][0]} | {r['poem_count_yuding']} | {vols} |")
    lines += ["", "## authors.tang 独有作者 Top 20（按 poet.tang 作品数）", "",
              "| 作者 | tang作品数 |", "|---|---|"]
    for k in sorted(tang_only, key=lambda k: -tang_counts.get(k, 0))[:20]:
        lines.append(f"| {tang_desc[k][0]} | {tang_counts.get(k, 0)} |")
    (ANALYSIS_DIR / "authors_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"authors: yuding={yd_total} matched={matched} ({matched/yd_total:.1%}) "
          f"merged={len(merged)} → {AUTHORS_MERGED.name}")


if __name__ == "__main__":
    main()

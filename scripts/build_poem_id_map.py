"""P2 御定全唐詩 ↔ poet.tang 对齐。

三轮匹配：① (作者, 题目) 精确；② 组诗（tang 题目 = 御定题目 + " 一/二/…"）；
③ (作者, 首句前5字) 兜底。均在异体字归一后比较。
①的多候选消歧：同题多首（如李商隐六首《無題》各有御定条目）时，只保留
首句出现在该御定条目原文中的候选（按出现位置排序）——否则六首会被
全部映射到每一个同题键上，P9 随之灌入合抄文本（2026-09 修正）。
输出：data/poem_id_map.json（poem_key → ids/refs）+ data/analysis/poem_id_map_report.md
"""
import json
import re
from collections import defaultdict

from config import POEM_ID_MAP, ANALYSIS_DIR
from lib_qts import (iter_yuding, iter_tang_shards, canonical_author,
                     strip_punct, poem_key, fold_t2s, VARIANT_CHARS)

CN_NUM = re.compile(r"^[一二三四五六七八九十百]+$")


def norm_text(s: str) -> str:
    """匹配归一：去标点 + 简体折叠 + 异体折叠（嶽/岳、荊/荆 等经折叠等价）。"""
    return fold_t2s(strip_punct(s)).translate(VARIANT_CHARS)


def main():
    # ---- poet.tang 索引 ----
    by_title = defaultdict(list)      # (author_c, title_n) -> [entry]
    by_group = defaultdict(list)      # (author_c, base_title_n) -> [(num, entry)]
    by_first = defaultdict(list)      # (author_c, first5) -> [entry]
    total_tang = 0
    for shard, poems in iter_tang_shards():
        for idx, p in enumerate(poems):
            total_tang += 1
            ac = canonical_author(p["author"])
            tn = norm_text(p["title"])
            entry = {"id": p["id"], "shard": shard, "idx": idx,
                     "first5": norm_text(p["paragraphs"][0])[:5]
                     if p.get("paragraphs") else ""}
            by_title[(ac, tn)].append(entry)
            parts = p["title"].rsplit(" ", 1)
            if len(parts) == 2 and CN_NUM.match(parts[1]):
                by_group[(ac, norm_text(parts[0]))].append((parts[1], entry))
            if p["paragraphs"]:
                by_first[(ac, norm_text(p["paragraphs"][0])[:5])].append(entry)

    # ---- 逐首匹配（必须用御定原始文本：本映射是 P9 文本修复的输入）----
    mapping = {}
    stats = {"title": 0, "group": 0, "firstline": 0, "unmatched": 0}
    total_yd = 0
    for volume, poems in iter_yuding(raw=True):
        for i, p in enumerate(poems, start=1):
            total_yd += 1
            key = poem_key(volume, i)
            ac = canonical_author(p["author"])
            tn = norm_text(p["title"])
            hit, how = by_title.get((ac, tn)), "title"
            if hit and len(hit) > 1:
                ydn = norm_text("".join(p.get("paragraphs", [])))
                contained = sorted(
                    ((ydn.index(e["first5"]), e) for e in hit
                     if len(e["first5"]) >= 4 and e["first5"] in ydn),
                    key=lambda x: x[0])
                if contained:
                    hit = [e for _, e in contained]
            if not hit:
                grp = by_group.get((ac, tn))
                if grp:
                    hit, how = [e for _, e in grp], "group"
                    if len(hit) > 1:
                        # tang 侧可能存在多组同名组诗（两组《無題二首》各含 一/二）：
                        # 按（分片,连续下标）聚为"组"，组内任一首句见于御定原文
                        # 即整组保留（子诗首句可能恰在丢失列中，不能单靠包含）
                        ydn = norm_text("".join(p.get("paragraphs", [])))
                        runs = []
                        for e in sorted(hit, key=lambda e: (e["shard"], e["idx"])):
                            if runs and runs[-1][-1]["shard"] == e["shard"]                                     and e["idx"] - runs[-1][-1]["idx"] == 1:
                                runs[-1].append(e)
                            else:
                                runs.append([e])
                        kept = [r for r in runs
                                if any(len(e["first5"]) >= 4 and e["first5"] in ydn
                                       for e in r)]
                        if kept:
                            hit = [e for r in kept for e in r]
            if not hit and p.get("paragraphs"):
                first5 = norm_text(p["paragraphs"][0])[:5]
                if len(first5) >= 4:
                    cand = by_first.get((ac, first5))
                    if cand:
                        hit, how = cand[:1], "firstline"
            if hit:
                stats[how] += 1
                mapping[key] = {"ids": [e["id"] for e in hit],
                                "refs": [[e["shard"], e["idx"]] for e in hit],
                                "match": how}
            else:
                stats["unmatched"] += 1

    POEM_ID_MAP.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    matched = total_yd - stats["unmatched"]
    lines = [
        "# P2 御定 ↔ poet.tang 对齐报告", "",
        f"- 御定诗总数：**{total_yd}**；poet.tang 诗总数：{total_tang}",
        f"- 匹配成功：**{matched}**（{matched/total_yd:.1%}）",
        f"  - ① 题目精确：{stats['title']}",
        f"  - ② 组诗展开：{stats['group']}（御定 1 首 ↔ tang 多首）",
        f"  - ③ 首句兜底：{stats['firstline']}",
        f"- 未匹配：{stats['unmatched']}（{stats['unmatched']/total_yd:.1%}）——增强字段（平仄/热度/三百首徽章）对这些诗缺省，不影响阅读",
        "",
        f"- 映射覆盖的 tang 诗条数：{sum(len(m['ids']) for m in mapping.values())}",
    ]
    (ANALYSIS_DIR / "poem_id_map_report.md").write_text("\n".join(lines) + "\n",
                                                        encoding="utf-8")
    print(f"poem map: {matched}/{total_yd} ({matched/total_yd:.1%}) "
          f"title={stats['title']} group={stats['group']} first={stats['firstline']}")


if __name__ == "__main__":
    main()

"""P6 热度榜单。

数据源两路：
1. rank/poet/*.json 搜索引擎命中数（按分片+下标对齐 poet.tang）。
   ⚠️ 实测发现：命中数反映的是"词组常见度"而非"诗篇知名度"（单字题目如《雪》《月》
   与常用词作者名如"無可"严重虚高），**不可单独作为名篇依据**，只作参考分数保留。
2. 唐诗三百首.json（人工选本，366 首，带 UUID 可直接 join poet.tang → 御定）。
   名篇榜以三百首为锚，榜内按 rank 分数排序。
诗人榜按三百首入选数排序（rank 分数破平局）。
输出：data/analysis/popularity.{json,md}
"""
import json
from collections import defaultdict

from config import RANK_DIR, POEM_ID_MAP, TANG300, ANALYSIS_DIR
from lib_qts import iter_yuding, canonical_author, poem_key


def main():
    shard_scores = {}
    for f in RANK_DIR.glob("poet.tang.rank.*.json"):
        parts = f.name.split(".")
        if not parts[-2].isdigit():
            continue
        entries = json.loads(f.read_text(encoding="utf-8"))
        shard_scores[int(parts[-2])] = [
            sum(max(0, e.get(k, 0) or 0) for k in ("baidu", "bing", "so360", "google"))
            for e in entries]

    id_map = json.loads(POEM_ID_MAP.read_text(encoding="utf-8"))
    tang_id_to_key = {tid: key for key, m in id_map.items() for tid in m["ids"]}

    poem_scores = {}
    for key, m in id_map.items():
        scores = [shard_scores[s][i] for s, i in m["refs"]
                  if s in shard_scores and i < len(shard_scores[s])]
        if scores:
            poem_scores[key] = max(scores)

    # 御定索引（供三百首内容兜底匹配 + 元数据聚合）
    from lib_qts import fold_t2s, strip_punct
    rows = []                      # (key, title, author, canon)
    title_idx = {}                 # (canon, 折叠题) -> key
    author_texts = defaultdict(list)   # canon -> [(key, 折叠全文)]
    for volume, poems in iter_yuding():
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            ac = canonical_author(p["author"])
            rows.append((key, p["title"], p["author"], ac))
            title_idx.setdefault((ac, fold_t2s(strip_punct(p["title"]))), key)
            author_texts[ac].append(
                (key, fold_t2s(strip_punct("".join(p.get("paragraphs", []))))))

    # 三百首锚定：① UUID join；② 兜底——同诗异抄本按（作者+折叠题）、
    # 组诗子首按首句包含于御定合并全文
    t300 = json.loads(TANG300.read_text(encoding="utf-8"))
    tang300 = {}
    unmatched_300 = []
    fallback_n = 0
    for e in t300:
        key = tang_id_to_key.get(e["id"])
        if not key:
            ac = canonical_author(e["author"])
            key = title_idx.get((ac, fold_t2s(strip_punct(e["title"]))))
            if not key and e.get("paragraphs"):
                first = fold_t2s(strip_punct(e["paragraphs"][0]))[:8]
                if len(first) >= 5:
                    for k, txt in author_texts.get(ac, []):
                        if first in txt:
                            key = k
                            break
            if key:
                fallback_n += 1
        if key:
            tags = [t for t in e.get("tags", []) if t != "唐诗三百首"]
            if key in tang300:
                tang300[key] = sorted(set(tang300[key]) | set(tags))
            else:
                tang300[key] = tags
        else:
            unmatched_300.append(f"{e['author']}《{e['title']}》")

    meta = {}
    poet_300 = defaultdict(int)
    poet_score = defaultdict(int)
    for key, title, author, ac in rows:
        if key in poem_scores or key in tang300:
            meta[key] = (title, author)
        if key in tang300:
            poet_300[ac] += 1
        poet_score[ac] += poem_scores.get(key, 0)

    famous = sorted(tang300, key=lambda k: -poem_scores.get(k, 0))
    poet_rank = sorted(poet_300, key=lambda a: (-poet_300[a], -poet_score[a]))

    out = {"poem_scores": poem_scores,
           "tang300": tang300,
           "famous_poems": [{"poem": k, "title": meta[k][0], "author": meta[k][1],
                             "tags": tang300[k], "score": poem_scores.get(k, 0)}
                            for k in famous],
           "top_poets_by_300": [[a, poet_300[a]] for a in poet_rank]}
    (ANALYSIS_DIR / "popularity.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")

    lines = ["# P6 热度榜单", "",
             f"- rank 分数覆盖：{len(poem_scores)}/{len(id_map)} 首（仅作参考，见下）",
             f"- 唐诗三百首命中御定：**{len(tang300)}** 键/366 条（内容兜底 {fallback_n}，未匹配 {len(unmatched_300)}）",
             "",
             "## ⚠️ 数据质量发现（本管线主要结论）", "",
             "搜索引擎命中数与诗篇知名度**不相关**：单字/短语题目（《雪》《月》《句》）与",
             "常用词作者名（無可、張為）虚高数个数量级，Top 榜完全被噪声占据。",
             "因此名篇榜以人工选本（唐诗三百首）为锚，rank 分数只在榜内排序时参考。",
             "前端展示热度徽章应仅使用三百首徽章；rank 分数不宜直接示人。",
             "",
             "## 名篇 Top 30（三百首锚定）", "",
             "| 诗 | 作者 | 题目 | 体裁标签 |", "|---|---|---|---|"]
    for k in famous[:30]:
        t, a = meta[k]
        lines.append(f"| {k} | {a} | {t} | {'、'.join(tang300[k][:3])} |")
    lines += ["", "## 诗人榜 Top 20（三百首入选数）", "",
              "| 诗人 | 入选数 |", "|---|---|"]
    for a in poet_rank[:20]:
        lines.append(f"| {a} | {poet_300[a]} |")
    if unmatched_300:
        lines += ["", "## 三百首未匹配清单（P2 映射缺口，人工核对候选）", ""]
        lines += [f"- {x}" for x in unmatched_300]
    (ANALYSIS_DIR / "popularity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"popularity: 300首 matched {len(tang300)}/366; "
          f"top poets {[(a, poet_300[a]) for a in poet_rank[:3]]}")


if __name__ == "__main__":
    main()

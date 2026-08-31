"""P4 诗题社交网络抽取。

唐诗题目高度结构化（"贈李白""酬樂天揚州初逢席上見贈""夢李白二首"），
规则：题目中出现已知诗人名（≥2 字，含字号别名），且名前有交往动词 → 记一条边。
输出：data/analysis/poet_network.{json,md}
"""
import json
from collections import Counter

from config import AUTHORS_MERGED, ANALYSIS_DIR
from lib_qts import iter_yuding, canonical_author, load_aliases, VARIANT_CHARS, poem_key

VERBS = set("贈答和酬送寄別哭挽憶懷訪過呈示簡招陪餞夢懐")
NAME_STOP_SUFFIX = ("氏", "皇帝", "皇后", "宮人", "女仙", "隱者")
NAME_STOP = {"佚名", "無名", "少年", "兒童", "先生", "神仙", "處士", "山人",
             "太守", "侍郎", "舍人", "學士", "判官", "明府", "尚書", "將軍"}


def build_name_index():
    """已知名 → 规范名。含作者表全名与字号别名，仅取 2–4 字名。"""
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))
    names = {}
    for key, rec in merged.items():
        for nm in set(rec["yuding_names"]) | {rec["tang_name"], rec["display"]}:
            nm = nm.strip()
            if 2 <= len(nm) <= 4 and nm not in NAME_STOP \
               and not nm.endswith(NAME_STOP_SUFFIX):
                names[nm.translate(VARIANT_CHARS)] = key
    for alias, canon in load_aliases().items():
        if 2 <= len(alias) <= 4 and not alias.endswith(NAME_STOP_SUFFIX):
            names[alias.translate(VARIANT_CHARS)] = canon
    return names


def find_names(title_n, names):
    """标题中的已知名命中（取最长匹配，去除被覆盖的短名）。"""
    hits = []
    for i in range(len(title_n)):
        for ln in (4, 3, 2):
            frag = title_n[i:i + ln]
            if len(frag) == ln and frag in names:
                hits.append((i, i + ln, frag))
                break
    pruned = []
    for h in hits:
        if not any(o != h and o[0] <= h[0] and h[1] <= o[1] for o in hits):
            pruned.append(h)
    # 官称假阳性：「X明府/X少府/X使君…」是官职敬称，非人名（送鄭明府 ≠ 鄭明）
    OFFICIAL_NEXT = ("府", "君", "曹", "尹", "丞", "簿", "尉")
    pruned = [h for h in pruned
              if not (h[1] < len(title_n) and title_n[h[1]] in OFFICIAL_NEXT)]
    return pruned


def main():
    names = build_name_index()
    edges = []
    pair_count = Counter()
    degree = Counter()

    for volume, poems in iter_yuding():
        for i, p in enumerate(poems, start=1):
            title_n = p["title"].translate(VARIANT_CHARS)
            src = canonical_author(p["author"])
            for start, _end, frag in find_names(title_n, names):
                tgt = names[frag]
                if tgt == src:
                    continue
                verb_pos = [j for j in range(start) if title_n[j] in VERBS]
                if not verb_pos:
                    continue
                verb = title_n[verb_pos[-1]]
                edges.append({"source": src, "target": tgt, "verb": verb,
                              "poem": poem_key(volume, i), "title": p["title"]})
                pair_count[(src, tgt)] += 1
                degree[src] += 1
                degree[tgt] += 1

    out = {
        "edge_count": len(edges),
        "node_count": len(degree),
        "edges": edges,
        "top_pairs": [{"source": s, "target": t, "count": c}
                      for (s, t), c in pair_count.most_common(100)],
        "top_degree": degree.most_common(50),
    }
    (ANALYSIS_DIR / "poet_network.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# P4 诗题社交网络报告", "",
             f"- 抽取边：**{len(edges)}** 条；涉及诗人节点：{len(degree)}",
             f"- 已知名词表规模：{len(names)}（作者名 + 字号别名）", "",
             "## 高频往来对 Top 30", "", "| 作者 | 对象 | 次数 |", "|---|---|---|"]
    for (s, t), c in pair_count.most_common(30):
        lines.append(f"| {s} | {t} | {c} |")
    lines += ["", "## 网络度数 Top 20", "", "| 诗人 | 度数 |", "|---|---|"]
    for n, d in degree.most_common(20):
        lines.append(f"| {n} | {d} |")
    lines += ["", "## 抽样边（前 10 条，人工抽检用）", ""]
    for e in edges[:10]:
        lines.append(f"- （{e['poem']}）{e['source']} —{e['verb']}→ {e['target']}：《{e['title']}》")
    (ANALYSIS_DIR / "poet_network.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"network: {len(edges)} edges, {len(degree)} nodes; "
          f"top pair {pair_count.most_common(1)}")


if __name__ == "__main__":
    main()

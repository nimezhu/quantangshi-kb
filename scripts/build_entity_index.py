"""P8 实体索引：人名 / 地名 / 邦国族群 / 时节（词表匹配法）。

词表来源（对标 shiji-kb 的实体体系，直接复用其词表）：
- 古人・地名・族群：../shiji-kb/kg/entity_index.json（简体；史记引用数过滤取名实体）
  —— 唐诗大量用汉以前人物地名作典故，史记词表正是现成的典故词典
- 邦国族群补充・唐代地名・年号・节令：本文件内人工词表（繁体）
匹配策略：正文与词表都折叠到简体空间比较（fold_t2s，P7 安全方向），
逐位置最长匹配（4→2 字）；展示名取语料中最常见的原繁体表面形式。
词表法有噪声（一词多义、非指称用法），精度上限见报告；逐字标注留给 Phase 5。

输出：data/entities/entity_poem_index.json + data/analysis/entities_report.md
用法: python build_entity_index.py
"""
import json
from collections import Counter, defaultdict

from config import DATA_DIR, ANALYSIS_DIR, WORKSPACE_ROOT
from lib_qts import (iter_yuding, canonical_author, fold_t2s, load_aliases,
                     normalize_author, poem_key)

SHIJI_ENTITY_INDEX = WORKSPACE_ROOT / "shiji-kb" / "kg" / "entity_index.json"
ENTITIES_DIR = DATA_DIR / "entities"

MIN_SHIJI_REFS = {"person": 5, "place": 5, "tribe": 3}
PERSON_STOP = {"高祖", "先王", "先帝", "大王", "王后", "太后", "夫人", "君王",
               "诸侯", "将军", "天子", "太子", "单于", "二世", "五帝", "三王",
               "公子", "中行", "无知", "不疑", "如意", "丈夫", "君子", "小人",
               "大夫", "王子", "美人", "佳人"}
PLACE_STOP = {"天下", "海内", "四海", "中国", "宫中", "天门", "云中", "太清",
              "北方", "南方", "东方", "西方", "人间", "山中", "水上", "关内",
              "白马", "东门", "北门", "南门", "西门", "中门"}

# 唐代邦国族群（史记词表没有的）
NATIONS_TANG = ["突厥", "吐蕃", "回紇", "回鶻", "大食", "天竺", "高麗", "新羅",
                "渤海", "南詔", "契丹", "吐谷渾", "龜茲", "于闐", "疏勒", "驃國"]
# 唐诗高频地名补充
PLACES_TANG = ["揚州", "金陵", "姑蘇", "杭州", "洞庭", "瀟湘", "巫峽", "劍閣",
               "玉門關", "陽關", "涼州", "峨眉", "廬山", "曲江", "樂遊原", "灞橋",
               "渭城", "江南", "塞北", "嶺南", "湘江", "錦官城", "白帝城", "黃鶴樓",
               "鸚鵡洲", "終南", "華清宮", "大明宮", "昆明池", "瞿塘", "夔州",
               "赤壁", "蘇州", "越州", "宣城", "夜郎", "潯陽", "浙江", "劍南"]
# 年号（选常见且不与常用词冲突者；長安/上元/萬歲等歧义年号不取）
ERAS = ["武德", "貞觀", "永徽", "顯慶", "麟德", "咸亨", "垂拱", "神龍", "景龍",
        "景雲", "先天", "開元", "天寶", "至德", "乾元", "寶應", "廣德", "永泰",
        "大曆", "建中", "興元", "貞元", "永貞", "元和", "長慶", "寶曆", "開成",
        "會昌", "大中", "咸通", "乾符", "廣明", "中和", "光啟", "龍紀", "景福",
        "乾寧", "光化", "天復", "天祐"]
# 节令
FESTIVALS = ["寒食", "清明", "上巳", "端午", "七夕", "中元", "中秋", "重陽",
             "重九", "除夜", "元日", "上元", "人日", "冬至", "臘日", "社日",
             "花朝"]

TYPE_LABELS = {"person": "古人", "place": "地名", "nation": "邦国族群", "time": "时节"}


def build_lexicon():
    """返回 {简体词: (type, from_shiji)}；插入按精度优先级，先入者胜。"""
    shiji = json.loads(SHIJI_ENTITY_INDEX.read_text(encoding="utf-8"))

    # 诗人名冲突集：凡与本库诗人名/字号相同的词不作"古人/地名"（诗人页已覆盖）
    poet_names = set()
    for alias, canon in load_aliases().items():
        poet_names.add(fold_t2s(alias))
        poet_names.add(fold_t2s(canon))
    from json import loads
    merged = loads((DATA_DIR / "authors_merged.json").read_text(encoding="utf-8"))
    for k, r in merged.items():
        if r["poem_count_yuding"] > 0:
            poet_names.add(fold_t2s(normalize_author(k)))

    lex = {}

    def add(name, typ, from_shiji):
        key = fold_t2s(name)
        if key not in lex:
            lex[key] = (typ, from_shiji)

    # 优先级：时节（最精确）→ 邦国 → 古人 → 地名
    for w in ERAS + FESTIVALS:
        add(w, "time", False)
    for w in NATIONS_TANG:
        add(w, "nation", False)
    for name, rec in shiji["tribe"].items():
        if 2 <= len(name) <= 4 and len(rec.get("refs", [])) >= MIN_SHIJI_REFS["tribe"]:
            add(name, "nation", True)
    for name, rec in shiji["person"].items():
        if (2 <= len(name) <= 4 and name not in PERSON_STOP
                and len(rec.get("refs", [])) >= MIN_SHIJI_REFS["person"]
                and fold_t2s(name) not in poet_names):
            add(name, "person", True)
    for w in PLACES_TANG:
        add(w, "place", False)
    for name, rec in shiji["place"].items():
        if (2 <= len(name) <= 4 and name not in PLACE_STOP
                and len(rec.get("refs", [])) >= MIN_SHIJI_REFS["place"]
                and fold_t2s(name) not in poet_names):
            add(name, "place", True)
    return lex


def main():
    ENTITIES_DIR.mkdir(parents=True, exist_ok=True)
    lex = build_lexicon()
    max_len = max(len(k) for k in lex)

    hits = defaultdict(lambda: {"count": 0, "poems": [], "surfaces": Counter()})
    for volume, poems in iter_yuding():
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            text = p["title"] + "\n" + "\n".join(p.get("paragraphs", []))
            folded = fold_t2s(text)
            pos = 0
            while pos < len(folded):
                matched = False
                for ln in range(min(max_len, len(folded) - pos), 1, -1):
                    frag = folded[pos:pos + ln]
                    if frag in lex:
                        typ, _ = lex[frag]
                        rec = hits[(typ, frag)]
                        rec["count"] += 1
                        rec["surfaces"][text[pos:pos + ln]] += 1
                        if not rec["poems"] or rec["poems"][-1] != key:
                            rec["poems"].append(key)
                        pos += ln
                        matched = True
                        break
                if not matched:
                    pos += 1

    out = {t: {} for t in TYPE_LABELS}
    for (typ, name), rec in hits.items():
        out[typ][name] = {
            "display": rec["surfaces"].most_common(1)[0][0],
            "count": rec["count"],
            "poem_count": len(rec["poems"]),
            "poems": rec["poems"],
            "shiji": lex[name][1],
        }
    (ENTITIES_DIR / "entity_poem_index.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")

    lines = ["# P8 实体索引报告（词表匹配法）", "",
             f"- 词表规模：{len(lex)}（史记词表 + 唐代补充；简体空间匹配）",
             "- ⚠️ 词表法局限：一词多义与非指称用法会产生误报（如「清明」形容词义、",
             "  「武陵」既是郡名也是桃源典故载体）；逐字精标留给 Phase 5 LLM 标注。", ""]
    for typ, label in TYPE_LABELS.items():
        ents = out[typ]
        total = sum(e["count"] for e in ents.values())
        lines += [f"## {label}：{len(ents)} 个实体，{total:,} 次命中", "",
                  "| 实体 | 命中 | 诗数 | 出自史记词表 |", "|---|---|---|---|"]
        for name, e in sorted(ents.items(), key=lambda kv: -kv[1]["count"])[:30]:
            lines.append(f"| {e['display']} | {e['count']} | {e['poem_count']} |"
                         f" {'✓' if e['shiji'] else ''} |")
        lines.append("")
    (ANALYSIS_DIR / "entities_report.md").write_text("\n".join(lines), encoding="utf-8")

    counts = {TYPE_LABELS[t]: len(out[t]) for t in out}
    print(f"entities: lexicon {len(lex)} → matched {counts}, "
          f"total hits {sum(e['count'] for t in out.values() for e in t.values()):,}")


if __name__ == "__main__":
    main()

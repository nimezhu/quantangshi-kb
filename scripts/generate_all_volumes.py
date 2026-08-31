"""全量生成：900 卷页面 + docs/index.html + t2s 字表 + volume_titles.json 缓存。

用法: python generate_all_volumes.py
"""
import html
import json
from collections import Counter

from config import (ANALYSIS_DIR, DOCS_DIR, VOLUMES_DIR, VOLUME_TITLES, YUDING_DIR)
from render_volume import esc, page, render_volume


def load_ctx():
    rhymes = json.loads((ANALYSIS_DIR / "rhymes.json").read_text(encoding="utf-8"))
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    return rhymes["per_poem"], pop["tang300"]


def build_t2s_map():
    """扫描语料全部文本，用 opencc 生成逐字 t2s 表 → docs/js/t2s-map.js。"""
    from opencc import OpenCC
    cc = OpenCC("t2s")
    chars = set()
    for f in YUDING_DIR.glob("*.json"):
        for p in json.loads(f.read_text(encoding="utf-8")):
            chars.update(p.get("title", ""), p["author"],
                         p.get("biography", ""), *p.get("paragraphs", []))
    mapping = {}
    for ch in chars:
        if "一" <= ch <= "鿿":
            s = cc.convert(ch)
            if s != ch and len(s) == 1:
                mapping[ch] = s
    js = ("// 构建时由 opencc(t2s) 按语料生成，勿手改（generate_all_volumes.py）\n"
          "window.T2S_MAP = " + json.dumps(mapping, ensure_ascii=False) + ";\n")
    (DOCS_DIR / "js" / "t2s-map.js").write_text(js, encoding="utf-8")
    return len(mapping)


def generate_index(vol_meta, t300):
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    wf = json.loads((ANALYSIS_DIR / "word_freq.json").read_text(encoding="utf-8"))
    total_poems = sum(m["poems"] for m in vol_meta.values())
    total_authors = len({a for m in vol_meta.values() for a in m["authors"]})

    # 名篇（三百首锚定，见 P6）
    famous = "\n".join(
        f'<li><a href="volumes/{f["poem"][:3]}.html#p{f["poem"][4:]}">{esc(f["title"])}</a>'
        f'<span class="fp-author">{esc(f["author"])}</span></li>'
        for f in pop["famous_poems"][:24])

    poets = "\n".join(
        f'<span class="chip">{esc(a)}<small>三百首×{n}</small></span>'
        for a, n in pop["top_poets_by_300"][:12])

    groups = []
    for g in range(9):
        lo, hi = g * 100 + 1, (g + 1) * 100
        cells = "\n".join(
            f'<a href="volumes/{v:03d}.html"><span class="vg-num">{v:03d}</span>'
            f'{esc(vol_meta[v]["top_author"])}</a>'
            for v in range(lo, hi + 1) if v in vol_meta)
        state = " open" if g == 0 else ""
        groups.append(f'<details class="vol-group"{state}><summary>卷 {lo:03d} – {hi:03d}</summary>'
                      f'<div class="volume-grid">\n{cells}\n</div></details>')

    top_chars = "、".join(c for c, _ in wf["char_top"][:10])
    body = f"""<div class="hero">
<h1>全唐詩</h1>
<div class="subtitle">御定全唐詩 · 交互式阅读</div>
<div class="stats">900 卷 · {total_poems:,} 首 · {total_authors:,} 位诗人 ·
{wf['total_chars']:,} 字 · 高频字：{top_chars}</div>
</div>
<h2 class="section-title">名篇（唐诗三百首）</h2>
<ul class="famous-list">
{famous}
</ul>
<h2 class="section-title">名家</h2>
<div class="poet-chips">
{poets}
</div>
<h2 class="section-title">分卷浏览</h2>
{"".join(groups)}
"""
    (DOCS_DIR / "index.html").write_text(
        page("全唐诗知识库", body, css_prefix="", home="index.html"), encoding="utf-8")


def main():
    VOLUMES_DIR.mkdir(parents=True, exist_ok=True)
    forms, t300 = load_ctx()

    vol_meta = {}
    for v in range(1, 901):
        name, n, authors = render_volume(v, forms, t300, vol_meta)
        counts = Counter(authors)
        vol_meta[v] = {"name": name, "poems": n,
                       "top_author": counts.most_common(1)[0][0] if counts else "",
                       "authors": sorted(counts)}
        if v % 100 == 0:
            print(f"  … {v}/900 卷完成")

    VOLUME_TITLES.write_text(
        json.dumps({str(v): {k: m[k] for k in ("name", "poems", "top_author")}
                    for v, m in vol_meta.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    n_map = build_t2s_map()
    generate_index(vol_meta, t300)
    print(f"done: 900 卷 + index.html + t2s-map.js（{n_map} 字）+ volume_titles.json")


if __name__ == "__main__":
    main()

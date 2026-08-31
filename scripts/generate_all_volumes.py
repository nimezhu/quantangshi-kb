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
    _install_entity_lexicon()
    return rhymes["per_poem"], pop["tang300"]


def _install_entity_lexicon():
    """把 P8 实体索引中有独立页面（诗数≥5）的实体注入渲染器做行内高亮。"""
    from config import DATA_DIR
    from render_volume import set_entity_lexicon
    idx_path = DATA_DIR / "entities" / "entity_poem_index.json"
    if not idx_path.exists():
        return
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    lex = {}
    for typ, ents in idx.items():
        for name, e in ents.items():
            if e["poem_count"] >= 5 and name not in lex:
                lex[name] = (typ, name)
    set_entity_lexicon(lex)
    print(f"  entity highlight lexicon: {len(lex)} entries")
    from render_volume import set_pilot_annotations
    pilot_path = DATA_DIR / "annotations" / "pilot_annotations.json"
    if pilot_path.exists():
        pilot = {k: v for k, v in
                 json.loads(pilot_path.read_text(encoding="utf-8")).items()
                 if not k.startswith("_")}
        set_pilot_annotations(pilot)
        print(f"  pilot annotations: {len(pilot)} poems")


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
        f'<li><a href="tang300/{f["poem"]}.html">{esc(f["title"])}</a>'
        f'<span class="fp-author">{esc(f["author"])}</span></li>'
        for f in pop["famous_poems"][:24])

    from urllib.parse import quote
    poets = "\n".join(
        f'<a class="chip" href="authors/{quote(a, safe="")}.html">{esc(a)}'
        f'<small>三百首×{n}</small></a>'
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
    rhymes = json.loads((ANALYSIS_DIR / "rhymes.json").read_text(encoding="utf-8"))
    form_chips = "".join(
        f'<span class="chip">{esc(fm)}<small>{n:,}</small></span>'
        for fm, n in list(rhymes["form_distribution"].items())[:8]
        if fm not in ("無正文",))
    body = f"""<nav class="chapter-nav">
<a href="search.html">🔍 搜索</a>
<a href="tang300.html">唐诗三百首</a>
<a href="authors/index.html">诗人索引</a>
<a href="entities/index.html">实体索引</a>
<a href="app/network/index.html">交游网络</a>
<a href="app/timeline/index.html">诗人长河</a>
<a href="app/map/index.html">诗中地图</a>
</nav>
<div class="hero">
<h1>全唐詩</h1>
<div class="subtitle">御定全唐詩 · 交互式阅读</div>
<form class="hero-search" action="search.html" method="get" autocomplete="off">
<input type="search" name="q" placeholder="搜索题目 / 作者 / 诗句（简繁均可）…">
<div id="live-results" class="live-results"></div>
</form>
<div class="stats">900 卷 · {total_poems:,} 首 · {total_authors:,} 位诗人 ·
{wf['total_chars']:,} 字 · 高频字：{top_chars}</div>
</div>
<div class="home-main">
<div class="home-side">
<div id="daily-card" class="daily-card"><div class="dp-foot">今日一诗加载中…</div></div>
</div>
<div class="home-rest">
<h2 class="section-title">名篇 <a class="more-link" href="tang300.html">唐诗三百首全览 →</a></h2>
<ul class="famous-list">
{famous}
</ul>
</div>
</div>
<h2 class="section-title">名家 <a class="more-link" href="authors/index.html">诗人索引 →</a></h2>
<div class="poet-chips">
{poets}
</div>
<h2 class="section-title">诗体</h2>
<div class="form-strip">
{form_chips}
</div>
<h2 class="section-title">分卷浏览</h2>
{"".join(groups)}
<script defer src="js/tangshi-home.js"></script>
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

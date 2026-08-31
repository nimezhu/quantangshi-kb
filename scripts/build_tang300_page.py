"""Phase 3: 唐诗三百首精选页（docs/tang300.html）。

数据：P6 popularity.json 的 tang300（key→tags）与 famous_poems（榜内排序）。
按 P5 诗体分组展示，组内按 P6 名篇榜排序。
用法: python build_tang300_page.py
"""
import json
from collections import defaultdict
from urllib.parse import quote

from config import ANALYSIS_DIR, DOCS_DIR
from lib_qts import canonical_author
from render_volume import esc, page


def main():
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    forms = json.loads((ANALYSIS_DIR / "rhymes.json").read_text(encoding="utf-8"))["per_poem"]

    groups = defaultdict(list)
    for f in pop["famous_poems"]:   # 已按榜内分数排序
        form = forms.get(f["poem"], ["其他"])[0] or "其他"
        groups[form].append(f)

    sections = []
    for form, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        rows = []
        for f in items:
            key = f["poem"]
            href = f"volumes/{key[:3]}.html#p{key[4:]}"
            a_href = f"authors/{quote(canonical_author(f['author']), safe='')}.html"
            tags = "、".join(f["tags"][:3])
            rows.append(
                f'<li><a class="para-num" href="{href}">（{key}）</a>'
                f'<a href="{href}">{esc(f["title"])}</a>'
                f'<span class="fp-author"><a href="{a_href}">{esc(f["author"])}</a>'
                + (f' · {esc(tags)}' if tags else "") + "</span></li>")
        sections.append(
            f'<h2 class="section-title">{esc(form)}'
            f'<span class="vol-count">{len(items)} 首</span></h2>'
            f'<ul class="famous-list">\n' + "\n".join(rows) + "\n</ul>")

    total = len(pop["famous_poems"])
    body = ('<nav class="chapter-nav"><a class="nav-home" href="index.html">🏠 目录</a>'
            '<a href="search.html">🔍 搜索</a><a href="authors/index.html">诗人索引</a></nav>\n'
            f'<h1>唐诗三百首<span class="vol-count">{total} 首（御定命中）· 按诗体分组</span></h1>\n'
            + "\n".join(sections))
    (DOCS_DIR / "tang300.html").write_text(
        page("唐诗三百首 - 全唐诗", body, css_prefix="", home="index.html"),
        encoding="utf-8")

    # 首页「今日一诗」数据：321 首三百首全文（API 不可用时的静态回退）
    from lib_qts import load_volume
    vol_cache = {}
    daily = []
    for f in sorted(pop["famous_poems"], key=lambda x: x["poem"]):
        key = f["poem"]
        vol = int(key[:3])
        if vol not in vol_cache:
            vol_cache[vol] = load_volume(vol)
        p = vol_cache[vol][int(key[4:]) - 1]
        daily.append({"key": key, "title": f["title"], "author": f["author"],
                      "form": forms.get(key, [""])[0],
                      "paragraphs": p.get("paragraphs", [])})
    (DOCS_DIR / "data" / "tang300_poems.json").write_text(
        json.dumps(daily, ensure_ascii=False), encoding="utf-8")
    print(f"tang300.html: {total} poems in {len(groups)} form groups; "
          f"tang300_poems.json baked ({len(daily)})")


if __name__ == "__main__":
    main()

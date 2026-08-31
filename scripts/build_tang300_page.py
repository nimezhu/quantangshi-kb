"""Phase 3: 唐诗三百首精选页（docs/tang300.html）+ 独立成册（docs/tang300/）。

数据：P6 popularity.json 的 tang300（key→tags）与 famous_poems（榜内排序）。
目录页按 P5 诗体分组；每首另编为独立页（上一首/下一首按目录序推进，
可跳回卷中上下文），复用卷渲染烘焙的 data/volumes/NNN.json 预渲染行。
用法: python build_tang300_page.py（须在 generate_all_volumes 之后）
"""
import json
from collections import defaultdict
from urllib.parse import quote

from config import ANALYSIS_DIR, DOCS_DIR
from lib_qts import canonical_author
from render_volume import esc, page

BOOK_DIR = DOCS_DIR / "tang300"


def build_book(ordered):
    """三百首独立成册：每首一页，按目录序前后翻页。先清目录防陈页残留。"""
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    for f in BOOK_DIR.glob("*.html"):
        f.unlink()
    vol_cache = {}
    total = len(ordered)
    for n, f in enumerate(ordered):
        key = f["poem"]
        vol, idx = key[:3], key[4:]
        if vol not in vol_cache:
            vol_cache[vol] = json.loads(
                (DOCS_DIR / "data" / "volumes" / f"{vol}.json")
                .read_text(encoding="utf-8"))
        p = vol_cache[vol]["poems"][f"p{idx}"]

        nav_parts = ['<a class="nav-home" href="../tang300.html">📜 三百首目录</a>']
        if n > 0:
            nav_parts.insert(0,
                f'<a href="{ordered[n-1]["poem"]}.html" '
                f'data-book="{ordered[n-1]["poem"]}">← 上一首</a>')
        nav_parts.append(f'<a href="../volumes/{vol}.html#p{idx}">📖 在卷中查看</a>')
        if n + 1 < total:
            nav_parts.append(
                f'<a href="{ordered[n+1]["poem"]}.html" '
                f'data-book="{ordered[n+1]["poem"]}">下一首 →</a>')
        # 预取相邻页，翻页即时呈现
        prefetch = "".join(
            f'<link rel="prefetch" href="{ordered[j]["poem"]}.html">'
            for j in (n - 1, n + 1) if 0 <= j < total)

        badges = ""
        if p["form"]:
            badges += f'<span class="badge badge-form">{esc(p["form"])}</span>'
        if p.get("pilot"):
            badges += ('<span class="badge badge-pilot" '
                       'title="实体经逐字精标（试点）">精標</span>')
        tags = "、".join((p.get("t300") or [])[:3])
        lines = "\n".join(f'<div class="line">{h}</div>' for h in p["lines"])
        a_href = f"../authors/{quote(p['canonical'], safe='')}.html"
        body = (
            f"{prefetch}"
            f'<nav class="chapter-nav" id="nav-top">' + "\n".join(nav_parts) + "</nav>\n"
            '<main id="content">'
            f'<h1 class="poem-title solo-title"><a class="para-num" href="#">（{key}）</a>'
            f'{esc(p["title"])}{badges}</h1>\n'
            f'<div class="poem-author"><a href="{a_href}">{esc(p["author"])}</a>'
            f'<span class="solo-vol"> · {esc(vol_cache[vol]["vol_name"])} · '
            f'三百首 第 {n+1}/{total} 首'
            + (f' · {esc(tags)}' if tags else "") + "</span></div>\n"
            f'<div class="poem" id="p{idx}"><div class="poem-body solo-body">\n'
            f"{lines}\n</div></div></main>\n"
            f'<nav class="chapter-nav" id="nav-bottom">' + "\n".join(nav_parts) + "</nav>\n"
            '<script defer src="../js/tangshi-book.js"></script>')
        (BOOK_DIR / f"{key}.html").write_text(
            page(f"{p['title']} - {p['author']} - 唐诗三百首", body),
            encoding="utf-8")

    # 成册顺序表：SPA 翻页用（键序即目录序）
    (DOCS_DIR / "data" / "tang300_order.json").write_text(
        json.dumps([f["poem"] for f in ordered], ensure_ascii=False),
        encoding="utf-8")
    return total


def main():
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    forms = json.loads((ANALYSIS_DIR / "rhymes.json").read_text(encoding="utf-8"))["per_poem"]

    groups = defaultdict(list)
    for f in pop["famous_poems"]:   # 已按榜内分数排序
        form = forms.get(f["poem"], ["其他"])[0] or "其他"
        groups[form].append(f)

    sections = []
    ordered = []
    for form, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        ordered.extend(items)
        rows = []
        for f in items:
            key = f["poem"]
            href = f"tang300/{key}.html"
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

    n_book = build_book(ordered)

    total = len(pop["famous_poems"])
    body = ('<nav class="chapter-nav"><a class="nav-home" href="index.html">🏠 目录</a>'
            '<a href="search.html">🔍 搜索</a><a href="authors/index.html">诗人索引</a></nav>\n'
            f'<h1>唐诗三百首<span class="vol-count">{total} 首（御定命中）· 按诗体分组 · '
            '独立成册可逐首翻阅 · 全部实体精标</span></h1>\n'
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
                      "canonical": canonical_author(f["author"]),
                      "form": forms.get(key, [""])[0],
                      "tags": f.get("tags", [])[:4],
                      "paragraphs": p.get("paragraphs", [])})
    (DOCS_DIR / "data" / "tang300_poems.json").write_text(
        json.dumps(daily, ensure_ascii=False), encoding="utf-8")
    print(f"tang300.html: {total} poems in {len(groups)} form groups; "
          f"book pages {n_book} → docs/tang300/; "
          f"tang300_poems.json baked ({len(daily)})")


if __name__ == "__main__":
    main()

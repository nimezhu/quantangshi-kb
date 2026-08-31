"""Phase 3: 诗人页生成。

每位在御定有作品的诗人一页：小传（御定 biography + authors.tang desc）、
统计、三百首入选、交游（P4 网络）、按卷分组的全部作品链接。
另生成 docs/authors/index.html 诗人总索引（按作品数分档）。
用法: python build_author_pages.py
"""
import json
from collections import defaultdict
from urllib.parse import quote

from config import ANALYSIS_DIR, AUTHORS_MERGED, DOCS_DIR
from lib_qts import iter_yuding, canonical_author, poem_key
from render_volume import esc, page

AUTHORS_DIR = DOCS_DIR / "authors"


def author_href(canonical, prefix=""):
    return f"{prefix}authors/{quote(canonical, safe='')}.html"


def main():
    AUTHORS_DIR.mkdir(parents=True, exist_ok=True)
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))
    net = json.loads((ANALYSIS_DIR / "poet_network.json").read_text(encoding="utf-8"))
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    t300 = pop["tang300"]

    # 逐卷收集每位诗人的作品（key, title, volume）
    works = defaultdict(list)
    titles = {}
    for volume, poems in iter_yuding():
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            works[canonical_author(p["author"])].append((key, p["title"], volume))
            titles[key] = p["title"]

    # 交游：canonical → Counter(对方 → 次数) + 样例
    contacts = defaultdict(lambda: defaultdict(int))
    samples = {}
    for e in net["edges"]:
        contacts[e["source"]][e["target"]] += 1
        contacts[e["target"]][e["source"]] += 1
        samples.setdefault((e["source"], e["target"]), e)

    poets = {k: v for k, v in merged.items() if v["poem_count_yuding"] > 0}
    for key, rec in poets.items():
        wl = works.get(key, [])
        n300 = sum(1 for k, _, _ in wl if k in t300)
        names = "、".join(n for n in rec["yuding_names"] if n != rec["display"])
        alias_line = f'<div class="poem-author">又作：{esc(names)}</div>' if names else ""

        bio = ""
        if rec["biography"]:
            bio += (f'<details class="biography" open><summary>小传（御定全唐詩）</summary>'
                    f'<p>{esc(rec["biography"])}</p></details>')
        if rec["desc"] and rec["desc"] != rec["biography"]:
            bio += (f'<details class="biography"><summary>小传（全唐诗数据库）</summary>'
                    f'<p>{esc(rec["desc"])}</p></details>')

        contact_html = ""
        cs = sorted(contacts.get(key, {}).items(), key=lambda x: -x[1])[:10]
        if cs:
            chips = []
            for other, n in cs:
                e = samples.get((key, other)) or samples.get((other, key))
                title_attr = f'《{e["title"]}》' if e else ""
                if other in poets:
                    chips.append(f'<a class="chip" href="{author_href(other, "../")}" '
                                 f'title="{esc(title_attr)}">{esc(other)}<small>×{n}</small></a>')
                else:
                    chips.append(f'<span class="chip">{esc(other)}<small>×{n}</small></span>')
            contact_html = ('<h2 class="section-title">交游（据诗题）</h2>'
                            f'<div class="poet-chips">{"".join(chips)}</div>')

        by_vol = defaultdict(list)
        for k, t, v in wl:
            by_vol[v].append((k, t))
        vol_blocks = []
        for v in sorted(by_vol):
            items = " ".join(
                f'<a href="../volumes/{v:03d}.html#p{k[4:]}">{esc(t)}</a>'
                + ('<span class="badge badge-300">三百首</span>' if k in t300 else "")
                for k, t in by_vol[v])
            vol_blocks.append(f'<div class="line"><span class="vg-num">卷{v:03d}</span>{items}</div>')

        stats = (f'{rec["poem_count_yuding"]} 首 · 见于 {len(by_vol)} 卷'
                 + (f' · 三百首入选 {n300}' if n300 else ""))
        body = (f'<nav class="chapter-nav"><a class="nav-home" href="../index.html">🏠 目录</a>'
                f'<a href="index.html">诗人索引</a></nav>\n'
                f'<h1>{esc(rec["display"])}<span class="vol-count">{stats}</span></h1>\n'
                f'{alias_line}{bio}{contact_html}\n'
                f'<h2 class="section-title">作品</h2>\n<div class="poem-body">\n'
                + "\n".join(vol_blocks) + "\n</div>")
        (AUTHORS_DIR / f"{key}.html").write_text(
            page(f"{rec['display']} - 全唐诗", body), encoding="utf-8")

    # 诗人索引页
    tiers = [("百首以上", 100, 10 ** 9), ("十首以上", 10, 100), ("十首以下", 1, 10)]
    sections = []
    ranked = sorted(poets.items(), key=lambda x: -x[1]["poem_count_yuding"])
    for label, lo, hi in tiers:
        chips = "".join(
            f'<a class="chip" href="{author_href(k)}">{esc(r["display"])}'
            f'<small>{r["poem_count_yuding"]}</small></a>'
            for k, r in ranked if lo <= r["poem_count_yuding"] < hi)
        sections.append(f'<h2 class="section-title">{label}</h2>'
                        f'<div class="poet-chips">{chips}</div>')
    body = (f'<nav class="chapter-nav"><a class="nav-home" href="../index.html">🏠 目录</a></nav>\n'
            f'<h1>诗人索引<span class="vol-count">{len(poets)} 人</span></h1>\n'
            + "\n".join(sections))
    # 索引页在 authors/ 目录下，chip 链接需相对本目录
    body = body.replace('href="authors/', 'href="')
    (AUTHORS_DIR / "index.html").write_text(page("诗人索引 - 全唐诗", body), encoding="utf-8")
    print(f"author pages: {len(poets)} + index.html")


if __name__ == "__main__":
    main()

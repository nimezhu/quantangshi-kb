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
    seq_dir = DOCS_DIR / "data" / "authors"
    seq_dir.mkdir(parents=True, exist_ok=True)
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))
    net = json.loads((ANALYSIS_DIR / "poet_network.json").read_text(encoding="utf-8"))
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    t300 = pop["tang300"]

    from config import DATA_DIR
    from lib_qts import canonical_author as _ca
    years_raw = json.loads((DATA_DIR / "poet_years.json").read_text(encoding="utf-8"))
    years = {_ca(k): v for k, v in years_raw.items() if not k.startswith("_")}

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

        # 逐首阅读序列（按卷序）
        (seq_dir / f"{key}.json").write_text(
            json.dumps({"display": rec["display"],
                        "poems": [k for k, _, _ in wl]}, ensure_ascii=False),
            encoding="utf-8")
        reader_href = (f'../poem.html?id={wl[0][0]}&author={quote(key, safe="")}'
                       if wl else "")

        y = years.get(key)
        life = ""
        if y:
            life = (f'{"约 " if y[2] else ""}{y[0] or "?"}–{y[1] or "?"}')

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
        author_q = quote(key, safe="")
        vol_blocks = []
        for v in sorted(by_vol):
            items = " ".join(
                f'<a class="para-num wl-pn" href="../volumes/{v:03d}.html#p{k[4:]}" '
                f'title="在卷中查看">（{k[4:]}）</a>'
                f'<a href="../poem.html?id={k}&author={author_q}">{esc(t)}</a>'
                + ('<span class="badge badge-300">三百首</span>' if k in t300 else "")
                for k, t in by_vol[v])
            vol_blocks.append(f'<div class="line"><span class="vg-num">卷{v:03d}</span>{items}</div>')

        stats = ((f"{life} · " if life else "")
                 + f'{rec["poem_count_yuding"]} 首 · 见于 {len(by_vol)} 卷'
                 + (f' · 三百首入选 {n300}' if n300 else ""))
        reader_btn = (f'<a href="{reader_href}">▶ 逐首阅读</a>' if reader_href else "")
        body = (f'<nav class="chapter-nav"><a class="nav-home" href="../index.html">🏠 目录</a>'
                f'<a href="index.html">诗人索引</a>{reader_btn}</nav>\n'
                f'<h1>{esc(rec["display"])}<span class="vol-count">{stats}</span></h1>\n'
                f'{alias_line}{bio}{contact_html}\n'
                f'<h2 class="section-title">作品'
                f'<span class="vol-count">题目进逐首阅读，（编号）进卷中上下文</span></h2>\n'
                f'<div class="poem-body worklist">\n'
                + "\n".join(vol_blocks) + "\n</div>")
        (AUTHORS_DIR / f"{key}.html").write_text(
            page(f"{rec['display']} - 全唐诗", body), encoding="utf-8")

    # 诗人索引页：名家卡片 → 百首/十首分层 → 长尾折叠
    ranked = sorted(poets.items(), key=lambda x: -x[1]["poem_count_yuding"])
    t300_of = dict(pop.get("top_poets_by_300", []))

    def href(k):
        return f"{quote(k, safe='')}.html"

    FEATURED = 24
    NOT_A_POET = {"不詳", "無名氏", "佚名", "無名", "闕名"}
    cards = []
    featured = [(k, r) for k, r in ranked if r["display"] not in NOT_A_POET][:FEATURED]
    for k, r in featured:
        n300 = t300_of.get(k, 0)
        badge = f'<span class="pc-300">三百首×{n300}</span>' if n300 else ""
        cards.append(
            f'<a class="poet-card" href="{href(k)}">{badge}'
            f'<span class="pc-name">{esc(r["display"])}</span>'
            f'<span class="pc-stats">{r["poem_count_yuding"]} 首 · '
            f'{len(r["volumes"])} 卷</span></a>')

    def col_links(items):
        return "".join(
            f'<a href="{href(k)}">{esc(r["display"])}'
            f'<span class="cnt">{r["poem_count_yuding"]}</span></a>'
            for k, r in items)

    featured_keys = {k for k, _ in featured}
    hundred = [(k, r) for k, r in ranked
               if r["poem_count_yuding"] >= 100 and k not in featured_keys]
    ten = [(k, r) for k, r in ranked if 10 <= r["poem_count_yuding"] < 100]
    tail = [(k, r) for k, r in ranked if r["poem_count_yuding"] < 10]

    body = (
        '<nav class="chapter-nav"><a class="nav-home" href="../index.html">🏠 目录</a>'
        '<a href="../search.html">🔍 搜索</a>'
        '<a href="#t100">百首以上</a><a href="#t10">十首以上</a><a href="#tail">其余</a></nav>\n'
        f'<h1>诗人索引<span class="vol-count">{len(poets)} 人 · 按存诗数</span></h1>\n'
        '<h2 class="section-title">名家</h2>\n'
        f'<div class="poet-card-grid">{"".join(cards)}</div>\n'
        f'<h2 class="section-title" id="t100">百首以上'
        f'<span class="vol-count">{len(hundred)} 人</span></h2>\n'
        f'<div class="poet-cols cols-wide">{col_links(hundred)}</div>\n'
        f'<h2 class="section-title" id="t10">十首以上'
        f'<span class="vol-count">{len(ten)} 人</span></h2>\n'
        f'<div class="poet-cols">{col_links(ten)}</div>\n'
        f'<h2 class="section-title" id="tail">十首以下</h2>\n'
        f'<details class="tail-fold"><summary>展开 {len(tail)} 位存诗较少的诗人</summary>'
        f'<div class="poet-cols cols-dense">{col_links(tail)}</div></details>')
    (AUTHORS_DIR / "index.html").write_text(page("诗人索引 - 全唐诗", body), encoding="utf-8")
    print(f"author pages: {len(poets)} + index.html "
          f"(featured {FEATURED}, 100+ {len(hundred)}, 10+ {len(ten)}, tail {len(tail)})")


if __name__ == "__main__":
    main()

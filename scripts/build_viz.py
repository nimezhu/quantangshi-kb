"""Phase 6: 可视化数据与页面。

1. 交游网络 → docs/app/network/data.json（P4 边聚合成对 + 节点度数/存诗/三百首）
   前端 canvas 力导向图（docs/app/network/，手写零依赖 JS）
2. 诗人长河 → docs/app/timeline/index.html（服务端生成整页 SVG）
   横轴为御定编次（卷号，大体以时代先后为序——本书按时代编排；非生卒年）
用法: python build_viz.py
"""
import json
from collections import Counter, defaultdict

from config import ANALYSIS_DIR, AUTHORS_MERGED, DOCS_DIR
from render_volume import esc, page
from urllib.parse import quote

NET_DIR = DOCS_DIR / "app" / "network"
TL_DIR = DOCS_DIR / "app" / "timeline"


def build_network_data():
    net = json.loads((ANALYSIS_DIR / "poet_network.json").read_text(encoding="utf-8"))
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))
    t300 = dict(pop.get("top_poets_by_300", []))

    pair = Counter()
    sample = {}
    for e in net["edges"]:
        k = tuple(sorted((e["source"], e["target"])))
        pair[k] += 1
        sample.setdefault(k, f'{e["source"]}《{e["title"]}》')

    degree = Counter()
    for (a, b), w in pair.items():
        degree[a] += w
        degree[b] += w

    nodes = []
    for name, d in degree.items():
        rec = merged.get(name, {})
        nodes.append({"id": name, "d": d,
                      "poems": rec.get("poem_count_yuding", 0),
                      "n300": t300.get(name, 0),
                      "page": rec.get("poem_count_yuding", 0) > 0})
    links = [{"s": a, "t": b, "w": w, "eg": sample[(a, b)]}
             for (a, b), w in pair.items()]

    NET_DIR.mkdir(parents=True, exist_ok=True)
    (NET_DIR / "data.json").write_text(
        json.dumps({"nodes": nodes, "links": links}, ensure_ascii=False),
        encoding="utf-8")
    return len(nodes), len(links)


ERAS = [("初唐", 618, 712), ("盛唐", 712, 766), ("中唐", 766, 835),
        ("晚唐", 835, 907), ("五代", 907, 979)]
Y0, Y1 = 550, 1000


def build_timeline():
    from config import DATA_DIR
    from lib_qts import canonical_author
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    t300 = dict(pop.get("top_poets_by_300", []))

    raw_years = json.loads((DATA_DIR / "poet_years.json").read_text(encoding="utf-8"))
    years = {canonical_author(k): v for k, v in raw_years.items()
             if not k.startswith("_")}

    NOT_A_POET = {"不詳", "無名氏", "佚名", "無名", "闕名"}
    pool = [(k, r) for k, r in merged.items()
            if r["poem_count_yuding"] >= 30 and r["display"] not in NOT_A_POET]
    dated = [(k, r, years[k]) for k, r in pool if k in years]
    undated = [(k, r) for k, r in pool if k not in years]
    dated.sort(key=lambda kv: (kv[2][0] if kv[2][0] is not None
                               else kv[2][1] - 55, -kv[1]["poem_count_yuding"]))

    W, ROW, LABEL = 1150, 17, 110
    H = len(dated) * ROW + 78
    x = lambda yr: LABEL + (yr - Y0) / (Y1 - Y0) * (W - LABEL - 20)

    rows = []
    # 朝代分期底带（交替着色 + 顶部标签）
    for j, (label, e0, e1) in enumerate(ERAS):
        rows.append(f'<rect x="{x(e0):.0f}" y="20" width="{x(e1)-x(e0):.0f}" '
                    f'height="{H-52}" fill="{"#f7f1df" if j % 2 else "#fdf9ec"}"/>')
        rows.append(f'<text x="{(x(e0)+x(e1))/2:.0f}" y="34" class="era">'
                    f'{label}</text>')
    for yr in range(600, 1000, 50):
        rows.append(f'<line x1="{x(yr):.0f}" y1="20" x2="{x(yr):.0f}" y2="{H-32}" '
                    f'stroke="#eadfc2" stroke-width="1"/>')
        rows.append(f'<text x="{x(yr):.0f}" y="{H-16}" class="tick">{yr}</text>')

    for i, (k, r, (b, d, circa)) in enumerate(dated):
        y = 52 + i * ROW
        n300 = t300.get(k, 0)
        color = "#a5453b" if n300 else "#c9a55a"
        op = min(0.95, 0.35 + r["poem_count_yuding"] / 1500)
        href = f"../../authors/{quote(k, safe='')}.html"
        life = (f'{"约 " if circa else ""}{b or "?"}–{d or "?"}')
        title = (f'{r["display"]}（{life}）：{r["poem_count_yuding"]} 首'
                 + (f'，三百首×{n300}' if n300 else ""))
        rows.append(f'<a href="{href}"><title>{esc(title)}</title>'
                    f'<text x="{LABEL-6}" y="{y+4}" class="pname">'
                    f'{esc(r["display"])}</text>')
        if b is not None and d is not None:
            dash = ' stroke-dasharray="3,2" stroke="#b09a50" stroke-width="0.8"' \
                if circa else ""
            rows.append(f'<rect x="{x(b):.0f}" y="{y-5}" '
                        f'width="{max(x(d)-x(b), 3):.0f}" height="9" rx="4" '
                        f'fill="{color}" opacity="{op:.2f}"{dash}/>')
        else:
            yr = b if b is not None else d
            rows.append(f'<circle cx="{x(yr):.0f}" cy="{y}" r="4.5" fill="{color}" '
                        f'opacity="{op:.2f}"/>'
                        f'<line x1="{x(yr)-14:.0f}" y1="{y}" x2="{x(yr)+14:.0f}" '
                        f'y2="{y}" stroke="{color}" stroke-width="1" '
                        f'stroke-dasharray="2,3" opacity="0.6"/>')
        rows.append('</a>')

    svg = (f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'xmlns="http://www.w3.org/2000/svg">'
           '<style>.pname{font-size:11px;fill:#6b5636;text-anchor:end;'
           'font-family:"Noto Serif TC",serif}.tick{font-size:10px;fill:#b09a50;'
           'text-anchor:middle}.era{font-size:12px;fill:#a08040;text-anchor:middle;'
           'letter-spacing:0.3em;font-family:"Noto Serif TC",serif}'
           'a:hover rect,a:hover circle{opacity:1}a:hover .pname{fill:#8B0000}</style>'
           + "".join(rows) + "</svg>")

    und_chips = "".join(
        f'<a class="chip" href="../../authors/{quote(k, safe="")}.html">'
        f'{esc(r["display"])}<small>{r["poem_count_yuding"]}</small></a>'
        for k, r in sorted(undated, key=lambda kv: -kv[1]["poem_count_yuding"]))

    body = ('<nav class="chapter-nav"><a class="nav-home" href="../../index.html">🏠 目录</a>'
            '<a href="../network/index.html">交游网络</a></nav>\n'
            f'<h1>诗人长河<span class="vol-count">存诗 ≥30 首 · 生卒可考 {len(dated)} 位</span></h1>\n'
            '<p class="search-status">横轴为<b>公元纪年</b>（生卒年据史料人工核对表 '
            '<code>data/poet_years.json</code>，月份多无考，精确到年；虚线框 = 约略，'
            '圆点 = 仅生年或卒年可考）。红色 = 有唐诗三百首入选，透明度 ≈ 存诗数。'
            '点击进入诗人页。</p>\n'
            f'<div style="overflow-x:auto">{svg}</div>\n'
            f'<h2 class="section-title">生卒无考<span class="vol-count">'
            f'{len(undated)} 位</span></h2>\n'
            f'<div class="poet-chips">{und_chips}</div>')
    TL_DIR.mkdir(parents=True, exist_ok=True)
    (TL_DIR / "index.html").write_text(
        page("诗人长河 - 全唐诗", body, css_prefix="../../", home="../../index.html"),
        encoding="utf-8")
    return len(dated), len(undated)


if __name__ == "__main__":
    n, l = build_network_data()
    m, u = build_timeline()
    print(f"viz: network {n} nodes / {l} pair-links → app/network/data.json; "
          f"timeline {m} dated + {u} undated poets → app/timeline/index.html")

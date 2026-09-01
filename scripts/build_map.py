"""Phase 6 补遗: 诗中地图（docs/app/map/index.html，服务端生成整页 SVG）。

写意底图：手绘简化海岸线 + 黄河/长江（非精确地理，风格与刻本纸色一致），
点位来自人工核对表 data/place_coords.json × P8 实体索引的诗数。
点面积 ∝ 诗数，虚线圈 = 泛称地域，紫色 = 邦国族群；点击进实体页。
用法: python build_map.py（依赖 build_entity_index 产出）
"""
import json
import math

from config import DATA_DIR, DOCS_DIR
from render_volume import esc, page
from urllib.parse import quote

MAP_DIR = DOCS_DIR / "app" / "map"
LON0, LON1, LAT0, LAT1 = 90, 130, 18, 46
W, H = 1150, 780

# 写意海岸线与大河（经纬度折线，手绘近似）
COAST = [(121.5, 40.6), (119.5, 39.8), (117.8, 39.0), (118.2, 38.1), (119.2, 37.5),
         (120.9, 37.7), (122.5, 37.4), (122.2, 36.8), (120.8, 36.3), (119.5, 35.2),
         (120.3, 33.0), (121.3, 32.0), (121.9, 31.2), (121.2, 30.3), (121.7, 29.6),
         (120.9, 28.3), (119.9, 26.8), (119.4, 25.8), (118.2, 24.5), (116.7, 23.3),
         (114.8, 22.7), (113.8, 22.5), (112.2, 21.8), (110.6, 21.2), (109.6, 21.5),
         (108.5, 21.6)]
YELLOW_R = [(96.0, 35.4), (98.5, 34.9), (100.5, 36.0), (103.0, 36.1), (103.9, 37.4),
            (105.8, 38.9), (106.8, 40.5), (109.0, 40.7), (110.8, 40.4), (111.2, 39.0),
            (110.6, 37.0), (110.5, 35.6), (112.0, 35.0), (114.2, 34.9), (116.0, 35.3),
            (117.8, 36.8), (118.9, 37.6)]
YANGTZE = [(91.0, 33.2), (94.5, 32.5), (97.3, 31.3), (99.5, 29.0), (101.5, 27.0),
           (103.0, 26.6), (104.5, 28.6), (106.2, 29.4), (107.6, 30.0), (109.5, 30.8),
           (111.2, 30.5), (112.6, 30.3), (114.3, 30.6), (116.0, 29.9), (117.6, 30.5),
           (119.2, 31.7), (120.6, 31.9), (121.8, 31.4)]


def xy(lon, lat):
    x = (lon - LON0) / (LON1 - LON0) * (W - 40) + 20
    y = (LAT1 - lat) / (LAT1 - LAT0) * (H - 60) + 20
    return x, y


def path(points):
    return "M " + " L ".join(f"{xy(a,b)[0]:.0f} {xy(a,b)[1]:.0f}" for a, b in points)


def main():
    idx = json.loads((DATA_DIR / "entities" / "entity_poem_index.json")
                     .read_text(encoding="utf-8"))
    coords = {k: v for k, v in json.loads(
        (DATA_DIR / "place_coords.json").read_text(encoding="utf-8")).items()
        if not k.startswith("_")}

    ents = []
    missing = []
    for typ in ("place", "nation"):
        for name, e in idx[typ].items():
            if name in coords:
                lon, lat, region = coords[name]
                ents.append((typ, name, e["display"], e["poem_count"],
                             lon, lat, region, e["poem_count"] >= 5))
            elif e["poem_count"] >= 20 and typ == "place":
                missing.append(f'{e["display"]}({e["poem_count"]})')
    ents.sort(key=lambda t: -t[3])

    svg = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           'xmlns="http://www.w3.org/2000/svg">',
           '<style>'
           '.coast{fill:none;stroke:#cfe0e8;stroke-width:5;stroke-linecap:round;'
           'stroke-linejoin:round}'
           '.river{fill:none;stroke:#bcd4e6;stroke-width:2.6;stroke-linecap:round;'
           'stroke-linejoin:round}'
           '.rlabel{font-size:11px;fill:#9db8c8;font-family:"Noto Serif TC",serif}'
           '.pt{opacity:0.8}.pt:hover{opacity:1}'
           '.plabel{font-size:11px;fill:#6b5636;font-family:"Noto Serif TC",serif}'
           '.plabel-big{font-size:13px;font-weight:600;fill:#5a3d1e}'
           'a:hover .plabel{fill:#8B0000}'
           '</style>',
           f'<path class="coast" d="{path(COAST)}"/>',
           f'<path class="river" d="{path(YELLOW_R)}"/>',
           f'<path class="river" d="{path(YANGTZE)}"/>']
    hx, hy = xy(101.5, 36.6)
    svg.append(f'<text class="rlabel" x="{hx:.0f}" y="{hy:.0f}">黄河</text>')
    yx, yy = xy(99.2, 28.3)
    svg.append(f'<text class="rlabel" x="{yx:.0f}" y="{yy:.0f}">长江</text>')

    labeled = 0
    for typ, name, disp, n, lon, lat, region, has_page in ents:
        x, y = xy(lon, lat)
        r = max(2.5, min(2.2 * math.sqrt(n), 26))
        color = "#9370DB" if typ == "nation" else "#a5453b"
        dash = ' stroke-dasharray="3,3"' if region else ""
        fill_op = 0.32 if region else 0.55
        dot = (f'<circle class="pt" cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" '
               f'fill="{color}" fill-opacity="{fill_op}" stroke="{color}" '
               f'stroke-width="1"{dash}/>')
        label = ""
        if n >= 60 or (typ == "nation" and n >= 30):
            big = " plabel-big" if n >= 200 else ""
            label = (f'<text class="plabel{big}" x="{x + r + 3:.0f}" '
                     f'y="{y + 4:.0f}">{esc(disp)}</text>')
            labeled += 1
        title = f'<title>{esc(disp)}：{n} 首</title>'
        if has_page:
            href = f"../../entities/{typ}_{quote(name, safe='')}.html"
            svg.append(f'<a href="{href}">{title}{dot}{label}</a>')
        else:
            svg.append(f'<g>{title}{dot}{label}</g>')
    svg.append("</svg>")

    note = ("底图为写意简化（海岸线与黄河/长江示意，非精确地理），点位取唐代地望"
            "约略坐标（人工核对表 <code>data/place_coords.json</code>，欢迎修订）。"
            "点面积 ∝ 诗数；虚线圈 = 泛称地域；紫色 = 邦国族群；点击进实体页。"
            "远域（天竺、大食、龟兹、于阗、疏勒等）在图幅之外未标。")
    body = ('<style>body{max-width:1210px}</style>'
            '<nav class="chapter-nav"><a class="nav-home" href="../../index.html">🏠 目录</a>'
            '<a href="../../entities/index.html">实体索引</a>'
            '<a href="../network/index.html">交游网络</a>'
            '<a href="../timeline/index.html">诗人长河</a></nav>\n'
            f'<h1>诗中地图<span class="vol-count">{len(ents)} 处可标 · '
            f'{labeled} 处标名</span></h1>\n'
            f'<p class="search-status">{note}</p>\n'
            f'<div style="overflow-x:auto">{"".join(svg)}</div>')
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    (MAP_DIR / "index.html").write_text(
        page("诗中地图 - 全唐诗", body, css_prefix="../../", home="../../index.html"),
        encoding="utf-8")
    print(f"map: {len(ents)} plotted ({labeled} labeled); "
          f"uncoordinated hot places: {', '.join(missing[:10])}")


if __name__ == "__main__":
    main()

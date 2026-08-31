"""渲染单卷：御定全唐詩 JSON → docs/volumes/NNN.html。

页面骨架借鉴 shiji-kb render_shiji_html.py：导航条（顶/底）、Purple Numbers、
折叠小传；诗体版式为本项目新写。徽章数据来自 Phase 1 分析产出。

CLI（调试用）: python render_volume.py 001
批量入口: generate_all_volumes.py
"""
import html
import json
import re
import sys
from urllib.parse import quote

from config import YUDING_DIR, VOLUMES_DIR
from lib_qts import canonical_author, fold_t2s, load_volume, poem_key

SENT = re.compile(r"[^。！？]+[。！？]*")

# Phase 5：词表实体行内高亮（P8 索引中有独立页面的实体；由 generate_all 注入）
_ENT_LEX = {}
_ENT_MAXLEN = 0


def set_entity_lexicon(lex):
    """lex: {折叠简体名: (type, 实体键)}，仅含有页面的实体。"""
    global _ENT_LEX, _ENT_MAXLEN
    _ENT_LEX = lex
    _ENT_MAXLEN = max((len(k) for k in lex), default=0)


# 实体精标试点（data/annotations/pilot_annotations.json；见其 _comment）
_PILOT = {}


def set_pilot_annotations(d):
    global _PILOT
    _PILOT = d


_TYPE_LABEL = {"person": "人物", "place": "地名", "nation": "邦国族群", "time": "时节"}


def _ent_html(surface, typ, target, note=None):
    key = target or fold_t2s(surface)
    tip = esc(note) if note else f"{_TYPE_LABEL.get(typ, typ)} · 精标"
    attrs = f'class="ent ent-{typ}" data-note="{tip}"'
    if key in _ENT_LEX:
        ltyp = _ENT_LEX[key][0]
        return (f'<a {attrs} '
                f'href="../entities/{ltyp}_{quote(key, safe="")}.html">'
                f'{esc(surface)}</a>')
    return f'<span {attrs}>{esc(surface)}</span>'


def apply_pilot(sents, entries):
    """精标应用：条目按阅读序游标式定位（表面形逐句查找，命中即包）。
    返回 (每句 html 列表, 未命中条目数)。"""
    out = []
    ei = 0
    miss = 0
    for sent in sents:
        pos = 0
        parts = []
        while ei < len(entries):
            e = entries[ei]
            surface = e[0]
            j = sent.find(surface, pos)
            if j == -1:
                break
            parts.append(decorate_line(sent[pos:j]))
            parts.append(_ent_html(surface, e[1],
                                   e[2] if len(e) > 2 else None,
                                   e[3] if len(e) > 3 else None))
            pos = j + len(surface)
            ei += 1
        parts.append(decorate_line(sent[pos:]))
        out.append("".join(parts))
    miss = len(entries) - ei
    return out, miss


def wrap_entities(sent):
    """句内实体标注：最长匹配折叠空间，命中片段包成实体链接（原字展示）。"""
    if not _ENT_LEX:
        return decorate_line(sent)
    folded = fold_t2s(sent)
    out, plain, pos = [], [], 0
    while pos < len(folded):
        hit = None
        for ln in range(min(_ENT_MAXLEN, len(folded) - pos), 1, -1):
            frag = folded[pos:pos + ln]
            if frag in _ENT_LEX:
                hit = (ln, *_ENT_LEX[frag])
                break
        if hit:
            if plain:
                out.append(decorate_line("".join(plain)))
                plain = []
            ln, typ, ekey = hit
            out.append(f'<a class="ent ent-{typ}" '
                       f'href="../entities/{typ}_{quote(ekey, safe="")}.html">'
                       f'{esc(sent[pos:pos + ln])}</a>')
            pos += ln
        else:
            plain.append(sent[pos])
            pos += 1
    if plain:
        out.append(decorate_line("".join(plain)))
    return "".join(out)


def esc(s):
    return html.escape(s, quote=False)


def page(title, body, css_prefix="../", home="../index.html"):
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{css_prefix}css/tangshi-styles.css">
<link rel="stylesheet" href="{css_prefix}css/chapter-nav.css">
<link rel="icon" href="{css_prefix}favicon.svg">
<script defer src="{css_prefix}js/purple-numbers.js"></script>
<script defer src="{css_prefix}js/t2s-map.js"></script>
<script defer src="{css_prefix}js/tangshi-settings.js"></script>
</head>
<body>
{body}
<footer>数据源：<a href="https://github.com/chinese-poetry/chinese-poetry">chinese-poetry</a>（御定全唐詩，MIT）·
设计借鉴 <a href="https://github.com/baojie/shiji-kb">shiji-kb</a> ·
<a href="{home}">全唐诗知识库</a></footer>
</body>
</html>
"""


def nav_bar(volume, vol_names):
    parts = []
    if volume > 1:
        parts.append(f'<a href="{volume-1:03d}.html">← 上一卷</a>')
    parts.append('<a class="nav-home" href="../index.html">🏠 目录</a>')
    parts.append('<a href="../search.html">🔍 搜索</a>')
    if volume < 900:
        parts.append(f'<a href="{volume+1:03d}.html">下一卷 →</a>')
    return '<nav class="chapter-nav">' + "\n".join(parts) + "</nav>"


def author_link(raw_author, prefix="../"):
    """作者名 → 诗人页链接（每位御定作者都有页面，见 build_author_pages）。"""
    canon = canonical_author(raw_author)
    return (f'<a href="{prefix}authors/{quote(canon, safe="")}.html">'
            f'{esc(raw_author)}</a>')


LIANJU = re.compile(r"——([^，。！？；：、\s—]{2,7})")


def decorate_line(sent):
    """行内标记：□ 阙字样式；联句 ——作者 → 作者标签。"""
    out = esc(sent)
    out = out.replace("□", '<span class="lacuna" title="底本阙字">□</span>')
    out = LIANJU.sub(r'<span class="lianju-author" title="联句作者">\1</span>', out)
    return out


def render_poem(volume, idx, p, forms, t300):
    """返回 (卷页诗块 HTML, 单诗数据 dict)。单诗数据供独立诗页/三百首成册复用。"""
    key = poem_key(volume, idx)
    anchor = f"p{idx:02d}"
    badges = ""
    form = forms.get(key)
    form_name = form[0] if form and form[0] != "無正文" else ""
    if form_name:
        badges += f'<span class="badge badge-form">{esc(form_name)}</span>'
    if key in t300:
        tags = "、".join(t300[key][:3])
        badges += f'<span class="badge badge-300" title="{esc(tags)}">三百首</span>'
    if "mismatch_kept" in p.get("flags", []):
        badges += ('<span class="badge badge-review" '
                   'title="双源文本存疑，保留御定原文待审">文本待审</span>')
    sents = [s for para in p.get("paragraphs", []) for s in SENT.findall(para)]
    if key in _PILOT:
        line_html, miss = apply_pilot(sents, _PILOT[key])
        if miss:
            print(f"  ⚠ 精标 {key}: {miss} 条未命中")
        badges += ('<span class="badge badge-pilot" '
                   'title="实体经逐字精标（试点），非词表自动匹配">精標</span>')
    else:
        line_html = [wrap_entities(s) for s in sents]
    lines = "\n".join(f'<div class="line">{h}</div>' for h in line_html)
    block = (
        f'<div class="poem" id="{anchor}">\n'
        f'<h3 class="poem-title"><a class="para-num" href="#{anchor}">（{key}）</a>'
        f'{esc(p["title"])}{badges}'
        f'<a class="solo-link" href="../poem.html?id={key}" title="单独页查看">❐</a></h3>\n'
        f'<div class="poem-author">{author_link(p["author"])}</div>\n'
        "{bio}"
        f'<div class="poem-body">\n{lines}\n</div>\n</div>'
    )
    pdata = {"key": key, "title": p["title"], "author": p["author"],
             "canonical": canonical_author(p["author"]),
             "lines": line_html, "form": form_name,
             "t300": t300.get(key), "src": p.get("text_source", "yuding"),
             "pilot": key in _PILOT}
    return block, pdata


def render_volume(volume, forms, t300, vol_names):
    poems = load_volume(volume)   # 应用 P9 文本修复覆盖层
    vol_name = poems[0].get("volume", f"卷{volume}") if poems else f"卷{volume}"
    seen_bio = set()
    blocks = []
    vol_json = {}
    for i, p in enumerate(poems, start=1):
        blk, pdata = render_poem(volume, i, p, forms, t300)
        pdata["prev"] = poem_key(volume, i - 1) if i > 1 else None
        pdata["next"] = poem_key(volume, i + 1) if i < len(poems) else None
        vol_json[f"p{i:02d}"] = pdata
        bio = ""
        author = p["author"].strip()
        if author not in seen_bio and p.get("biography", "").strip():
            seen_bio.add(author)
            bio = (f'<details class="biography"><summary>{esc(author)} · 小传</summary>'
                   f'<p>{esc(p["biography"].strip())}</p></details>\n')
        blocks.append(blk.replace("{bio}", bio))

    vol_data_dir = VOLUMES_DIR.parent / "data" / "volumes"
    vol_data_dir.mkdir(parents=True, exist_ok=True)
    (vol_data_dir / f"{volume:03d}.json").write_text(
        json.dumps({"vol_name": vol_name, "poems": vol_json}, ensure_ascii=False),
        encoding="utf-8")

    nav = nav_bar(volume, vol_names)
    title = f"御定全唐詩·{vol_name}"
    body = (f"{nav}\n<h1>{esc(title)}"
            f'<span class="vol-count">卷 {volume:03d} / 900 · {len(poems)} 首</span></h1>\n'
            '<main id="content">\n' + "\n".join(blocks) + f"\n</main>\n{nav}")
    out = VOLUMES_DIR / f"{volume:03d}.html"
    out.write_text(page(title, body), encoding="utf-8")
    return vol_name, len(poems), [p["author"].strip() for p in poems]


if __name__ == "__main__":
    from generate_all_volumes import load_ctx
    v = int(sys.argv[1])
    forms, t300 = load_ctx()
    VOLUMES_DIR.mkdir(parents=True, exist_ok=True)
    name, n, _ = render_volume(v, forms, t300, {})
    print(f"rendered {v:03d} ({name}, {n} poems) → docs/volumes/{v:03d}.html")

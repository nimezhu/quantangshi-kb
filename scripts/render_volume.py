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
    key = poem_key(volume, idx)
    anchor = f"p{idx:02d}"
    badges = ""
    form = forms.get(key)
    if form and form[0] != "無正文":
        badges += f'<span class="badge badge-form">{esc(form[0])}</span>'
    if key in t300:
        tags = "、".join(t300[key][:3])
        badges += f'<span class="badge badge-300" title="{esc(tags)}">三百首</span>'
    if "mismatch_kept" in p.get("flags", []):
        badges += ('<span class="badge badge-review" '
                   'title="双源文本存疑，保留御定原文待审">文本待审</span>')
    lines = []
    for para in p.get("paragraphs", []):
        for sent in SENT.findall(para):
            lines.append(f'<div class="line">{wrap_entities(sent)}</div>')
    return (
        f'<div class="poem" id="{anchor}">\n'
        f'<h3 class="poem-title"><a class="para-num" href="#{anchor}">（{key}）</a>'
        f'{esc(p["title"])}{badges}</h3>\n'
        f'<div class="poem-author">{author_link(p["author"])}</div>\n'
        "{bio}"
        f'<div class="poem-body">\n' + "\n".join(lines) + "\n</div>\n</div>"
    )


def render_volume(volume, forms, t300, vol_names):
    poems = load_volume(volume)   # 应用 P9 文本修复覆盖层
    vol_name = poems[0].get("volume", f"卷{volume}") if poems else f"卷{volume}"
    seen_bio = set()
    blocks = []
    for i, p in enumerate(poems, start=1):
        blk = render_poem(volume, i, p, forms, t300)
        bio = ""
        author = p["author"].strip()
        if author not in seen_bio and p.get("biography", "").strip():
            seen_bio.add(author)
            bio = (f'<details class="biography"><summary>{esc(author)} · 小传</summary>'
                   f'<p>{esc(p["biography"].strip())}</p></details>\n')
        blocks.append(blk.replace("{bio}", bio))

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

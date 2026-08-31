"""Phase 3b: 实体索引页面（docs/entities/）。

- entities/index.html：四类（古人/地名/邦国族群/时节）chips 总览
- 每个诗数 ≥ MIN_POEMS 的实体一页：命中诗列表（题目/作者/链接）；
  出自史记词表的实体附 shiji-kb wiki 互链（跨库典故网络）
用法: python build_entity_pages.py（依赖 build_entity_index.py 与 search_index.json）
"""
import json
from urllib.parse import quote

from config import DATA_DIR, DOCS_DIR
from render_volume import esc, page

ENTITIES_OUT = DOCS_DIR / "entities"
MIN_POEMS = 5
MAX_LIST = 300
TYPE_LABELS = {"person": "古人", "place": "地名", "nation": "邦国族群", "time": "时节"}
SHIJI_WIKI = "https://baojie.github.io/shiji-kb/wiki/#"


def main():
    ENTITIES_OUT.mkdir(parents=True, exist_ok=True)
    idx = json.loads((DATA_DIR / "entities" / "entity_poem_index.json")
                     .read_text(encoding="utf-8"))
    meta = {e[0]: (e[1], e[2]) for e in json.loads(
        (DOCS_DIR / "data" / "search_index.json").read_text(encoding="utf-8"))}

    n_pages = 0
    sections = []
    for typ, label in TYPE_LABELS.items():
        ents = sorted(idx[typ].items(), key=lambda kv: -kv[1]["count"])
        chips = []
        for name, e in ents:
            disp = e["display"]
            if e["poem_count"] >= MIN_POEMS:
                n_pages += 1
                fname = f"{typ}_{name}.html"
                chips.append(f'<a class="chip" href="{quote(fname, safe="")}">{esc(disp)}'
                             f'<small>{e["poem_count"]}</small></a>')

                rows = []
                for k in e["poems"][:MAX_LIST]:
                    t, a = meta.get(k, ("?", "?"))
                    rows.append(
                        f'<div class="search-hit"><a class="para-num" '
                        f'href="../volumes/{k[:3]}.html#p{k[4:]}">（{k}）</a>'
                        f'<a href="../volumes/{k[:3]}.html#p{k[4:]}">{esc(t)}</a>'
                        f'<span class="fp-author">{esc(a)}</span></div>')
                more = (f'<p class="search-status">（共 {e["poem_count"]} 首，'
                        f'仅列前 {MAX_LIST}）</p>' if e["poem_count"] > MAX_LIST else "")
                shiji_link = (f'<p><a class="chip" href="{SHIJI_WIKI}{quote(name)}" '
                              f'target="_blank">↗ 史记知识库 wiki：{esc(name)}</a>'
                              '<span class="search-status">（史记词表实体，典故源头可溯）</span></p>'
                              if e["shiji"] else "")
                body = (f'<nav class="chapter-nav"><a class="nav-home" href="../index.html">🏠 目录</a>'
                        f'<a href="index.html">实体索引</a></nav>\n'
                        f'<h1>{esc(disp)}<span class="vol-count">{label} · '
                        f'{e["poem_count"]} 首 / {e["count"]} 次</span></h1>\n'
                        f'{shiji_link}\n<h2 class="section-title">命中诗篇</h2>\n'
                        + "\n".join(rows) + more)
                (ENTITIES_OUT / fname).write_text(
                    page(f"{disp} - 全唐诗实体", body), encoding="utf-8")
            else:
                chips.append(f'<span class="chip">{esc(disp)}'
                             f'<small>{e["poem_count"]}</small></span>')
        sections.append(f'<h2 class="section-title">{label}'
                        f'<span class="vol-count">{len(ents)} 个</span></h2>'
                        f'<div class="poet-chips">{"".join(chips)}</div>')

    body = ('<nav class="chapter-nav"><a class="nav-home" href="../index.html">🏠 目录</a>'
            '<a href="../search.html">🔍 搜索</a></nav>\n'
            '<h1>实体索引<span class="vol-count">词表匹配 · 借史记知识库词表</span></h1>\n'
            '<p class="search-status">古人/地名/族群词表复用 '
            '<a href="https://github.com/baojie/shiji-kb">shiji-kb</a> 实体索引 —— '
            '唐诗中的汉前典故与史记实体天然互通；词表法有噪声，精标注为远期计划。</p>\n'
            + "\n".join(sections))
    (ENTITIES_OUT / "index.html").write_text(
        page("实体索引 - 全唐诗", body), encoding="utf-8")
    print(f"entity pages: {n_pages} + index.html")


if __name__ == "__main__":
    main()

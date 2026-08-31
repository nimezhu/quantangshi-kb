"""Phase 3: 搜索索引与搜索页。

- 一级索引 docs/data/search_index.json：全部 43,103 首的 [key, 题目, 作者, 诗体]
- 全文索引 docs/data/fulltext_{0..8}.json：每 100 卷一片，[key, 题目, 作者, 正文]
  （懒加载：只有用户切到"全文"模式才逐片拉取）
- 生成 docs/search.html
繁简匹配策略（P7 结论）：索引存繁体原文；前端把 查询词 与 索引条目 都经
T2S_MAP 逐字折叠成简体后比较，简繁输入均可命中。
用法: python build_search_index.py
"""
import json

from config import ANALYSIS_DIR, DOCS_DIR
from lib_qts import iter_yuding, poem_key
from render_volume import page

DATA_OUT = DOCS_DIR / "data"


def main():
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    forms = json.loads((ANALYSIS_DIR / "rhymes.json").read_text(encoding="utf-8"))["per_poem"]

    primary = []
    shards = [[] for _ in range(9)]
    for volume, poems in iter_yuding():
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            form = forms.get(key, ["", ""])[0]
            primary.append([key, p["title"], p["author"], form])
            shards[(volume - 1) // 100].append(
                [key, p["title"], p["author"], "\n".join(p.get("paragraphs", []))])

    (DATA_OUT / "search_index.json").write_text(
        json.dumps(primary, ensure_ascii=False), encoding="utf-8")
    for g, shard in enumerate(shards):
        (DATA_OUT / f"fulltext_{g}.json").write_text(
            json.dumps(shard, ensure_ascii=False), encoding="utf-8")

    body = """<nav class="chapter-nav"><a class="nav-home" href="index.html">🏠 目录</a>
<a href="authors/index.html">诗人索引</a><a href="tang300.html">唐诗三百首</a></nav>
<h1>搜索<span class="vol-count">43,103 首 · 简繁均可</span></h1>
<div class="search-box">
<input type="search" id="q" placeholder="题目 / 作者 / 诗句…" autofocus>
<label><input type="checkbox" id="fulltext"> 搜诗句全文（首次稍慢）</label>
</div>
<div id="status" class="search-status"></div>
<div id="results"></div>
<script defer src="js/tangshi-search.js"></script>"""
    (DOCS_DIR / "search.html").write_text(
        page("搜索 - 全唐诗", body, css_prefix="", home="index.html"), encoding="utf-8")

    sizes = [(DATA_OUT / f).stat().st_size // 1024 for f in
             ["search_index.json"] + [f"fulltext_{g}.json" for g in range(9)]]
    print(f"search index: {len(primary)} poems; primary {sizes[0]}KB, "
          f"fulltext shards {min(sizes[1:])}-{max(sizes[1:])}KB ×9")


if __name__ == "__main__":
    main()

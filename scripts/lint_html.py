"""渲染结果校验（借鉴 shiji-kb 的 lint 门禁思想）。

检查：卷文件齐全 / 每卷诗数与源 JSON 一致 / 锚点唯一且与 PN 链接一致 /
prev-next 链接可达 / index 覆盖 900 卷 / 名篇链接锚点真实存在 / 模板占位符无泄漏 /
诗人页齐全且作者链接可达 / 搜索与三百首页面资产齐全。
用法: python lint_html.py   （出错以非零码退出）
"""
import json
import re
import sys
from urllib.parse import unquote

from config import AUTHORS_MERGED, DOCS_DIR, VOLUMES_DIR, YUDING_DIR

ID_RE = re.compile(r'<div class="poem" id="(p\d+)">')
PN_RE = re.compile(r'<a class="para-num" href="#(p\d+)">')
NAV_RE = re.compile(r'<a href="(\d{3})\.html">')
AUTHOR_RE = re.compile(r'href="\.\./authors/([^"]+)\.html"')


def main():
    errors = []
    author_links = set()

    for v in range(1, 901):
        f = VOLUMES_DIR / f"{v:03d}.html"
        if not f.exists():
            errors.append(f"缺少卷文件 {f.name}")
            continue
        htmltext = f.read_text(encoding="utf-8")
        src_n = len(json.loads((YUDING_DIR / f"{v:03d}.json").read_text(encoding="utf-8")))
        ids = ID_RE.findall(htmltext)
        if len(ids) != src_n:
            errors.append(f"{f.name}: 诗块 {len(ids)} ≠ 源 {src_n}")
        if len(set(ids)) != len(ids):
            errors.append(f"{f.name}: 锚点重复")
        if set(PN_RE.findall(htmltext)) != set(ids):
            errors.append(f"{f.name}: PN 链接与锚点不一致")
        for tgt in NAV_RE.findall(htmltext):
            if not (VOLUMES_DIR / f"{tgt}.html").exists():
                errors.append(f"{f.name}: 导航目标 {tgt}.html 不存在")
        if "{bio}" in htmltext:
            errors.append(f"{f.name}: 模板占位符泄漏")
        author_links.update(unquote(m) for m in AUTHOR_RE.findall(htmltext))

    # 诗人页：数量与 authors_merged 一致，卷页作者链接全部可达
    authors_dir = DOCS_DIR / "authors"
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))
    expected = {k for k, r in merged.items() if r["poem_count_yuding"] > 0}
    actual = {f.stem for f in authors_dir.glob("*.html")} - {"index"}
    if actual != expected:
        errors.append(f"诗人页数量不符: 实际 {len(actual)} vs 预期 {len(expected)}"
                      f"（差异样例 {list(expected ^ actual)[:3]}）")
    for a in author_links:
        if a not in actual:
            errors.append(f"卷页作者链接无对应诗人页: {a}")
    if not (authors_dir / "index.html").exists():
        errors.append("缺少 authors/index.html")

    # 三百首页与搜索页
    t300 = (DOCS_DIR / "tang300.html")
    if t300.exists():
        t = t300.read_text(encoding="utf-8")
        for vol, anchor in re.findall(r'href="volumes/(\d{3})\.html#(p\d+)"', t):
            if f'id="{anchor}"' not in (VOLUMES_DIR / f"{vol}.html").read_text(encoding="utf-8"):
                errors.append(f"tang300 链接失效: {vol}.html#{anchor}")
    else:
        errors.append("缺少 tang300.html")

    index = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    for a in re.findall(r'href="authors/([^"]+)\.html"', index):
        if unquote(a) not in actual and a != "index":
            errors.append(f"index 名家链接无对应诗人页: {unquote(a)}")

    # 实体索引页：chips 链接可达，实体页诗链接锚点抽查
    ent_dir = DOCS_DIR / "entities"
    if (ent_dir / "index.html").exists():
        ent_index = (ent_dir / "index.html").read_text(encoding="utf-8")
        ent_links = re.findall(r'href="((?:person|place|nation|time)_[^"]+\.html)"',
                               ent_index)
        for l in ent_links:
            if not (ent_dir / unquote(l)).exists():
                errors.append(f"entities/index 链接失效: {unquote(l)}")
        for l in ent_links[::20]:  # 抽查 1/20 实体页的诗锚点
            body = (ent_dir / unquote(l)).read_text(encoding="utf-8")
            for vol, anchor in re.findall(r'href="\.\./volumes/(\d{3})\.html#(p\d+)"',
                                          body)[:10]:
                if f'id="{anchor}"' not in (VOLUMES_DIR / f"{vol}.html").read_text(
                        encoding="utf-8"):
                    errors.append(f"实体页 {unquote(l)} 诗链接失效: {vol}.html#{anchor}")
    else:
        errors.append("缺少 entities/index.html")
    linked = set(re.findall(r'href="volumes/(\d{3})\.html"', index))
    if len(linked) != 900:
        errors.append(f"index.html 卷链接 {len(linked)}/900")
    for vol, anchor in re.findall(r'href="volumes/(\d{3})\.html#(p\d+)"', index):
        page = (VOLUMES_DIR / f"{vol}.html").read_text(encoding="utf-8")
        if f'id="{anchor}"' not in page:
            errors.append(f"index 名篇链接失效: {vol}.html#{anchor}")

    for a in ("css/tangshi-styles.css", "css/chapter-nav.css", "js/purple-numbers.js",
              "js/t2s-map.js", "js/tangshi-settings.js", "js/tangshi-search.js",
              "js/tangshi-home.js", "data/tang300_poems.json",
              "search.html", "data/search_index.json",
              *(f"data/fulltext_{g}.json" for g in range(9))):
        if not (DOCS_DIR / a).exists():
            errors.append(f"缺少资产 {a}")

    if errors:
        print(f"✗ lint 未通过（{len(errors)} 项）：")
        for e in errors[:30]:
            print("  -", e)
        sys.exit(1)
    print(f"✓ lint 通过：900 卷 + {len(actual)} 诗人页 + index/search/tang300，"
          "锚点/导航/作者/名篇链接全部有效")


if __name__ == "__main__":
    main()

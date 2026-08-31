"""渲染结果校验（借鉴 shiji-kb 的 lint 门禁思想）。

检查：卷文件齐全 / 每卷诗数与源 JSON 一致 / 锚点唯一且与 PN 链接一致 /
prev-next 链接可达 / index 覆盖 900 卷 / 名篇链接锚点真实存在 / 模板占位符无泄漏。
用法: python lint_html.py   （出错以非零码退出）
"""
import json
import re
import sys

from config import DOCS_DIR, VOLUMES_DIR, YUDING_DIR

ID_RE = re.compile(r'<div class="poem" id="(p\d+)">')
PN_RE = re.compile(r'<a class="para-num" href="#(p\d+)">')
NAV_RE = re.compile(r'<a href="(\d{3})\.html">')


def main():
    errors = []

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

    index = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
    linked = set(re.findall(r'href="volumes/(\d{3})\.html"', index))
    if len(linked) != 900:
        errors.append(f"index.html 卷链接 {len(linked)}/900")
    for vol, anchor in re.findall(r'href="volumes/(\d{3})\.html#(p\d+)"', index):
        page = (VOLUMES_DIR / f"{vol}.html").read_text(encoding="utf-8")
        if f'id="{anchor}"' not in page:
            errors.append(f"index 名篇链接失效: {vol}.html#{anchor}")

    for a in ("css/tangshi-styles.css", "css/chapter-nav.css", "js/purple-numbers.js",
              "js/t2s-map.js", "js/tangshi-settings.js"):
        if not (DOCS_DIR / a).exists():
            errors.append(f"缺少资产 {a}")

    if errors:
        print(f"✗ lint 未通过（{len(errors)} 项）：")
        for e in errors[:30]:
            print("  -", e)
        sys.exit(1)
    print("✓ lint 通过：900 卷 + index，锚点/导航/名篇链接全部有效")


if __name__ == "__main__":
    main()

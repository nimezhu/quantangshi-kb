#!/bin/bash
# 站点全量重建 + lint 门禁。顺序即依赖：
# 实体索引先行（卷页行内高亮需要词表）→ 卷页 → 诗人页 → 搜索索引 →
# 实体页（需搜索索引的题目表）→ 三百首 → 平仄数据 → lint
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
$PY build_entity_index.py
$PY generate_all_volumes.py
$PY build_author_pages.py
$PY build_search_index.py
$PY build_entity_pages.py
$PY build_tang300_page.py
$PY build_strains_data.py
$PY build_viz.py
$PY lint_html.py

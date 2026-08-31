#!/bin/bash
# 站点全量重建（Phase 2+3）+ lint 门禁
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
$PY generate_all_volumes.py
$PY build_author_pages.py
$PY build_search_index.py
$PY build_entity_index.py
$PY build_entity_pages.py
$PY build_tang300_page.py
$PY lint_html.py

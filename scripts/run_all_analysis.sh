#!/bin/bash
# Phase 1 分析管线一键重跑（P1→P7，P2 依赖 P1，P5/P6 依赖 P2）
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
$PY build_author_index.py       # P1 作者归一
$PY build_poem_id_map.py        # P2 双源对齐
$PY analyze_word_frequency.py   # P3 字/词频与意象
$PY extract_poet_network.py     # P4 诗题社交网络
$PY analyze_rhymes.py           # P5 韵脚与诗体
$PY build_popularity.py         # P6 热度榜单
$PY analyze_simp_trad.py        # P7 简繁质检
echo "=== 全部管线完成，产出见 data/ 与 data/analysis/ ==="

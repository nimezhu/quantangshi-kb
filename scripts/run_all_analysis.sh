#!/bin/bash
# 分析管线一键重跑。顺序即依赖：P1/P2 用御定原始文本，P9 生成文本修复覆盖层，
# 其后管线（P3-P8）自动读取修复后的语料。
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
$PY build_author_index.py       # P1 作者归一（原始）
$PY build_poem_id_map.py        # P2 双源对齐（原始，raw=True）
$PY build_clean_corpus.py       # P9 文本修复覆盖层
$PY analyze_word_frequency.py   # P3 字/词频与意象
$PY extract_poet_network.py     # P4 诗题社交网络
$PY analyze_rhymes.py           # P5 韵脚与诗体
$PY build_popularity.py         # P6 热度榜单
$PY analyze_simp_trad.py        # P7 简繁质检
$PY build_entity_index.py       # P8 实体索引（借史记词表）
echo "=== 全部管线完成，产出见 data/ 与 data/analysis/ ==="

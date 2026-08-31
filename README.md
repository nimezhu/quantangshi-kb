# quantangshi-kb 全唐诗知识库

《御定全唐詩》900 卷（43,103 首）的静态浏览器与分析管线，设计与方法论借鉴 [shiji-kb](../shiji-kb)。

- **规划**: [PLAN.md](PLAN.md)
- **数据源**: [chinese-poetry](../chinese-poetry)（MIT，只读引用）：御定全唐詩为主干，poet.tang 系列（UUID/平仄/热度/三百首）为增强层
- **分析产出**: `data/analysis/`（P1 作者归一、P2 双源对齐、P3 词频、P4 诗题社交网络、P5 韵脚诗体、P6 名篇榜、P7 简繁质检）

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/run_all_analysis.sh   # 重跑全部分析管线
./serve.sh 8000                    # 本地预览 docs/（Phase 2 起可用）
```

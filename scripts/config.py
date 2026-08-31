"""quantangshi-kb 路径常量。所有脚本从这里导入路径，不得各自硬编码。"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

# 上游数据（只读！）
POETRY_ROOT = WORKSPACE_ROOT / "chinese-poetry"
YUDING_DIR = POETRY_ROOT / "御定全唐詩" / "json"        # 900 卷，主干
QTS_DIR = POETRY_ROOT / "全唐诗"                        # poet.tang 分片，增强层
STRAINS_DIR = POETRY_ROOT / "strains" / "json"          # 平仄（按 id 对齐 poet.tang）
RANK_DIR = POETRY_ROOT / "rank" / "poet"                # 热度（按分片+下标对齐 poet.tang）
AUTHORS_TANG = QTS_DIR / "authors.tang.json"
TANG300 = QTS_DIR / "唐诗三百首.json"

# 本项目派生数据
DATA_DIR = PROJECT_ROOT / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"
DOCS_DIR = PROJECT_ROOT / "docs"
VOLUMES_DIR = DOCS_DIR / "volumes"

AUTHOR_ALIASES = DATA_DIR / "author_aliases.json"
CORPUS_PATCH = DATA_DIR / "corpus_patch.json"   # P9 文本修复覆盖层
AUTHORS_MERGED = DATA_DIR / "authors_merged.json"
POEM_ID_MAP = DATA_DIR / "poem_id_map.json"
VOLUME_TITLES = DATA_DIR / "volume_titles.json"

for d in (DATA_DIR, ANALYSIS_DIR):
    d.mkdir(parents=True, exist_ok=True)

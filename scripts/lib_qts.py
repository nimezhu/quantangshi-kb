"""共享数据加载与作者名归一工具。"""
import json
import re
from functools import lru_cache

from config import YUDING_DIR, QTS_DIR, AUTHOR_ALIASES

# 异体字/过度简繁转换归一映射（仅用于匹配比较，不改变展示文本）。
# 御定全唐詩数据存在机器简→繁过度转换（方干→方幹、鄭谷→鄭穀、于→於），
# 两侧同时折叠到同一代表字后再比较。
VARIANT_CHARS = str.maketrans({
    "羣": "群", "峯": "峰", "祕": "秘", "啓": "启",
    "竒": "奇", "邨": "村", "喦": "岩", "巗": "岩", "嵒": "岩", "巖": "岩",
    "廻": "回", "逈": "迥", "臯": "皋", "鄕": "乡",
    # 过度转换对（御定侧多余的繁体 ↔ authors.tang 侧本字）
    "幹": "干", "穀": "谷", "鹹": "咸", "於": "于", "紮": "扎",
    "複": "复", "復": "复", "爲": "為", "徵": "征", "祐": "佑",
    "敻": "夐", "玨": "珏", "麴": "麹", "準": "准", "凖": "准",
    "叡": "睿", "樸": "朴", "棲": "栖", "眘": "昚", "昇": "升",
})

_TRAILING_NUM = re.compile(r"\d+$")


def normalize_author(name: str) -> str:
    """匹配用归一：去首尾空白、去御定消歧数字后缀（李瀚1→李瀚）、异体字折叠。"""
    name = name.strip()
    name = _TRAILING_NUM.sub("", name)
    return name.translate(VARIANT_CHARS)


@lru_cache(maxsize=1)
def load_aliases() -> dict:
    """别名表：alias → canonical（人工核对种子 + 后续修订）。值统一做归一处理。"""
    if not AUTHOR_ALIASES.exists():
        return {}
    raw = json.loads(AUTHOR_ALIASES.read_text(encoding="utf-8"))
    return {k: normalize_author(v) for k, v in raw.items() if not k.startswith("_")}


def canonical_author(name: str) -> str:
    """别名表优先，其次归一形。返回规范名（用于跨源匹配的键）。"""
    aliases = load_aliases()
    if name in aliases:
        return aliases[name]
    norm = normalize_author(name)
    return aliases.get(norm, norm)


def iter_yuding():
    """按卷序迭代御定全唐诗：yield (volume:int, poems:list[dict])。"""
    for f in sorted(YUDING_DIR.glob("*.json")):
        yield int(f.stem), json.loads(f.read_text(encoding="utf-8"))


def iter_tang_shards():
    """按分片序迭代 poet.tang：yield (shard_start:int, poems:list[dict])。"""
    shards = sorted(QTS_DIR.glob("poet.tang.*.json"),
                    key=lambda p: int(p.name.split(".")[-2]))
    for f in shards:
        yield int(f.name.split(".")[-2]), json.loads(f.read_text(encoding="utf-8"))


PUNCT = "，。！？；：、「」『』（）·□?○—…"


def split_clauses(paragraphs):
    """把 paragraphs 拆成句读单元（诗行）列表。"""
    text = "".join(paragraphs)
    return [c for c in re.split(r"[，。！？；：、\s]+", text) if c]


def strip_punct(text: str) -> str:
    return re.sub(r"[，。！？；：、「」『』（）\s·□?○—…]+", "", text)


def poem_key(volume: int, idx: int) -> str:
    """卷内永久编号：001-01 （卷 1 第 1 首，1 起）。"""
    return f"{volume:03d}-{idx:02d}"

"""Phase 4: 平仄数据按卷烘焙（docs/data/strains/NNN.json）。

strains/json 按 UUID 对齐 poet.tang；经 P2 映射到御定诗，服务端对齐到
渲染行（与 render_volume 相同的句读切分），仅在字数完全吻合时输出，
避免前端错位。标记映射：平→○ 仄→● 其余→◌。
用法: python build_strains_data.py
"""
import json
import re

from config import DOCS_DIR, POEM_ID_MAP, STRAINS_DIR
from lib_qts import iter_yuding, strip_punct, poem_key

SENT = re.compile(r"[^。！？]+[。！？]*")
MARK = {"平": "○", "仄": "●"}

OUT = DOCS_DIR / "data" / "strains"


def main():
    strains_by_id = {}
    for f in STRAINS_DIR.glob("poet.tang.*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            if e.get("strains"):
                strains_by_id[e["id"]] = "".join(e["strains"])

    id_map = json.loads(POEM_ID_MAP.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    total = aligned = 0
    for volume, poems in iter_yuding():
        vol_data = {}
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            m = id_map.get(key)
            if not m:
                continue
            raw = "".join(strains_by_id.get(tid, "") for tid in m["ids"])
            marks = [MARK.get(c, "◌") for c in raw if c in "平仄○？"]
            total += 1
            # 与渲染行对齐：句读单元序列，字数须整体吻合
            lines = []
            for para in p.get("paragraphs", []):
                lines.extend(SENT.findall(para))
            counts = [len(strip_punct(ln)) for ln in lines]
            if sum(counts) != len(marks) or not marks:
                continue
            aligned += 1
            out_lines, pos = [], 0
            for n in counts:
                out_lines.append("".join(marks[pos:pos + n]))
                pos += n
            vol_data[f"p{i:02d}"] = out_lines
        (OUT / f"{volume:03d}.json").write_text(
            json.dumps(vol_data, ensure_ascii=False), encoding="utf-8")
    print(f"strains data: {aligned}/{total} poems aligned "
          f"({aligned/total:.1%}), 900 volume files → docs/data/strains/")


if __name__ == "__main__":
    main()

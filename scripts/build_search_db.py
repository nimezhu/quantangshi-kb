"""P10 自索引搜索库：SQLite + FTS5（data/poems.db）。

- poems 表：全部 43,103 首的完整数据（修复后正文、来源、旗标、诗体、三百首标签）
- poems_fts（FTS5）：题目/作者/正文，**逐字空格分词 + 简体折叠**——中文无分词器时的
  标准做法；查询侧同样折叠+分字后按短语匹配，简繁输入均可命中，任意长度子串可查
- authors 表：诗人聚合（小传、统计）
API 服务器（server/api_server.py）启动时检测本库过期则自动重建（"自索引"）。
用法: python build_search_db.py
"""
import json
import sqlite3

from config import DATA_DIR, ANALYSIS_DIR, AUTHORS_MERGED
from lib_qts import iter_yuding, canonical_author, fold_t2s, poem_key

DB_PATH = DATA_DIR / "poems.db"


def spaced(text: str) -> str:
    """逐字空格分词 + 简体折叠（FTS 索引/查询共用的归一形）。"""
    return " ".join(fold_t2s(text))


def build(db_path=DB_PATH):
    forms = json.loads((ANALYSIS_DIR / "rhymes.json").read_text(encoding="utf-8"))["per_poem"]
    pop = json.loads((ANALYSIS_DIR / "popularity.json").read_text(encoding="utf-8"))
    t300 = pop["tang300"]
    merged = json.loads(AUTHORS_MERGED.read_text(encoding="utf-8"))

    tmp = db_path.with_suffix(".db.tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    cur = con.cursor()
    cur.executescript("""
    CREATE TABLE poems (
      key TEXT PRIMARY KEY, volume INTEGER, idx INTEGER, vol_name TEXT,
      title TEXT, author TEXT, author_canonical TEXT,
      paragraphs TEXT, form TEXT, tang300 TEXT,
      text_source TEXT, flags TEXT
    );
    CREATE VIRTUAL TABLE poems_fts USING fts5(
      key UNINDEXED, title_f, author_f, text_f, tokenize='unicode61'
    );
    CREATE TABLE authors (
      canonical TEXT PRIMARY KEY, display TEXT, biography TEXT, description TEXT,
      poem_count INTEGER, volumes TEXT
    );
    CREATE INDEX idx_poems_vol ON poems(volume, idx);
    CREATE INDEX idx_poems_author ON poems(author_canonical);
    """)

    n = 0
    for volume, poems in iter_yuding():
        rows, fts_rows = [], []
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            body = "\n".join(p.get("paragraphs", []))
            rows.append((
                key, volume, i, p.get("volume", f"卷{volume}"),
                p["title"], p["author"], canonical_author(p["author"]),
                json.dumps(p.get("paragraphs", []), ensure_ascii=False),
                forms.get(key, ["", ""])[0],
                json.dumps(t300.get(key), ensure_ascii=False) if key in t300 else None,
                p.get("text_source", "yuding"),
                json.dumps(p.get("flags", []), ensure_ascii=False),
            ))
            fts_rows.append((key, spaced(p["title"]), spaced(p["author"]), spaced(body)))
            n += 1
        cur.executemany("INSERT INTO poems VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        cur.executemany("INSERT INTO poems_fts VALUES (?,?,?,?)", fts_rows)

    cur.executemany(
        "INSERT INTO authors VALUES (?,?,?,?,?,?)",
        [(k, r["display"], r["biography"], r["desc"], r["poem_count_yuding"],
          json.dumps(r["volumes"]))
         for k, r in merged.items() if r["poem_count_yuding"] > 0])

    con.commit()
    cur.execute("INSERT INTO poems_fts(poems_fts) VALUES('optimize')")
    con.commit()
    con.close()
    tmp.replace(db_path)
    return n


if __name__ == "__main__":
    n = build()
    print(f"poems.db: {n} poems indexed, {DB_PATH.stat().st_size/1e6:.1f} MB")

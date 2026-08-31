"""全唐诗自索引 API 服务器（零第三方依赖，对标 shiji-kb wiki/server/serve.py 模式）。

- 静态站：继续服务 docs/（阅读器页面原样可用）
- API（JSON, UTF-8, CORS *）：
    GET /api/ping                      存活 + 库信息
    GET /api/poem/<key>                单诗全文（修复后正文、来源、旗标、prev/next）
    GET /api/volume/<n>                一卷目录
    GET /api/author/<名>               诗人信息 + 作品（?limit=）
    GET /api/search?q=…                搜索（&mode=meta|all|title|author|text，
                                       &limit= ≤100，&offset=；简繁均可）
    GET /api/stats                     总体统计
- 自索引：启动时若 data/poems.db 缺失或旧于语料（corpus_patch/rhymes/authors_merged），
  自动调用 build_search_db.build() 重建——后端自己维护自己的索引。

用法: python server/api_server.py [port]   （默认 8787）；或 ./api.sh [port]
"""
import json
import re
import sqlite3
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import DATA_DIR, DOCS_DIR, CORPUS_PATCH, ANALYSIS_DIR, AUTHORS_MERGED  # noqa: E402
from lib_qts import fold_t2s, strip_punct, canonical_author  # noqa: E402
import build_search_db  # noqa: E402

DB_PATH = DATA_DIR / "poems.db"
FTS_COLS = {"title": "title_f", "author": "author_f", "text": "text_f"}


def ensure_index():
    """自索引：库缺失或旧于语料输入则重建。"""
    inputs = [CORPUS_PATCH, ANALYSIS_DIR / "rhymes.json", AUTHORS_MERGED]
    newest = max(p.stat().st_mtime for p in inputs if p.exists())
    if not DB_PATH.exists() or DB_PATH.stat().st_mtime < newest:
        print("index stale/missing → rebuilding poems.db …")
        n = build_search_db.build()
        print(f"rebuilt: {n} poems")


def q2phrase(q: str) -> str:
    chars = [c for c in fold_t2s(strip_punct(q)) if not c.isspace() and c != '"']
    return '"' + " ".join(chars) + '"' if chars else ""


def snippet(paragraphs_json, q, width=14):
    text = "".join(json.loads(paragraphs_json))
    folded, fq = fold_t2s(text), fold_t2s(strip_punct(q))
    pos = folded.find(fq)
    if pos == -1:
        return None
    lo, hi = max(0, pos - width // 2), min(len(text), pos + len(fq) + width)
    return ("…" if lo else "") + text[lo:hi].replace("\n", " ") + ("…" if hi < len(text) else "")


def row_poem(r, full=False):
    d = {"key": r["key"], "volume": r["volume"], "title": r["title"],
         "author": r["author"], "canonical": r["author_canonical"],
         "form": r["form"]}
    if r["tang300"]:
        d["tang300_tags"] = json.loads(r["tang300"])
    if full:
        d.update(vol_name=r["vol_name"], author_canonical=r["author_canonical"],
                 paragraphs=json.loads(r["paragraphs"]),
                 text_source=r["text_source"], flags=json.loads(r["flags"]))
    return d


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 静默常规日志
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.path.startswith("/api/"):
            return super().do_GET()
        try:
            # http.server 以 iso-8859-1 解码 URL；裸 UTF-8 查询需还原
            try:
                path = self.path.encode("latin-1").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                path = self.path
            self.route(urlparse(path))
        except BrokenPipeError:
            pass
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 500)

    def route(self, u):
        db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        try:
            parts = [unquote(p) for p in u.path.split("/") if p][1:]  # 去掉 'api'
            qs = {k: v[0] for k, v in parse_qs(u.query).items()}

            if parts == ["ping"]:
                n = db.execute("SELECT COUNT(*) c FROM poems").fetchone()["c"]
                self._json({"ok": True, "poems": n, "db": DB_PATH.name})

            elif parts[0] == "poem" and len(parts) == 2:
                r = db.execute("SELECT * FROM poems WHERE key=?", (parts[1],)).fetchone()
                if not r:
                    return self._json({"error": "not found"}, 404)
                d = row_poem(r, full=True)
                for label, op in (("prev", "<"), ("next", ">")):
                    n = db.execute(
                        f"SELECT key FROM poems WHERE volume=? AND idx{op}? "
                        f"ORDER BY idx {'DESC' if op == '<' else 'ASC'} LIMIT 1",
                        (r["volume"], r["idx"])).fetchone()
                    if n:
                        d[label] = n["key"]
                self._json(d)

            elif parts[0] == "volume" and len(parts) == 2:
                rows = db.execute(
                    "SELECT * FROM poems WHERE volume=? ORDER BY idx",
                    (int(parts[1]),)).fetchall()
                if not rows:
                    return self._json({"error": "not found"}, 404)
                self._json({"volume": int(parts[1]), "vol_name": rows[0]["vol_name"],
                            "poems": [row_poem(r) for r in rows]})

            elif parts[0] == "author" and len(parts) == 2:
                canon = canonical_author(parts[1])
                a = db.execute("SELECT * FROM authors WHERE canonical=? OR display=?",
                               (canon, parts[1])).fetchone()
                if not a:
                    return self._json({"error": "not found"}, 404)
                limit = min(int(qs.get("limit", 100)), 1000)
                rows = db.execute(
                    "SELECT * FROM poems WHERE author_canonical=? ORDER BY volume, idx "
                    "LIMIT ?", (a["canonical"], limit)).fetchall()
                self._json({"canonical": a["canonical"], "display": a["display"],
                            "biography": a["biography"], "description": a["description"],
                            "poem_count": a["poem_count"],
                            "volumes": json.loads(a["volumes"]),
                            "poems": [row_poem(r) for r in rows]})

            elif parts == ["search"]:
                q = qs.get("q", "").strip()
                phrase = q2phrase(q)
                if not phrase:
                    return self._json({"error": "empty query"}, 400)
                mode = qs.get("mode", "meta")
                limit = min(int(qs.get("limit", 50)), 100)
                offset = int(qs.get("offset", 0))
                if mode in FTS_COLS:
                    match = f"{FTS_COLS[mode]}:{phrase}"
                elif mode == "meta":
                    match = f"{{title_f author_f}}:{phrase}"
                else:  # all
                    match = phrase
                total = db.execute(
                    "SELECT COUNT(*) c FROM poems_fts WHERE poems_fts MATCH ?",
                    (match,)).fetchone()["c"]
                rows = db.execute(
                    "SELECT p.* FROM poems_fts f JOIN poems p ON p.key=f.key "
                    "WHERE poems_fts MATCH ? "
                    "ORDER BY bm25(poems_fts, 0, 10.0, 5.0, 1.0) LIMIT ? OFFSET ?",
                    (match, limit, offset)).fetchall()
                hits = []
                for r in rows:
                    d = row_poem(r)
                    if mode in ("all", "text"):
                        d["snippet"] = snippet(r["paragraphs"], q)
                    hits.append(d)
                self._json({"query": q, "mode": mode, "total": total,
                            "offset": offset, "hits": hits})

            elif parts == ["stats"]:
                s = {"poems": db.execute("SELECT COUNT(*) c FROM poems").fetchone()["c"],
                     "authors": db.execute("SELECT COUNT(*) c FROM authors").fetchone()["c"],
                     "patched": db.execute(
                         "SELECT COUNT(*) c FROM poems WHERE text_source='poet.tang'"
                     ).fetchone()["c"],
                     "forms": dict(db.execute(
                         "SELECT form, COUNT(*) FROM poems WHERE form!='' "
                         "GROUP BY form ORDER BY 2 DESC").fetchall())}
                self._json(s)

            else:
                self._json({"error": "unknown endpoint"}, 404)
        finally:
            db.close()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    ensure_index()
    handler = partial(Handler, directory=str(DOCS_DIR))
    print(f"全唐诗 API + 静态站: http://localhost:{port}  (API 前缀 /api/)")
    ThreadingHTTPServer(("", port), handler).serve_forever()


if __name__ == "__main__":
    main()

"""P9 文本修复：御定全唐詩缺行修补（覆盖层方案）。

诊断结论（2026-08-31）：御定 JSON 上游抓取按刻本"隔列丢失"，长诗普遍缺约半数
诗句（如長恨歌 435-19 仅存一半）；poet.tang 是同书另一次完整抓取，经 P2 已对齐
96.2%。修复策略：**匹配诗的正文权威切换为 poet.tang**，御定保留卷结构/小传/题序。

安全闸（不过闸则保留御定原文并标记）：
- 仅当 poet.tang 文本更长（御定缺文）才替换；
- title/group 匹配：首句前5字（折叠+异体归一后）至少 3/5 相同；
- firstline 匹配：P2 构造时首5字已精确相等，直接过闸（单独记 patched_firstline）。

输出：data/corpus_patch.json（仅记录被修复/被标记的诗：新 paragraphs + 来源 + flags）
     + data/analysis/corpus_cleaning_report.md
下游：lib_qts.iter_yuding() 默认应用本覆盖层；分析与渲染自动生效。
用法: python build_clean_corpus.py
"""
import json
import re

from config import CORPUS_PATCH, ANALYSIS_DIR, POEM_ID_MAP
from lib_qts import (iter_yuding, iter_tang_shards, strip_punct, fold_t2s,
                     split_clauses, poem_key, VARIANT_CHARS)


def norm(s):
    return fold_t2s(s).translate(VARIANT_CHARS)


def head_agree(a, b, n=5, need=3):
    a, b = norm(strip_punct(a))[:n], norm(strip_punct(b))[:n]
    return sum(x == y for x, y in zip(a, b)) >= need


def text_agree(yd_paras, tg_paras):
    """内容认同兜底：御定首列亦可能丢失（正文起于中段），首句闸会误拒。
    取御定文首/中/尾三个 4 字样片，≥2 片按序出现在 tang 文中即认作同诗。"""
    y = norm(strip_punct("".join(yd_paras)))
    t = norm(strip_punct("".join(tg_paras)))
    if len(y) < 8:
        return False
    picks = [y[:4], y[len(y) // 2:len(y) // 2 + 4], y[-4:]]
    return sum(1 for c in picks if len(c) == 4 and c in t) >= 2


JUNK = re.compile(r"[A-Za-z][A-Za-z0-9]*|\d+")
CLEAN = re.compile(r"[A-Za-z0-9]")


def sanitize_latin(paragraphs, tang_text, stats):
    """御定罕用字（gaiji）被上游转成拉丁乱码（玉z1↔玉䪥、醴z0↔醴𨣧）。
    有 tang 对照时按前后文对齐找回真字；否则以单个 □ 占位。
    返回 (新 paragraphs, 是否改动)。折叠归一保持长度不变，故索引可直接映射。"""
    joined = "\n".join(paragraphs)
    if not JUNK.search(joined):
        return paragraphs, False
    folded_tang = norm(tang_text) if tang_text else ""
    cursor = 0
    changed = False
    result = []
    pos = 0
    for m in JUNK.finditer(joined):
        result.append(joined[pos:m.start()])
        repl = "□"
        if folded_tang:
            pre_raw = CLEAN.sub("", joined[max(0, m.start() - 6):m.start()])[-4:]
            post_raw = CLEAN.sub("", joined[m.end():m.end() + 6])[:4]
            pre = norm(pre_raw.replace("\n", ""))
            post = norm(post_raw.replace("\n", ""))
            if len(pre) >= 2 and len(post) >= 2:
                j = folded_tang.find(pre, cursor)
                if j >= 0:
                    k = folded_tang.find(post, j + len(pre))
                    if 0 < k - (j + len(pre)) <= 2:
                        repl = tang_text[j + len(pre):k]
                        cursor = k
        if repl == "□":
            stats["latin_boxed"] += 1
        else:
            stats["latin_recovered"] += 1
        result.append(repl)
        pos = m.end()
        changed = True
    result.append(joined[pos:])
    return "".join(result).split("\n"), changed


def fix_title(title, tang_title, stats):
    """题目乱码修复：以 tang 题目为对照做锚定正则找回（^前文(.{1,2})后文），
    能处理题首乱码；找不回的以 □ 占位。归一保持长度，索引可直接映射回原文。"""
    if not JUNK.search(title):
        return title, False
    changed = False
    if tang_title and not JUNK.search(tang_title):
        nt = norm(tang_title)
        m = JUNK.search(title)
        while m:
            pre = norm(title[:m.start()])
            post = norm(title[m.end():m.end() + 2])
            mt = re.match("^" + re.escape(pre) + "(.{1,2})" + re.escape(post), nt)
            if mt:
                rec = tang_title[mt.start(1):mt.end(1)]
                title = title[:m.start()] + rec + title[m.end():]
                stats["latin_recovered"] += 1
                changed = True
                m = JUNK.search(title, m.start() + len(rec))
            else:
                break
    if JUNK.search(title):
        title, n = JUNK.subn("□", title)
        stats["latin_boxed"] += n
        changed = True
    return title, changed


def text_flags(paragraphs):
    flags = []
    text = "".join(paragraphs)
    if "□" in text:
        flags.append("que_zi")
    if "——" in text:
        flags.append("lianju")
    clauses = split_clauses(paragraphs)
    lens = {len(c) for c in clauses}
    if len(lens) == 1 and lens & {5, 7} and len(clauses) % 2 == 1 and len(clauses) > 1:
        flags.append("odd_lines")
    return flags


def main():
    id_map = json.loads(POEM_ID_MAP.read_text(encoding="utf-8"))
    tang, tang_titles = {}, {}
    for shard, poems in iter_tang_shards():
        for idx, p in enumerate(poems):
            tang[(shard, idx)] = p.get("paragraphs", [])
            tang_titles[(shard, idx)] = p.get("title", "")

    patch = {}
    stats = {"patched": 0, "patched_firstline": 0, "tang_shorter_kept": 0,
             "mismatch_kept": 0, "equal": 0, "unmatched": 0, "flag_only": 0,
             "latin_recovered": 0, "latin_boxed": 0, "latin_poems": 0}
    chars_before = chars_after = 0
    worst_fixed = []

    for volume, poems in iter_yuding(raw=True):
        for i, p in enumerate(poems, start=1):
            key = poem_key(volume, i)
            yd_paras = p.get("paragraphs", [])
            yd_len = len(strip_punct("".join(yd_paras)))
            chars_before += yd_len
            m = id_map.get(key)
            entry = None

            tg_paras = []
            if m:
                for ref in m["refs"]:
                    tg_paras.extend(tang.get(tuple(ref), []))

            # 拉丁乱码修复（gaiji 找回/□ 占位）；替换 tang 文本的分支不需要
            yd_paras, san_changed = sanitize_latin(
                yd_paras, "".join(tg_paras), stats)
            if san_changed:
                stats["latin_poems"] += 1
            # 题目同样修复（tang 首部题目为对照，去组诗数字后缀）
            title_ref = ""
            if m:
                title_ref = re.sub(r"\s+[一二三四五六七八九十百]+$", "",
                                   tang_titles.get(tuple(m["refs"][0]), ""))
            new_title, title_changed = fix_title(p["title"], title_ref, stats)

            if m:
                tg_len = len(strip_punct("".join(tg_paras)))
                if tg_len > yd_len and tg_paras:
                    gate = (m["match"] == "firstline"
                            or head_agree("".join(yd_paras), "".join(tg_paras))
                            or text_agree(yd_paras, tg_paras))
                    if gate:
                        which = ("patched_firstline" if m["match"] == "firstline"
                                 else "patched")
                        stats[which] += 1
                        flags = text_flags(tg_paras) + [which]
                        entry = {"paragraphs": tg_paras,
                                 "text_source": "poet.tang", "flags": flags}
                        chars_after += tg_len
                        worst_fixed.append((tg_len - yd_len, key, p["title"],
                                            p["author"], yd_len, tg_len))
                    else:
                        stats["mismatch_kept"] += 1
                        entry = {"text_source": "yuding",
                                 "flags": text_flags(yd_paras) + ["mismatch_kept"]}
                        chars_after += yd_len
                elif tg_len < yd_len:
                    stats["tang_shorter_kept"] += 1
                    chars_after += yd_len
                else:
                    stats["equal"] += 1
                    chars_after += yd_len
            else:
                stats["unmatched"] += 1
                chars_after += yd_len
                flags = text_flags(yd_paras)
                if flags:
                    entry = {"text_source": "yuding", "flags": flags}
                    stats["flag_only"] += 1

            if entry is None:
                flags = text_flags(yd_paras)
                if flags or san_changed or title_changed:
                    entry = {"text_source": "yuding", "flags": flags}
                    stats["flag_only"] += 1
            if entry and entry["text_source"] == "yuding" and san_changed:
                entry["paragraphs"] = yd_paras
                entry["flags"] = entry.get("flags", []) + ["latin_fixed"]
            if entry and title_changed:
                entry["title"] = new_title
                entry["flags"] = entry.get("flags", []) + ["latin_title_fixed"]
            if entry:
                patch[key] = entry

    CORPUS_PATCH.write_text(json.dumps(patch, ensure_ascii=False), encoding="utf-8")

    worst_fixed.sort(reverse=True)
    n_patched = stats["patched"] + stats["patched_firstline"]
    lines = [
        "# P9 文本修复报告（御定缺行修补）", "",
        "## 诊断", "",
        "御定 JSON 上游按刻本**隔列丢失**（keep-3-drop-3 句式，長恨歌等长诗缺半），",
        "poet.tang 为同书完整抓取。修复：匹配诗正文权威切换为 poet.tang，御定保留结构与小传。", "",
        "## 修复统计", "",
        f"- 正文替换：**{n_patched}** 首（title/group 闸 {stats['patched']} + firstline {stats['patched_firstline']}）",
        f"- 御定较长保留：{stats['tang_shorter_kept']}；等长未动：{stats['equal']}",
        f"- 首句闸未过、保留待审：{stats['mismatch_kept']}（flag=mismatch_kept）",
        f"- 无匹配保留：{stats['unmatched']}",
        f"- 仅标记（□阙字/联句/奇数句）：{stats['flag_only']}",
        f"- 拉丁乱码修复：{stats['latin_poems']} 首 —— gaiji 真字找回 "
        f"**{stats['latin_recovered']}** 处（对照 poet.tang 前后文对齐）+ "
        f"□ 占位 {stats['latin_boxed']} 处（无对照可考）",
        f"- 全库正文字数：{chars_before:,} → **{chars_after:,}**"
        f"（+{chars_after-chars_before:,}，+{(chars_after-chars_before)/chars_before:.1%}）",
        "", "## 补回最多的 15 首", "",
        "| 诗 | 题目 | 作者 | 御定字数 | 修复后 |", "|---|---|---|---|---|"]
    for d, key, t, a, y, g in worst_fixed[:15]:
        lines.append(f"| {key} | {t[:20]} | {a} | {y} | {g} |")
    lines += ["", "## 残留问题", "",
              "- `mismatch_kept` 与 `odd_lines` 诗单可由 `corpus_patch.json` flags 过滤复审",
              "- 未匹配的 1,600 余首缺文无从考订，留待第三源（维基文库）仲裁",
              "- □ 阙字为底本固有，渲染时以样式标出；联句 `——作者` 渲染为作者标记"]
    (ANALYSIS_DIR / "corpus_cleaning_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print(f"corpus patch: {n_patched} patched, {stats['mismatch_kept']} kept-for-review, "
          f"{stats['flag_only']} flag-only; chars {chars_before:,} → {chars_after:,} "
          f"(+{(chars_after-chars_before)/chars_before:.1%})")


if __name__ == "__main__":
    main()

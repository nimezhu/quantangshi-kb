/**
 * 全唐诗搜索（Phase 3 + Phase 3d 渐进增强）。
 * 优先探测自索引后端（/api/ping，见 server/api_server.py）：可用则走 API
 * （SQLite FTS5，免下载索引）；不可用（如 GitHub Pages）则回退静态索引：
 * 一级索引（题目/作者）常驻；全文分片（fulltext_0..8.json）勾选后懒加载。
 * 简繁均可：查询词与索引条目均经 T2S_MAP 折叠成简体再比较（见 P7 报告）。
 * 依赖：t2s-map.js
 */
(function () {
    'use strict';

    var MAX_SHOW = 200;
    var apiMode = false;
    var primary = null;      // [[key,title,author,form], ...] + 预折叠简体
    var shards = {};         // g -> 条目数组（已折叠）

    function fold(s) {
        if (!window.T2S_MAP) return s;
        var out = '';
        for (var i = 0; i < s.length; i++) out += window.T2S_MAP[s[i]] || s[i];
        return out;
    }

    function poemHref(key) {
        return 'volumes/' + key.slice(0, 3) + '.html#p' + key.slice(4);
    }

    function el(id) { return document.getElementById(id); }

    function status(msg) { el('status').textContent = msg; }

    function render(hits, q) {
        var html = hits.slice(0, MAX_SHOW).map(function (h) {
            var badge = h[3] ? '<span class="badge badge-form">' + h[3] + '</span>' : '';
            var snippet = h[4] ? '<div class="search-snippet">' + h[4] + '</div>' : '';
            return '<div class="search-hit"><a class="para-num" href="' + poemHref(h[0]) + '">（' + h[0] + '）</a>' +
                '<a href="' + poemHref(h[0]) + '">' + h[1] + '</a>' + badge +
                '<span class="fp-author">' + h[2] + '</span>' + snippet + '</div>';
        }).join('');
        el('results').innerHTML = html;
        status(q ? '命中 ' + hits.length + ' 首' +
            (hits.length > MAX_SHOW ? '（仅显示前 ' + MAX_SHOW + '）' : '') : '');
    }

    function searchPrimary(qf) {
        var hits = [];
        for (var i = 0; i < primary.length; i++) {
            var e = primary[i];
            if (e[4].indexOf(qf) !== -1 || e[5].indexOf(qf) !== -1) {
                hits.push([e[0], e[1], e[2], e[3], '']);
            }
        }
        return hits;
    }

    function snippetAround(text, qf, folded) {
        var pos = folded.indexOf(qf);
        if (pos === -1) return null;
        var lo = Math.max(0, pos - 12), hi = Math.min(text.length, pos + qf.length + 12);
        return (lo > 0 ? '…' : '') + text.slice(lo, hi).replace(/\n/g, ' ') + (hi < text.length ? '…' : '');
    }

    function searchFulltext(qf, done) {
        var hits = [];
        var pending = 0;
        for (var g = 0; g < 9; g++) {
            (function (g) {
                function scan(entries) {
                    for (var i = 0; i < entries.length; i++) {
                        var e = entries[i];
                        var snip = snippetAround(e[2], qf, e[5]);
                        if (snip !== null || e[3].indexOf(qf) !== -1 || e[4].indexOf(qf) !== -1) {
                            hits.push([e[0], e[1], e[6], '', snip || '']);
                        }
                    }
                    if (--pending === 0) done(hits);
                }
                pending++;
                if (shards[g]) { setTimeout(function () { scan(shards[g]); }, 0); return; }
                fetch('data/fulltext_' + g + '.json').then(function (r) { return r.json(); })
                    .then(function (raw) {
                        // 折叠一次缓存：[key,title,text,titleF,authorF,textF,author]
                        shards[g] = raw.map(function (e) {
                            return [e[0], e[1], e[3], fold(e[1]), fold(e[2]), fold(e[3]), e[2]];
                        });
                        scan(shards[g]);
                    });
            })(g);
        }
    }

    function searchApi(q) {
        var mode = el('fulltext').checked ? 'all' : 'meta';
        fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=' + mode + '&limit=100')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (el('q').value.trim() !== q) return; // 过期响应丢弃
                render(d.hits.map(function (h) {
                    return [h.key, h.title, h.author, h.form || '', h.snippet || ''];
                }), q);
                status('命中 ' + d.total + ' 首' +
                    (d.total > d.hits.length ? '（显示前 ' + d.hits.length + '）' : '') +
                    ' · 后端索引');
            })
            .catch(function () { status('后端查询失败'); });
    }

    function run() {
        var q = el('q').value.trim();
        if (!q) { el('results').innerHTML = ''; status(''); return; }
        if (apiMode) { searchApi(q); return; }
        var qf = fold(q);
        if (el('fulltext').checked) {
            status('全文搜索中…');
            searchFulltext(qf, function (hits) { render(hits, q); });
        } else {
            render(searchPrimary(qf), q);
        }
    }

    var timer = null;
    function debounced() {
        clearTimeout(timer);
        timer = setTimeout(run, 200);
    }

    function loadStaticIndex(then) {
        status('加载索引…');
        fetch('data/search_index.json').then(function (r) { return r.json(); })
            .then(function (raw) {
                primary = raw.map(function (e) {
                    return [e[0], e[1], e[2], e[3], fold(e[1]), fold(e[2])];
                });
                status('');
                then();
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var boot = function () {
            var params = new URLSearchParams(location.search);
            if (params.get('q')) { el('q').value = params.get('q'); run(); }
        };
        fetch('/api/ping').then(function (r) { return r.json(); })
            .then(function (d) {
                if (d && d.ok) { apiMode = true; status(''); boot(); }
                else { loadStaticIndex(boot); }
            })
            .catch(function () { loadStaticIndex(boot); });
        el('q').addEventListener('input', debounced);
        el('fulltext').addEventListener('change', run);
    });
})();

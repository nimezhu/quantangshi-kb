/**
 * 单诗页（poem.html?id=VVV-PP[&author=规范名]）—— SPA 式无刷新切换。
 * - 默认按卷序翻页；带 author 参数时按**该诗人作品序**翻页（跨卷推进，
 *   如三百首成册的逐首阅读），序列取 data/authors/{规范名}.json。
 * - 数据：按卷烘焙的 data/volumes/NNN.json（含预渲染实体行），按卷缓存 +
 *   相邻预取；原地更新 DOM + pushState，无整页重载。
 * - ←/→ 方向键、浏览器前进后退、View Transitions 淡入淡出。
 * - 渲染后 QTS_REFRESH()：平仄/简繁/实体偏好即时生效。
 */
(function () {
    'use strict';

    var volCache = {};
    var current = null;            // {key, vol, pid, poem}
    var author = null;             // {key, display, seq} | null
    var prevKey = null, nextKey = null;

    function esc(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function fail(msg) {
        document.getElementById('content').innerHTML =
            '<div class="search-status">' + esc(msg) + '</div>';
    }

    function parseKey(k) {
        var m = /^(\d{3})-(\d{2,3})$/.exec(k || '');
        return m ? { key: m[0], vol: m[1], pid: 'p' + m[2] } : null;
    }

    function href(key) {
        return 'poem.html?id=' + key +
            (author ? '&author=' + encodeURIComponent(author.key) : '');
    }

    function getVolume(vol) {
        if (volCache[vol]) return Promise.resolve(volCache[vol]);
        return fetch('data/volumes/' + vol + '.json')
            .then(function (r) { return r.json(); })
            .then(function (d) { volCache[vol] = d; return d; });
    }

    function resolveNeighbors(ctx, p) {
        if (author) {
            var n = author.seq.indexOf(ctx.key);
            prevKey = n > 0 ? author.seq[n - 1] : null;
            nextKey = n >= 0 && n + 1 < author.seq.length ? author.seq[n + 1] : null;
        } else {
            prevKey = p.prev;
            nextKey = p.next;
        }
    }

    function navHtml(ctx) {
        var parts = [];
        if (prevKey) parts.push('<a href="' + href(prevKey) + '" data-poem="' + prevKey + '">← 上一首</a>');
        if (author) {
            parts.push('<a class="nav-home" href="authors/' +
                encodeURIComponent(author.key) + '.html">👤 ' + esc(author.display) + '</a>');
        }
        parts.push('<a href="volumes/' + ctx.vol + '.html#' + ctx.pid + '">📖 在卷中查看</a>');
        if (nextKey) parts.push('<a href="' + href(nextKey) + '" data-poem="' + nextKey + '">下一首 →</a>');
        return parts.join('\n');
    }

    function draw(ctx, d) {
        var p = d.poems[ctx.pid];
        if (!p) { fail('未找到 ' + ctx.key); return; }
        current = { key: ctx.key, vol: ctx.vol, pid: ctx.pid, poem: p };
        resolveNeighbors(ctx, p);
        document.title = p.title + ' - ' + p.author + ' - 全唐诗';

        var badges = '';
        if (p.form) badges += '<span class="badge badge-form">' + esc(p.form) + '</span>';
        if (p.t300) badges += '<span class="badge badge-300" title="' +
            esc(p.t300.slice(0, 3).join('、')) + '">三百首</span>';
        if (p.pilot) badges += '<span class="badge badge-pilot" ' +
            'title="实体经逐字精标（试点）">精標</span>';

        var seqInfo = '';
        if (author) {
            var n = author.seq.indexOf(ctx.key);
            if (n >= 0) seqInfo = ' · ' + esc(author.display) + ' 作品 第 ' +
                (n + 1) + '/' + author.seq.length + ' 首';
        }

        document.getElementById('content').innerHTML =
            '<h1 class="poem-title solo-title"><a class="para-num" href="#">（' + ctx.key + '）</a>' +
            esc(p.title) + badges + '</h1>' +
            '<div class="poem-author"><a href="authors/' +
            encodeURIComponent(p.canonical) + '.html">' + esc(p.author) + '</a>' +
            '<span class="solo-vol"> · ' + esc(d.vol_name) + seqInfo + '</span></div>' +
            '<div class="poem" id="' + ctx.pid + '"><div class="poem-body solo-body">' +
            p.lines.map(function (h) {
                return '<div class="line">' + h.replace(/href="\.\.\//g, 'href="') + '</div>';
            }).join('') + '</div></div>';

        var nav = navHtml(ctx);
        document.getElementById('nav-top').innerHTML =
            '<a class="nav-home" href="index.html">🏠 目录</a>' +
            '<a href="search.html">🔍 搜索</a>' + nav;
        document.getElementById('nav-bottom').innerHTML = nav;

        var tries = 0;
        (function refresh() {
            if (window.QTS_REFRESH) { window.QTS_REFRESH(); }
            else if (tries++ < 10) { setTimeout(refresh, 100); }
        })();

        // 预取相邻卷数据，跨卷翻页无等待
        [prevKey, nextKey].forEach(function (k) {
            var c = parseKey(k);
            if (c && !volCache[c.vol]) getVolume(c.vol);
        });
    }

    function show(key, push) {
        var ctx = parseKey(key);
        if (!ctx) { fail('无效的诗编号。用法：poem.html?id=165-19'); return; }
        getVolume(ctx.vol).then(function (d) {
            if (push) history.pushState({ id: ctx.key }, '', href(ctx.key));
            var render = function () { draw(ctx, d); };
            if (document.startViewTransition) document.startViewTransition(render);
            else render();
        }).catch(function () { fail('数据加载失败'); });
    }

    document.addEventListener('click', function (e) {
        var a = e.target.closest && e.target.closest('a[data-poem]');
        if (a && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
            e.preventDefault();
            show(a.dataset.poem, true);
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.target.tagName === 'INPUT' || !current) return;
        if (e.key === 'ArrowLeft' && prevKey) show(prevKey, true);
        else if (e.key === 'ArrowRight' && nextKey) show(nextKey, true);
    });

    window.addEventListener('popstate', function () {
        var q = new URLSearchParams(location.search);
        var id = q.get('id');
        if (id) show(id, false);
    });

    var q0 = new URLSearchParams(location.search);
    var id0 = q0.get('id');
    var author0 = q0.get('author');
    if (author0) {
        fetch('data/authors/' + encodeURIComponent(author0) + '.json')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                author = { key: author0, display: d.display, seq: d.poems };
                show(id0, false);
            })
            .catch(function () { show(id0, false); });
    } else {
        show(id0, false);
    }
})();

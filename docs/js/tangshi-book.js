/**
 * 三百首成册 SPA 翻页（docs/tang300/KEY.html）。
 * 服务端页面为入口/无 JS 回退；本脚本接管 上一首/下一首：按目录序
 * （data/tang300_order.json）原地更新 DOM + pushState 到真实页面路径，
 * 数据取按卷烘焙的 data/volumes/NNN.json（按卷缓存 + 相邻预取），无整页重载。
 * 支持 ←/→ 方向键、浏览器前进后退；渲染后 QTS_REFRESH 使偏好即时生效。
 */
(function () {
    'use strict';

    var order = null;      // 目录序 key 数组
    var volCache = {};
    var current = null;    // 当前目录下标

    function esc(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function keyFromPath() {
        var m = /\/tang300\/(\d{3}-\d{2,3})\.html$/.exec(location.pathname);
        return m ? m[1] : null;
    }

    function getVolume(vol) {
        if (volCache[vol]) return Promise.resolve(volCache[vol]);
        return fetch('../data/volumes/' + vol + '.json')
            .then(function (r) { return r.json(); })
            .then(function (d) { volCache[vol] = d; return d; });
    }

    function navHtml(n, key) {
        var vol = key.slice(0, 3), pid = 'p' + key.slice(4);
        var parts = [];
        if (n > 0) {
            parts.push('<a href="' + order[n - 1] + '.html" data-book="' +
                order[n - 1] + '">← 上一首</a>');
        }
        parts.push('<a class="nav-home" href="../tang300.html">📜 三百首目录</a>');
        parts.push('<a href="../volumes/' + vol + '.html#' + pid + '">📖 在卷中查看</a>');
        if (n + 1 < order.length) {
            parts.push('<a href="' + order[n + 1] + '.html" data-book="' +
                order[n + 1] + '">下一首 →</a>');
        }
        return parts.join('\n');
    }

    function draw(n, key, d) {
        current = n;
        var vol = key.slice(0, 3), pid = 'p' + key.slice(4);
        var p = d.poems[pid];
        if (!p) return;
        document.title = p.title + ' - ' + p.author + ' - 唐诗三百首';

        var badges = '';
        if (p.form) badges += '<span class="badge badge-form">' + esc(p.form) + '</span>';
        if (p.pilot) badges += '<span class="badge badge-pilot" ' +
            'title="实体经逐字精标（试点）">精標</span>';
        var tags = (p.t300 || []).slice(0, 3).join('、');

        document.getElementById('content').innerHTML =
            '<h1 class="poem-title solo-title"><a class="para-num" href="#">（' + key + '）</a>' +
            esc(p.title) + badges + '</h1>' +
            '<div class="poem-author"><a href="../authors/' +
            encodeURIComponent(p.canonical) + '.html">' + esc(p.author) + '</a>' +
            '<span class="solo-vol"> · ' + esc(d.vol_name) + ' · 三百首 第 ' +
            (n + 1) + '/' + order.length + ' 首' +
            (tags ? ' · ' + esc(tags) : '') + '</span></div>' +
            '<div class="poem" id="' + pid + '"><div class="poem-body solo-body">' +
            p.lines.map(function (h) {
                return '<div class="line">' + h + '</div>';
            }).join('') + '</div></div>';

        var nav = navHtml(n, key);
        document.getElementById('nav-top').innerHTML = nav;
        document.getElementById('nav-bottom').innerHTML = nav;

        var tries = 0;
        (function refresh() {
            if (window.QTS_REFRESH) { window.QTS_REFRESH(); }
            else if (tries++ < 10) { setTimeout(refresh, 100); }
        })();

        // 预取相邻卷数据
        [n - 1, n + 1].forEach(function (j) {
            if (j >= 0 && j < order.length) getVolume(order[j].slice(0, 3));
        });
    }

    function show(key, push) {
        var n = order.indexOf(key);
        if (n === -1) { location.href = key + '.html'; return; }
        getVolume(key.slice(0, 3)).then(function (d) {
            if (push) history.pushState({ k: key }, '', key + '.html');
            var render = function () { draw(n, key, d); };
            if (document.startViewTransition) document.startViewTransition(render);
            else render();
        }).catch(function () { location.href = key + '.html'; });
    }

    document.addEventListener('click', function (e) {
        var a = e.target.closest && e.target.closest('a[data-book]');
        if (a && order && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
            e.preventDefault();
            show(a.dataset.book, true);
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.target.tagName === 'INPUT' || current === null || !order) return;
        if (e.key === 'ArrowLeft' && current > 0) show(order[current - 1], true);
        else if (e.key === 'ArrowRight' && current + 1 < order.length) {
            show(order[current + 1], true);
        }
    });

    window.addEventListener('popstate', function () {
        var k = keyFromPath();
        if (k && order) show(k, false);
    });

    fetch('../data/tang300_order.json')
        .then(function (r) { return r.json(); })
        .then(function (o) {
            order = o;
            current = order.indexOf(keyFromPath());
            var k = keyFromPath();
            if (k) getVolume(k.slice(0, 3));   // 暖缓存，便于翻页
        });
})();

/**
 * 首页交互（Phase 3e，API 驱动 + 静态回退）。
 * - 今日一诗：按日期从三百首中确定一首，竖排无标点渲染（仿御定刻本版式）；
 *   API 在线时经 /api/poem 取权威数据，否则用构建时烘焙的 data/tang300_poems.json
 * - 换一首：随机再抽
 * - Hero 即时搜索：API 在线时输入即出下拉结果（/api/search mode=meta），
 *   回车进搜索页；无 API 时保持表单 GET 跳转，行为不变
 * 依赖：t2s-map.js（简繁折叠已由 settings 处理，此处无需）
 */
(function () {
    'use strict';

    var apiMode = false;
    var t300 = null;          // 烘焙的三百首全文
    var currentIdx = -1;

    function el(id) { return document.getElementById(id); }

    /* ---------- 今日一诗 ---------- */

    var MAX_COLS = 8;   // 竖排最多列数（含题目/落款各一列时正文 ≤8 行全显）

    function clauses(paragraphs) {
        var text = paragraphs.join('');
        return text.split(/[，。！？；：、\s]+/).filter(Boolean);
    }

    function esc(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function seasonChar(month) {
        if (month >= 3 && month <= 5) return '春';
        if (month >= 6 && month <= 8) return '夏';
        if (month >= 9 && month <= 11) return '秋';
        return '冬';
    }

    function renderDaily(p, dateLabel) {
        var card = el('daily-card');
        if (!card) return;
        var href = 'poem.html?id=' + p.key;
        var title = p.title.length > 8 ? p.title.slice(0, 8) + '…' : p.title;
        var all = clauses(p.paragraphs);
        // 整联截取：全诗 ≤8 行全显，否则取前 8 行（偶数，保联完整）并标「节选」
        var shown = all.length <= MAX_COLS ? all : all.slice(0, MAX_COLS);
        var partial = shown.length < all.length;
        var cols = shown.map(function (c) {
            return '<span class="dp-line">' + esc(c) + '</span>';
        }).join('');
        // 列高随内容：以最长列（题/句/落款+低起）定高，短诗紧凑、长句从容
        var maxLen = Math.max.apply(null, [title.length, p.author.length + 2]
            .concat(shown.map(function (c) { return c.length; })));
        var bodyH = Math.min(Math.max(maxLen * 20 + 16, 120), 320);
        var foot2 = [p.form ? esc(p.form) : null, partial ? '节选' : null]
            .filter(Boolean).join(' · ');
        card.innerHTML =
            '<div class="dp-head"><span class="dp-seal">今日<br>一詩</span>' +
            '<span class="dp-date">' + dateLabel + '</span></div>' +
            '<div class="dp-wrap">' +
            '<a class="dp-body" style="height:' + bodyH + 'px" href="' + href + '" title="读全诗">' +
            '<span class="dp-line dp-title">' + esc(title) + '</span>' +
            cols + '</a>' +
            '<a class="dp-body dp-colophon" style="height:' + bodyH + 'px" href="authors/' +
            encodeURIComponent(p.canonical || p.author) + '.html" title="诗人页">' +
            '<span class="dp-line dp-author">' + esc(p.author) + '</span></a>' +
            '</div>' +
            '<div class="dp-foot"><a href="' + href + '">读全诗（' + p.key + '）</a>' +
            (foot2 ? ' · ' + foot2 : '') +
            ' · <button type="button" id="dp-again">换一首</button></div>';
        el('dp-again').addEventListener('click', function () {
            showPoem(Math.floor(Math.random() * t300.length), '偶得一首');
        });
    }

    function showPoem(idx, label) {
        currentIdx = idx;
        renderDaily(t300[idx], label);
    }

    function initDaily() {
        fetch('data/tang300_poems.json')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                t300 = data;
                var now = new Date();
                var start = new Date(now.getFullYear(), 0, 0);
                var doy = Math.floor((now - start) / 86400000);
                // 应季优先：标签含当季字的诗构成候选池（如秋日选"秋"诗），按日确定
                var s = seasonChar(now.getMonth() + 1);
                var pool = [];
                for (var i = 0; i < t300.length; i++) {
                    var tg = (t300[i].tags || []).join('');
                    if (tg.indexOf(s) !== -1) pool.push(i);
                }
                var label = (now.getMonth() + 1) + '月' + now.getDate() + '日';
                if (pool.length >= 5) {
                    showPoem(pool[doy % pool.length], label + ' · 应' + s);
                } else {
                    showPoem(doy % t300.length, label);
                }
            })
            .catch(function () {
                var card = el('daily-card');
                if (card) card.innerHTML = '<div class="dp-foot">今日一诗暂不可用</div>';
            });
    }

    /* ---------- Hero 即时搜索 ---------- */

    function initLiveSearch() {
        var input = document.querySelector('.hero-search input');
        var box = el('live-results');
        if (!input || !box) return;
        var timer = null;

        function hide() { box.style.display = 'none'; box.innerHTML = ''; }

        function query() {
            var q = input.value.trim();
            if (!q) { hide(); return; }
            fetch('/api/search?q=' + encodeURIComponent(q) + '&mode=meta&limit=8')
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (input.value.trim() !== q) return;
                    if (!d.hits || !d.hits.length) { hide(); return; }
                    box.innerHTML = d.hits.map(function (h) {
                        var href = 'poem.html?id=' + h.key + '&author=' +
                            encodeURIComponent(h.canonical || h.author);
                        return '<a href="' + href + '"><b>' + esc(h.title) + '</b>' +
                            (h.form ? '<span class="badge badge-form">' + h.form + '</span>' : '') +
                            '<span class="fp-author">' + esc(h.author) + '</span></a>';
                    }).join('') +
                        '<a class="lr-more" href="search.html?q=' + encodeURIComponent(q) +
                        '">全部结果（' + d.total + '）→</a>';
                    box.style.display = 'block';
                })
                .catch(hide);
        }

        input.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(query, 180);
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') hide();
        });
        document.addEventListener('click', function (e) {
            if (!box.contains(e.target) && e.target !== input) hide();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        fetch('/api/ping')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (d && d.ok) { apiMode = true; initLiveSearch(); }
                initDaily();
            })
            .catch(initDaily);
    });
})();

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

    function clauses(paragraphs, cap) {
        var text = paragraphs.join('');
        var parts = text.split(/[，。！？；：、\s]+/).filter(Boolean);
        return parts.slice(0, cap || 6);
    }

    function esc(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function renderDaily(p, dateLabel) {
        var card = el('daily-card');
        if (!card) return;
        var href = 'volumes/' + p.key.slice(0, 3) + '.html#p' + p.key.slice(4);
        var title = p.title.length > 8 ? p.title.slice(0, 8) + '…' : p.title;
        var cols = clauses(p.paragraphs).map(function (c) {
            return '<span class="dp-line">' + esc(c) + '</span>';
        }).join('');
        card.innerHTML =
            '<div class="dp-head"><span class="dp-seal">今日<br>一詩</span>' +
            '<span class="dp-date">' + dateLabel + '</span></div>' +
            '<a class="dp-body" href="' + href + '" title="读全诗">' +
            '<span class="dp-line dp-title">' + esc(title) + '</span>' +
            cols +
            '<span class="dp-line dp-author">' + esc(p.author) + '</span>' +
            '</a>' +
            '<div class="dp-foot"><a href="' + href + '">读全诗（' + p.key + '）</a>' +
            ' · <button type="button" id="dp-again">换一首</button></div>';
        el('dp-again').addEventListener('click', function () {
            showPoem(Math.floor(Math.random() * t300.length), '偶得一首');
        });
    }

    function showPoem(idx, label) {
        currentIdx = idx;
        var baked = t300[idx];
        if (apiMode) {
            fetch('/api/poem/' + baked.key)
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    renderDaily({key: d.key, title: d.title, author: d.author,
                                 paragraphs: d.paragraphs}, label);
                })
                .catch(function () { renderDaily(baked, label); });
        } else {
            renderDaily(baked, label);
        }
    }

    function initDaily() {
        fetch('data/tang300_poems.json')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                t300 = data;
                var now = new Date();
                var start = new Date(now.getFullYear(), 0, 0);
                var doy = Math.floor((now - start) / 86400000);
                showPoem(doy % t300.length,
                         (now.getMonth() + 1) + '月' + now.getDate() + '日');
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
                        var href = 'volumes/' + h.key.slice(0, 3) + '.html#p' + h.key.slice(4);
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

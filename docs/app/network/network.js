/**
 * 诗人交游网络 —— 零依赖 canvas 力导向图（Phase 6）。
 * 数据：data.json（P4 管线聚合的诗人往来对）。
 * 交互：拖拽平移、滚轮缩放、悬停提示（含样例诗题）、点击进诗人页、搜索定位。
 */
(function () {
    'use strict';

    var canvas = document.getElementById('net');
    var ctx = canvas.getContext('2d');
    var tip = document.getElementById('tip');
    var DPR = window.devicePixelRatio || 1;

    var allNodes = [], allLinks = [];
    var nodes = [], links = [];
    var view = { x: 0, y: 0, k: 1 };
    var ticks = 0, MAX_TICKS = 260;
    var hoverNode = null, focusName = null;

    function resize() {
        var r = canvas.getBoundingClientRect();
        canvas.width = r.width * DPR;
        canvas.height = r.height * DPR;
    }

    function subset(showAll) {
        links = showAll ? allLinks : allLinks.filter(function (l) { return l.w >= 2; });
        var keep = {};
        links.forEach(function (l) { keep[l.s] = keep[l.t] = 1; });
        if (showAll) allNodes.forEach(function (n) { keep[n.id] = 1; });
        nodes = allNodes.filter(function (n) { return keep[n.id]; });
        var byId = {};
        nodes.forEach(function (n) { byId[n.id] = n; });
        links.forEach(function (l) { l.a = byId[l.s]; l.b = byId[l.t]; });
        // 初始位置：按度数从中心向外的螺旋
        var sorted = nodes.slice().sort(function (a, b) { return b.d - a.d; });
        sorted.forEach(function (n, i) {
            var ang = i * 2.399963, r = 14 * Math.sqrt(i + 1);
            n.x = r * Math.cos(ang); n.y = r * Math.sin(ang);
            n.vx = 0; n.vy = 0;
            n.r = 3 + Math.sqrt(n.d) * 1.6;
        });
        ticks = 0;
        document.getElementById('stats').textContent =
            nodes.length + ' 位诗人 · ' + links.length + ' 组往来';
    }

    function step() {
        var i, j, a, b, dx, dy, d2, f;
        // 斥力（网格分桶近似）
        var CELL = 60, grid = {};
        for (i = 0; i < nodes.length; i++) {
            a = nodes[i];
            var key = Math.floor(a.x / CELL) + ',' + Math.floor(a.y / CELL);
            (grid[key] = grid[key] || []).push(a);
        }
        for (i = 0; i < nodes.length; i++) {
            a = nodes[i];
            var cx = Math.floor(a.x / CELL), cy = Math.floor(a.y / CELL);
            for (var gx = cx - 1; gx <= cx + 1; gx++) {
                for (var gy = cy - 1; gy <= cy + 1; gy++) {
                    var cell = grid[gx + ',' + gy];
                    if (!cell) continue;
                    for (j = 0; j < cell.length; j++) {
                        b = cell[j];
                        if (a === b) continue;
                        dx = a.x - b.x; dy = a.y - b.y;
                        d2 = dx * dx + dy * dy + 0.01;
                        if (d2 > 3600) continue;
                        f = 420 / d2;
                        a.vx += dx * f; a.vy += dy * f;
                    }
                }
            }
        }
        // 弹簧引力
        for (i = 0; i < links.length; i++) {
            var l = links[i];
            dx = l.b.x - l.a.x; dy = l.b.y - l.a.y;
            var dist = Math.sqrt(dx * dx + dy * dy) + 0.01;
            f = (dist - 46) * 0.012 * Math.min(l.w, 6);
            dx /= dist; dy /= dist;
            l.a.vx += dx * f; l.a.vy += dy * f;
            l.b.vx -= dx * f; l.b.vy -= dy * f;
        }
        // 向心 + 阻尼
        for (i = 0; i < nodes.length; i++) {
            a = nodes[i];
            a.vx -= a.x * 0.004; a.vy -= a.y * 0.004;
            a.x += a.vx * 0.5; a.y += a.vy * 0.5;
            a.vx *= 0.6; a.vy *= 0.6;
        }
    }

    function draw() {
        var w = canvas.width, h = canvas.height;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, w, h);
        ctx.setTransform(DPR * view.k, 0, 0, DPR * view.k,
                         w / 2 + view.x * DPR, h / 2 + view.y * DPR);
        var i;
        ctx.lineWidth = 0.7 / view.k;
        for (i = 0; i < links.length; i++) {
            var l = links[i];
            var hot = hoverNode && (l.a === hoverNode || l.b === hoverNode);
            ctx.strokeStyle = hot ? 'rgba(139,0,0,0.55)'
                : 'rgba(160,130,70,' + Math.min(0.12 + l.w * 0.05, 0.5) + ')';
            ctx.lineWidth = (hot ? 1.6 : 0.5 + Math.min(l.w, 8) * 0.25) / view.k;
            ctx.beginPath();
            ctx.moveTo(l.a.x, l.a.y);
            ctx.lineTo(l.b.x, l.b.y);
            ctx.stroke();
        }
        for (i = 0; i < nodes.length; i++) {
            var n = nodes[i];
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.r, 0, 6.2832);
            ctx.fillStyle = n.n300 ? '#a5453b' : '#c9a55a';
            if (n === hoverNode || n.id === focusName) ctx.fillStyle = '#8B0000';
            ctx.fill();
            if (n.d >= 10 || view.k > 1.6 || n === hoverNode || n.id === focusName) {
                ctx.fillStyle = '#5a4632';
                ctx.font = (11 / view.k) + 'px "Noto Serif TC", serif';
                ctx.fillText(n.id, n.x + n.r + 2 / view.k, n.y + 4 / view.k);
            }
        }
    }

    function loop() {
        if (ticks < MAX_TICKS) { step(); step(); ticks += 2; }
        draw();
        requestAnimationFrame(loop);
    }

    function toWorld(px, py) {
        var r = canvas.getBoundingClientRect();
        return {
            x: ((px - r.left) - r.width / 2 - view.x) / view.k,
            y: ((py - r.top) - r.height / 2 - view.y) / view.k
        };
    }

    function pick(px, py) {
        var p = toWorld(px, py);
        for (var i = nodes.length - 1; i >= 0; i--) {
            var n = nodes[i], dx = p.x - n.x, dy = p.y - n.y;
            if (dx * dx + dy * dy < (n.r + 3) * (n.r + 3)) return n;
        }
        return null;
    }

    var drag = null;
    canvas.addEventListener('mousedown', function (e) {
        drag = { x: e.clientX, y: e.clientY };
        canvas.classList.add('dragging');
    });
    window.addEventListener('mousemove', function (e) {
        if (drag) {
            view.x += e.clientX - drag.x;
            view.y += e.clientY - drag.y;
            drag = { x: e.clientX, y: e.clientY };
            return;
        }
        var n = pick(e.clientX, e.clientY);
        hoverNode = n;
        if (n) {
            var wrap = document.getElementById('wrap').getBoundingClientRect();
            tip.style.display = 'block';
            tip.style.left = (e.clientX - wrap.left + 14) + 'px';
            tip.style.top = (e.clientY - wrap.top + 10) + 'px';
            var best = null;
            links.forEach(function (l) {
                if ((l.a === n || l.b === n) && (!best || l.w > best.w)) best = l;
            });
            tip.innerHTML = '<b>' + n.id + '</b> · 往来 ' + n.d + ' 次 · 存诗 ' +
                n.poems + (n.n300 ? ' · 三百首×' + n.n300 : '') +
                (best ? '<div class="eg">如 ' + best.eg + '</div>' : '');
        } else {
            tip.style.display = 'none';
        }
    });
    window.addEventListener('mouseup', function (e) {
        canvas.classList.remove('dragging');
        if (drag && Math.abs(drag.x - e.clientX) < 3 && Math.abs(drag.y - e.clientY) < 3) {
            var n = pick(e.clientX, e.clientY);
            if (n && n.page) {
                location.href = '../../authors/' + encodeURIComponent(n.id) + '.html';
            }
        }
        drag = null;
    });
    canvas.addEventListener('wheel', function (e) {
        e.preventDefault();
        var k = Math.max(0.25, Math.min(6, view.k * (e.deltaY < 0 ? 1.15 : 0.87)));
        view.k = k;
    }, { passive: false });

    document.getElementById('q').addEventListener('input', function () {
        var q = this.value.trim();
        focusName = null;
        if (!q) return;
        var n = nodes.find(function (x) { return x.id.indexOf(q) !== -1; });
        if (n) {
            focusName = n.id;
            view.x = -n.x * view.k;
            view.y = -n.y * view.k;
        }
    });
    document.getElementById('showall').addEventListener('change', function () {
        subset(this.checked);
    });
    window.addEventListener('resize', resize);

    fetch('data.json').then(function (r) { return r.json(); }).then(function (d) {
        allNodes = d.nodes;
        allLinks = d.links;
        resize();
        subset(false);
        loop();
    });
})();

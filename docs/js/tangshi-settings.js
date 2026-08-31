/**
 * 全唐诗阅读器 - 设置面板（简化自 shiji-kb settings-panel-config.js）
 * 功能：繁→简 切换（逐字 t2s，见 P7 质检结论）、字号调节。偏好存 localStorage。
 * 依赖：t2s-map.js（构建时由 opencc 生成的 window.T2S_MAP 字表）
 */
(function () {
    'use strict';

    var LS_SIMP = 'qts-simplified';
    var LS_FONT = 'qts-font-scale';
    var originals = new Map();   // Text node -> 原繁体文本

    function convertT2S(enable) {
        if (typeof window.T2S_MAP === 'undefined') return;
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var node;
        while ((node = walker.nextNode())) {
            if (enable) {
                var text = node.nodeValue, out = '', changed = false;
                for (var i = 0; i < text.length; i++) {
                    var s = window.T2S_MAP[text[i]];
                    if (s) { out += s; changed = true; } else { out += text[i]; }
                }
                if (changed) {
                    if (!originals.has(node)) originals.set(node, text);
                    node.nodeValue = out;
                }
            } else if (originals.has(node)) {
                node.nodeValue = originals.get(node);
            }
        }
    }

    function applyFont(scale) {
        document.documentElement.style.setProperty('--font-scale', scale);
    }

    function save(key, val) {
        try { localStorage.setItem(key, val); } catch (e) { /* 隐私模式忽略 */ }
    }
    function load(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var simplified = load(LS_SIMP) === '1';
        var fontScale = load(LS_FONT) || '1';
        applyFont(fontScale);
        if (simplified) convertT2S(true);

        var gear = document.createElement('button');
        gear.className = 'settings-toggle';
        gear.title = '设置';
        gear.textContent = '⚙';

        var panel = document.createElement('div');
        panel.className = 'settings-panel';
        panel.innerHTML =
            '<div class="row">字体：<button data-simp="0">繁體</button> ' +
            '<button data-simp="1">简体</button></div>' +
            '<div class="row">字号：<button data-font="0.9">小</button> ' +
            '<button data-font="1">中</button> <button data-font="1.15">大</button></div>';

        function refresh() {
            panel.querySelectorAll('[data-simp]').forEach(function (b) {
                b.classList.toggle('active', (b.dataset.simp === '1') === simplified);
            });
            panel.querySelectorAll('[data-font]').forEach(function (b) {
                b.classList.toggle('active', b.dataset.font === fontScale);
            });
        }

        gear.addEventListener('click', function () {
            panel.classList.toggle('open');
        });
        panel.addEventListener('click', function (e) {
            var b = e.target;
            if (b.dataset.simp !== undefined) {
                simplified = b.dataset.simp === '1';
                convertT2S(simplified);
                save(LS_SIMP, simplified ? '1' : '0');
            } else if (b.dataset.font !== undefined) {
                fontScale = b.dataset.font;
                applyFont(fontScale);
                save(LS_FONT, fontScale);
            }
            refresh();
        });

        refresh();
        document.body.appendChild(gear);
        document.body.appendChild(panel);
    });
})();

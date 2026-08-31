/**
 * 全唐诗阅读器 - 设置面板（简化自 shiji-kb settings-panel-config.js）
 * 功能：繁→简 切换（逐字 t2s，见 P7 质检结论）、字号调节。偏好存 localStorage。
 * 依赖：t2s-map.js（构建时由 opencc 生成的 window.T2S_MAP 字表）
 */
(function () {
    'use strict';

    var LS_SIMP = 'qts-simplified';
    var LS_FONT = 'qts-font-scale';
    var LS_ENT = 'qts-ent';        // 实体高亮（默认开）
    var LS_STRAIN = 'qts-strains'; // 平仄显示（默认关，仅卷页）
    var originals = new Map();   // Text node -> 原繁体文本
    var strainData = null;       // 本卷平仄数据缓存
    var isVolumePage = /\/volumes\/\d{3}\.html/.test(location.pathname);

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

    function applyEnt(on) {
        document.body.classList.toggle('no-ent', !on);
    }

    function removeStrains() {
        document.querySelectorAll('.strain-marks').forEach(function (n) { n.remove(); });
    }

    function applyStrains(on) {
        if (!isVolumePage) return;
        if (!on) { removeStrains(); return; }
        var vol = location.pathname.match(/(\d{3})\.html/)[1];
        var draw = function () {
            removeStrains();
            Object.keys(strainData).forEach(function (pid) {
                var poem = document.getElementById(pid);
                if (!poem) return;
                var lines = poem.querySelectorAll('.poem-body .line');
                strainData[pid].forEach(function (marks, i) {
                    if (!marks || !lines[i]) return;
                    var sp = document.createElement('span');
                    sp.className = 'strain-marks';
                    // 偶数行末字为韵脚位，标红
                    if ((i + 1) % 2 === 0 && marks.length) {
                        sp.innerHTML = marks.slice(0, -1) +
                            '<b class="rhyme-mark">' + marks.slice(-1) + '</b>';
                    } else {
                        sp.textContent = marks;
                    }
                    lines[i].appendChild(sp);
                });
            });
        };
        if (strainData) { draw(); return; }
        fetch('../data/strains/' + vol + '.json')
            .then(function (r) { return r.json(); })
            .then(function (d) { strainData = d; draw(); })
            .catch(function () { strainData = {}; });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var simplified = load(LS_SIMP) === '1';
        var fontScale = load(LS_FONT) || '1';
        var entOn = load(LS_ENT) !== '0';
        var strainOn = load(LS_STRAIN) === '1';
        applyFont(fontScale);
        applyEnt(entOn);
        if (simplified) convertT2S(true);
        if (strainOn) applyStrains(true);

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
            '<button data-font="1">中</button> <button data-font="1.15">大</button></div>' +
            '<div class="row">实体：<button data-ent="1">高亮</button> ' +
            '<button data-ent="0">隐藏</button></div>' +
            (isVolumePage
                ? '<div class="row">平仄：<button data-strain="1">显示</button> ' +
                  '<button data-strain="0">隐藏</button></div>'
                : '');

        function refresh() {
            panel.querySelectorAll('[data-simp]').forEach(function (b) {
                b.classList.toggle('active', (b.dataset.simp === '1') === simplified);
            });
            panel.querySelectorAll('[data-font]').forEach(function (b) {
                b.classList.toggle('active', b.dataset.font === fontScale);
            });
            panel.querySelectorAll('[data-ent]').forEach(function (b) {
                b.classList.toggle('active', (b.dataset.ent === '1') === entOn);
            });
            panel.querySelectorAll('[data-strain]').forEach(function (b) {
                b.classList.toggle('active', (b.dataset.strain === '1') === strainOn);
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
            } else if (b.dataset.ent !== undefined) {
                entOn = b.dataset.ent === '1';
                applyEnt(entOn);
                save(LS_ENT, entOn ? '1' : '0');
            } else if (b.dataset.strain !== undefined) {
                strainOn = b.dataset.strain === '1';
                applyStrains(strainOn);
                save(LS_STRAIN, strainOn ? '1' : '0');
            }
            refresh();
        });

        refresh();
        document.body.appendChild(gear);
        document.body.appendChild(panel);
    });
})();

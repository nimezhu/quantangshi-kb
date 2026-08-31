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

    // 诗文语境识别：卷页 / 单诗页 / 三百首成册页 —— 三者均支持平仄逐字标注
    var poemCtx = (function () {
        var m = /\/volumes\/(\d{3})\.html/.exec(location.pathname);
        if (m) return { vol: m[1], prefix: '../' };
        m = /\/tang300\/(\d{3})-\d{2,3}\.html/.exec(location.pathname);
        if (m) return { vol: m[1], prefix: '../' };
        if (/\/poem\.html$/.test(location.pathname)) {
            m = /^(\d{3})-\d{2,3}$/.exec(
                new URLSearchParams(location.search).get('id') || '');
            if (m) return { vol: m[1], prefix: '' };
        }
        return null;
    })();
    var isVolumePage = !!poemCtx;

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

    /* ---- 平仄逐字对位（ruby 注于字下）---- */

    var CJK = /[㐀-䶿一-鿿豈-﫿]/;

    function cacheLines() {
        // 载入时缓存服务端原始（繁体）行 HTML，作为一切重建的基准
        document.querySelectorAll('.poem-body .line').forEach(function (l) {
            if (l.dataset.so === undefined) l.dataset.so = l.innerHTML;
        });
    }

    function restoreLines() {
        document.querySelectorAll('.poem-body .line').forEach(function (l) {
            if (l.dataset.so !== undefined) l.innerHTML = l.dataset.so;
        });
    }

    function rubyLine(line, marks, isEven) {
        var mi = 0;
        function walk(node) {
            if (node.nodeType === 3) {
                var frag = document.createDocumentFragment();
                var text = node.nodeValue;
                for (var c = 0; c < text.length; c++) {
                    var ch = text[c];
                    if (CJK.test(ch) && mi < marks.length) {
                        var r = document.createElement('ruby');
                        r.appendChild(document.createTextNode(ch));
                        var rt = document.createElement('rt');
                        rt.textContent = marks[mi];
                        rt.className = 'strain-rt' +
                            (isEven && mi === marks.length - 1 ? ' rhyme-rt' : '');
                        r.appendChild(rt);
                        frag.appendChild(r);
                        mi++;
                    } else {
                        frag.appendChild(document.createTextNode(ch));
                    }
                }
                node.parentNode.replaceChild(frag, node);
            } else if (node.nodeType === 1 && node.tagName !== 'RT') {
                Array.prototype.slice.call(node.childNodes).forEach(walk);
            }
        }
        Array.prototype.slice.call(line.childNodes).forEach(walk);
    }

    function decorateStrains() {
        Object.keys(strainData).forEach(function (pid) {
            var poem = document.getElementById(pid);
            if (!poem) return;
            var lines = poem.querySelectorAll('.poem-body .line');
            strainData[pid].forEach(function (marks, i) {
                // 渲染行为整联（上句，下句。），行末即韵脚位
                if (marks && lines[i]) rubyLine(lines[i], marks, true);
            });
        });
    }

    function rebuildLines(strainOn, simplified) {
        // 统一重建：原始繁体 → （可选）逐字 ruby → （可选）简体折叠
        restoreLines();
        document.body.classList.toggle('strains-on', !!strainOn);
        if (strainOn && strainData) decorateStrains();
        if (simplified) convertT2S(true);
    }

    function applyStrains(on, simplified) {
        if (!isVolumePage) return;
        if (!on || strainData) {
            rebuildLines(on, simplified);
            return;
        }
        fetch(poemCtx.prefix + 'data/strains/' + poemCtx.vol + '.json')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                strainData = d;
                rebuildLines(true, simplified);
            })
            .catch(function () { strainData = {}; });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var simplified = load(LS_SIMP) === '1';
        var fontScale = load(LS_FONT) || '1';
        var entOn = load(LS_ENT) !== '0';
        var strainOn = load(LS_STRAIN) === '1';
        if (isVolumePage) cacheLines();
        applyFont(fontScale);
        applyEnt(entOn);
        if (simplified) convertT2S(true);
        if (strainOn && isVolumePage) applyStrains(true, simplified);

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
                if (isVolumePage) {
                    // 诗行统一从原始繁体重建（叠加平仄 ruby），避免转换缓存失效
                    convertT2S(false);
                    rebuildLines(strainOn, simplified);
                } else {
                    convertT2S(simplified);
                }
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
                applyStrains(strainOn, simplified);
                save(LS_STRAIN, strainOn ? '1' : '0');
            }
            refresh();
        });

        refresh();
        document.body.appendChild(gear);
        document.body.appendChild(panel);

        // 供动态注入内容的页面（单诗页/成册页 SPA）在渲染后按已存偏好重新装饰。
        // SPA 跨卷翻页时同步平仄数据的卷号（换卷即失效重取）。
        window.QTS_REFRESH = function () {
            if (poemCtx) {
                var vol = null;
                var m = /\/tang300\/(\d{3})-\d{2,3}\.html$/.exec(location.pathname);
                if (m) vol = m[1];
                else if (/\/poem\.html$/.test(location.pathname)) {
                    m = /^(\d{3})-\d{2,3}$/.exec(
                        new URLSearchParams(location.search).get('id') || '');
                    if (m) vol = m[1];
                }
                if (vol && vol !== poemCtx.vol) {
                    poemCtx.vol = vol;
                    strainData = null;
                }
            }
            cacheLines();
            if (strainOn && isVolumePage) applyStrains(true, simplified);
            else if (simplified) convertT2S(true);
        };
    });
})();

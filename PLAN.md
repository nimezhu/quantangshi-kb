# 全唐诗浏览器（quantangshi-kb）建设计划

> **TL;DR (English)**: Build a static-site browser for the Complete Tang Poems (全唐诗), modeled on the shiji-kb reader. Content comes from `../chinese-poetry/御定全唐詩/` (900 卷, backbone) enriched by `../chinese-poetry/全唐诗/` (ids, 平仄, popularity, 三百首 tags). Pipeline mirrors shiji-kb: Python render scripts → `docs/` static HTML → GitHub Pages / local `serve.sh`. **Analysis pipelines borrowed from shiji-kb run first** (author disambiguation, word frequency, title-based social network, rhyme/meter stats) — their outputs feed the browser. Then: MVP volume reader → author & search → enrichment display → entity annotation & highlighting.

**日期**: 2026-08-31
**位置**: `Zhu-2026-ShiCi/quantangshi-kb/`（与 `chinese-poetry/`、`shiji-kb/` 平级）
**原则**: 上游数据只读（`chinese-poetry/` 不做任何修改），派生数据与代码全部放在本目录。

---

## 1. 目标

做一个像 **史记阅读器**（shiji-kb）一样的《全唐诗》浏览器：

- 按 **卷** 浏览（对应史记的"章"），卷内每首诗可精确引用与分享（Purple Numbers）
- 上一卷/下一卷/回目录导航，风格与 shiji-kb 阅读器一致
- 诗人页（小传 + 作品列表）、唐诗三百首精选入口
- 搜索（题目/作者优先，全文其次）
- 设置面板：简繁切换、字号、（后期）高亮开关
- 后期：实体标注与语法高亮（人名/地名/典故），以及唐诗特有的 **平仄着色**

**非目标（暂不做）**：宋诗（poet.song）、wiki 体系、知识图谱推理。架构上留扩展余地即可。

---

## 2. 内容源分析

两个候选数据集都在 `../chinese-poetry/` 中（均为繁体）：

### 2.1 主干：`御定全唐詩/json/001.json … 900.json` ✅（选定）

- **900 卷**，每卷一个 JSON 数组（如卷 1 有 88 首），完美对应 shiji-kb 的"130 章"模型
- 每首字段：`{title, author, biography, paragraphs, notes, volume, "no#"}`
  - `biography`：作者小传（同卷同作者重复出现，渲染时去重、提升到卷首/作者区块）
  - `notes`：校注；`no#` 是**字面量键名**（含 `#`），解析时注意
  - 组诗保持完整（如"帝京篇十首"是一条，多段 paragraphs）
- 缺点：无唯一 id、无 tags，与 strains/rank 数据不直接对齐
- **⚠️ 数据质量（2026-08-31 发现）**：上游抓取隔列丢失，约 1/4 诗缺文（长诗最重）。
  已由 P9 管线用 poet.tang 文本修补（见 Phase 3c）；**正文权威 = poet.tang，结构权威 = 御定**

### 2.2 增强层：`全唐诗/`（poet.tang 系列）

- `poet.tang.{0..57000}.json`：57 个分片 × 1000 首，每首 `{author, paragraphs, title, id}`（UUID）；组诗被拆成单首（"帝京篇十首 一"）
- `authors.tang.json`：3,675 位诗人 `{name, desc, id}`
- `唐诗三百首.json`：366 首，带 `tags`（用于精选页与标签）
- `strains/json/poet.tang.*.json`：**平仄**数据，与 poet.tang 分片**按文件名和数组下标一一对齐**
- `rank/poet/poet.tang.rank.*.json`：搜索引擎热度（baidu/bing/so360/google 命中数），同样按下标对齐

### 2.3 两源匹配策略

御定（整首）↔ poet.tang（拆分单首）通过 `(author 别名归一, title 前缀, 首句)` 匹配，生成一次性映射表 `data/poem_id_map.json`。匹配不上的不强求（热度/平仄增强是可选装饰，缺失不影响阅读）。作者名差异（如御定"李世民" vs poet.tang"太宗皇帝"）需要一张人工核对的别名表 `data/author_aliases.json`。

---

## 3. 向 shiji-kb 借鉴什么

### 3.1 直接复用/改造的资产（从 `../shiji-kb/` 拷贝后改名适配）

| shiji-kb 资产 | 用途 | 改造 |
|---|---|---|
| `docs/css/shiji-styles-v6.css` | 阅读器主样式 → `docs/css/tangshi-styles.css` | 删掉 22 类实体色板（后期再加），保留版式/导航/段号样式 |
| `docs/css/chapter-nav.css` | 上/下卷导航条 | 基本原样 |
| `docs/js/purple-numbers.js` | 段落锚点、点击复制引用链接 | 编号格式改为 `（VVV-PP）`卷-诗号 |
| `docs/js/settings-panel-config.js` | 右上角齿轮设置面板 | 项目改为：简繁、字号、（后期）高亮开关 |
| `docs/js/simp-trad-converter.js` | 前端简繁切换 | 原样（数据是繁体，默认繁体、可切简体） |
| `docs/js/search.js` + `docs/search.html` | 搜索页 | 索引结构见 §6 Phase 2 |
| `docs/js/report-issue-button.js` | 报错按钮 | 指向本项目 issue 地址（暂可去掉） |
| `serve.sh` | 本地预览 | 原样（`python3 -m http.server` in `docs/`） |
| `render_shiji_html.py` 的结构 | 渲染器**参考**（不是拷贝）：页面骨架、prev/next 推断、index 生成 | 输入从 tagged.md 换成 JSON |
| `scripts/config.py` 模式 | 集中路径常量 | 新写 |

### 3.2 借鉴的设计模式

- **数据 → 渲染脚本 → `docs/` 静态站**，无后端、无构建框架，GitHub Pages 直接发布
- **Purple Numbers**：每首诗有稳定编号 `（001-01）`（卷 1 第 1 首），锚点 + 一键复制引用
- **单章（卷）一页** + 首页目录网格 + 面包屑/上下卷导航
- **派生物不手改**：`docs/` 下 HTML 全部由脚本再生，改样式改脚本后重跑 `generate_all_volumes.py`
- **lint 门禁**：渲染后校验（链接完整性、编号连续性、HTML 合法性），对应 shiji 的 `lint_html.py`
- **skills 文档化**（远期）：标注规范若启动，写成 SKILL 文档驱动 agent 批量执行

### 3.3 借鉴的分析管线（先行实施 ⭐）

**思路**：先跑分析、后建浏览器。shiji-kb 的经验是——阅读器的价值来自底层结构化数据（索引、消歧、统计），而不是页面本身。以下管线在唐诗数据上**不需要 NER 标注就能先跑**（标题、作者、strains 等已是结构化字段），产出直接喂给后续的浏览器页面。

| # | 新管线 | 借鉴的 shiji-kb 资产 | 输入 | 输出 → 用在哪 |
|---|---|---|---|---|
| P1 | **作者别名归一与消歧** | `scripts/build_alias_index.py` 模式 + `skills/SKILL_03b_人名消歧.md`、`SKILL_03j_人名分类.md` 方法论 | 御定卷内作者名 × `authors.tang.json` | `data/author_aliases.json`、`data/authors_merged.json` → 诗人页、两源匹配的前提 |
| P2 | **御定 ↔ poet.tang 对齐** | `build_complete_pn_mapping.py` 的"建映射表"模式 | 双源 (作者归一, 题目前缀, 首句) | `data/poem_id_map.json` → 挂 strains/rank/三百首 |
| P3 | **字/词频与意象统计** | `analyze_word_frequency.py`（jieba 已在 shiji 依赖里） | 全部 paragraphs | `data/analysis/word_freq.json`、意象词表（月/酒/花/柳/山/水…）→ 首页统计图（对标 chinese-poetry README 的高频词分析图）、诗人页"签名用词" |
| P4 | **题目社交网络抽取** | `SKILL_05_关系构建.md` 的 SPO 三元组思路 | 诗题中的 赠/答/和/酬/送/寄/别/哭 + 人名（唐诗题目高度结构化，如"赠李白""酬乐天扬州初逢席上见赠"） | `data/analysis/poet_network.json` → 诗人页"交游"节、远期网络可视化 |
| P5 | **韵脚与声律分析** | `extract_polyphone_contexts.py`/`analyze_polyphone_*` 的读音管线思路 + pypinyin | 每首末字/偶句末字 × `strains/json/` 平仄 | `data/analysis/rhymes.json`（韵脚分组）、诗体判定（五绝/七律/古体…）→ 卷页诗体徽章、平仄着色 |
| P6 | **热度榜单** | `rank/` 数据（chinese-poetry 自带）+ shiji 的"精品页"分级思想 | `rank/poet/*.json`（经 P2 映射） | `data/analysis/popularity.json` → 首页名篇榜、诗人页热度排序 |
| P7 | **简繁映射质检** | `analyze_simp_trad_mapping.py` + opencc | 全部文本 | 简繁转换歧义字清单 → 决定前端转换 vs 预渲染双版本（§7） |
| P8 | **实体索引（古人/地名/邦国族群/时节）** ✅ | **shiji-kb 的 `kg/entity_index.json` 词表直接复用**（person/place/tribe，按史记引用数过滤）+ 唐代补充词表（年号/节令/唐代邦国/唐诗地名） | 全部题目+正文，简体空间最长匹配 | `data/entities/entity_poem_index.json` → 实体页 `docs/entities/`（史记实体附 wiki 互链） |
| P9 | **名句/典故抽取**（延后） | `extract_chengyu.py`、`extract_citations.py` 模式 | 热度数据 + LLM | `data/analysis/famous_lines.json` → 名句页；属 LLM 管线，随 Phase 5 一起做 |

**方法论一并借鉴**：每条管线一个脚本、输出进 `data/analysis/`（JSON 机读 + MD 人读成对，沿用 shiji 的 `X.json`+`X.md` 惯例）；跑完人工抽检 5–10%；发现系统性错误改脚本重跑（反思循环 `SKILL_03c_按章反思.md` 的精神，但 P1–P7 是纯规则管线，不烧 token）。

---

## 4. 目录结构（本项目）

```
quantangshi-kb/
├── PLAN.md                      # 本文件
├── README.md                    # 项目简介（Phase 0 末补）
├── requirements.txt             # 初期几乎零依赖（标准库）；简繁预转换时加 opencc
├── serve.sh                     # ./serve.sh [port] → docs/ 本地预览
├── scripts/
│   ├── config.py                # 路径常量（POETRY_ROOT 指向 ../chinese-poetry）
│   ├── render_volume.py         # 渲染单卷：JSON → docs/volumes/NNN.html
│   ├── generate_all_volumes.py  # 全量渲染 + docs/index.html
│   ├── build_author_index.py    # P1: 作者归一聚合 → data/authors_merged.json
│   ├── build_poem_id_map.py     # P2: 御定 ↔ poet.tang 匹配 → data/poem_id_map.json
│   ├── analyze_word_frequency.py# P3: 字/词频与意象统计
│   ├── extract_poet_network.py  # P4: 题目社交网络抽取
│   ├── analyze_rhymes.py        # P5: 韵脚/诗体/平仄分析
│   ├── build_popularity.py      # P6: 热度榜单
│   ├── analyze_simp_trad.py     # P7: 简繁映射质检
│   ├── build_search_index.py    # 搜索索引 → docs/data/search_index*.json
│   ├── enrich_poems.py          # 挂接 rank 热度 / strains 平仄 / 三百首标签
│   └── lint_html.py             # 渲染结果校验
├── data/                        # 派生数据（进 git）
│   ├── poem_id_map.json
│   ├── author_aliases.json      # 人工核对的作者别名表
│   ├── authors_merged.json
│   ├── volume_titles.json       # 卷名/卷内统计缓存
│   └── analysis/                # 分析管线产出（JSON+MD 成对）
│       ├── word_freq.{json,md}
│       ├── poet_network.{json,md}
│       ├── rhymes.{json,md}
│       └── popularity.{json,md}
└── docs/                        # 发布站点（全部脚本生成）
    ├── index.html               # 首页：900 卷网格 + 三百首精选 + 统计
    ├── volumes/001.html … 900.html
    ├── authors/                 # 诗人页
    ├── search.html
    ├── css/  js/  data/
    └── favicon.svg
```

---

## 5. 页面设计

### 5.1 卷页 `docs/volumes/NNN.html`（核心页面，对标 shiji 章节页）

- 头部：`卷一` + 卷内诗人列表摘要 + 上一卷/目录/下一卷（三处导航：顶、底，借 chapter-nav.css）
- 正文：按卷内顺序列出每首诗
  - 诗题（`h3`，锚点 id=`p01`）+ Purple Number `（001-01）`（点击复制永久链接）
  - 作者名 → 链到诗人页
  - 诗体正文：每段 `paragraphs[i]` 一行，居中或左对齐诗体版式（区别于史记的散文版式，CSS 需要新的 `.poem` 区块样式：行距疏朗、对句居中）
  - `notes` 折叠显示（借鉴 shiji 三家注的折叠交互思路）
- 同一作者连续多首时，作者小传（biography）只在该作者首次出现处折叠展示一次
- 右上角齿轮：简繁 / 字号 /（后期）高亮开关，偏好 localStorage 持久化

### 5.2 首页 `docs/index.html`

- Hero 区（简化版 shiji 首页）：项目名 + 一句话介绍 + 搜索框
- 900 卷网格（按 50 卷分组折叠，避免一屏 900 格）；每格显示卷号 + 首位诗人
- 精选入口：唐诗三百首、名家（李白/杜甫/白居易…按作品数 top）
- 底部：数据来源与许可（chinese-poetry, MIT）、shiji-kb 致谢

### 5.3 诗人页 `docs/authors/<name>.html`

- 小传：御定 biography（首选）+ `authors.tang.json` 的 desc（补充）
- 作品列表：按卷序，链接到 `volumes/NNN.html#pPP`
- 作品数、（Phase 3 后）热度 top 作品

### 5.4 永久引用格式

`（VVV-PP）` = 第 VVV 卷第 PP 首，URL 形如 `volumes/042.html#p07`。编号由渲染时卷内顺序确定，**一经发布不再变动**（上游数据是静态快照，无风险）。

---

## 6. 分阶段实施

### Phase 0 — 脚手架（半天）✅ 2026-08-31 完成
- [x] 建目录、`scripts/config.py`、`serve.sh`、`requirements.txt`（jieba、pypinyin、opencc；`.venv` 本地虚拟环境）
- [x] 从 shiji-kb 拷贝 CSS/JS（§3.1 清单，`tangshi-styles.css` 等；裁剪适配留到 Phase 2 渲染器落地时）
- [x] `git init`（首次提交待用户确认后执行，遵守工作区 git 规则）

### Phase 1 — 分析管线先行（§3.3，2–3 天）⭐ ✅ 2026-08-31 完成
- [x] **P1 作者归一**：`build_author_index.py` → 匹配率 **94.2%**（2458/2608）；发现御定数据存在上游简→繁过度转换（方幹/鄭穀/於鵠），以异体字折叠表 + 帝王庙号别名种子解决
- [x] **P2 双源对齐**：`build_poem_id_map.py` → 匹配率 **96.2%**（41459/43103：题目精确 34500 + 组诗展开 2173 + 首句兜底 4786）
- [x] **P3 词频/意象**：2,294,515 字；Top 字 不/人/山；句内双字组为主、jieba 仅对照
- [x] **P4 社交网络**：**2,340 条边、802 节点**；Top 往来对 陸龜蒙↔皮日休（177 首，符合松陵唱和史实）
- [x] **P5 韵脚/诗体**：诗体分布 五律 12437 居首；平仄（strains）覆盖 **96.2%**（41456 首）
- [x] **P6 热度**：⚠️ **数据质量发现**——rank 搜索命中数反映词组常见度而非诗篇知名度（《雪》《月》类单字题目虚高数个数量级），不可单独使用；名篇榜改以唐诗三百首为锚（命中 321/366），诗人榜 李白 40 / 杜甫 35 / 王維 28
- [x] **P7 简繁质检**：t2s 改写 2303 字（16.6% 字次）、多对一折叠 113 组；结论：展示方向 繁→简 无歧义，沿用前端 JS 转换即可，**全线禁止 s→t**
- [x] 每条管线出 MD 报告（`data/analysis/*.md`），含抽检样例与未匹配清单
- [x] 验收：`bash scripts/run_all_analysis.sh` 一条命令 38 秒复现全部产出；upstream `chinese-poetry/` 零修改

### Phase 2 — MVP 卷阅读器（1–2 天）✅ 2026-08-31 完成
- [x] `render_volume.py`：单卷 JSON → HTML（诗体版式、`（VVV-PP）`锚点、小传按作者去重折叠、P5 诗体徽章 + P6 三百首徽章；notes 全库为空未渲染）
- [x] `generate_all_volumes.py`：900 卷全量 **1.9 秒** + prev/next + `index.html`（Hero 统计、三百首名篇双栏、名家 chips、9 组折叠卷网格）+ `volume_titles.json` + 构建时生成 `t2s-map.js`（opencc 逐字表 2,305 字，落实 P7 结论）
- [x] 前端资产：`tangshi-styles.css` 全新重写（沿用 shiji 纸色/衬线/深红/紫色段号视觉基调）；`tangshi-settings.js` 替代 shiji 的 750 行设置面板（繁→简切换 + 字号，localStorage 持久化）；`purple-numbers.js`、`chapter-nav.css` 直接复用
- [x] `lint_html.py`：900 卷诗数与源一致、锚点唯一、PN/导航/名篇链接可达、资产齐全 —— 全绿
- [x] 验收：浏览器实测通过 —— 首页→卷页导航、`#p19` 锚点直达（靜夜思 165-19 带双徽章）、繁简切换全页即时生效；站点总体积 27MB

### Phase 3 — 诗人页与搜索（1–2 天）✅ 2026-08-31 完成
- [x] `build_author_pages.py`：**2,608 个诗人页** + 诗人索引页（按作品数三档分组）。每页含小传（御定 biography + authors.tang desc）、统计、P4 交游 chips（悬停示样例诗题）、按卷分组的全部作品链接（带三百首徽章）；卷页作者名已挂链（URL-quote 中文文件名）
- [x] `build_search_index.py` + `tangshi-search.js` + `search.html`：一级索引（题目+作者+诗体，2.5MB）常驻；全文索引按 **100 卷/片 ×9**（843–1390KB）勾选后懒加载并缓存。简繁均可命中：查询词与索引都经 T2S_MAP 折叠成简体再比较（P7 结论的应用）；命中带上下文摘要；支持 `?q=` 直达；首页 Hero 加搜索框
- [x] `build_tang300_page.py`：三百首精选页（321 首按 P5 诗体分组、组内按 P6 榜排序、tags 展示、作者互链）
- [x] `lint_html.py` 扩展：诗人页数量核对、卷页作者链接可达性、tang300/搜索资产齐全 —— 全绿；`build_site.sh` 一键重建站点
- [x] 验收：浏览器实测 —— 李白页（896 首/41 卷/三百首 40/交游 杜甫×9）、简体查询"静夜思"命中繁体题、全文搜索"床前看月光"命中靜夜思并带摘要；站点 54MB

### Phase 3b — 实体分析与索引（P8，借史记词表）✅ 2026-08-31 完成
- [x] `build_entity_index.py`：词表 961 条 —— **直接复用 shiji-kb 实体词表**（古人 3,004 → 过滤取名实体、地名、族群）+ 唐代人工补充（39 年号、17 节令、16 唐代邦国、39 唐诗地名）。匹配在简体折叠空间做（`fold_t2s`，P7 安全方向），最长匹配，展示名取语料最常见繁体表面形式
- [x] 结果：**681 实体、17,601 次命中**（古人 325、地名 252、邦国族群 49、时节 55）；Top：長安 958 诗、相如 139、屈原 25、韓信 23 —— 实为「唐诗中的史记典故引用榜」
- [x] 噪声治理：两轮停用词迭代（公子/中行/無知/如意/白馬 等泛化词剔除）；词表法局限写入报告，逐字精标留给 Phase 5
- [x] `build_entity_pages.py`：**426 个实体页** + 实体索引页（四类 chips）；史记词表实体附 **shiji-kb wiki 互链**（`wiki/#实体名`，跨库典故网络第一步）；首页加顶部导航
- [x] lint 扩展（实体链接可达 + 诗锚点抽查）全绿；站点 58MB

### Phase 3c — P9 文本修复：御定缺行修补 ✅ 2026-08-31 完成

**诊断**（用户发现"有诗缺句"，经查属实且系统性）：御定 JSON 上游抓取按刻本**隔列丢失**
（keep-3-drop-3 句式），33,500 首 1:1 对照中 8,260 首缺文、7,791 首缺 ≥10 字，
長恨歌等长诗恰缺一半；7,622 首齐言诗呈奇数句。另有 □ 阙字 607 处、联句 `——作者` 内嵌 152 首。

**修复**（覆盖层方案，原始数据不动）：
- [x] `build_clean_corpus.py`（P9）：匹配诗正文权威切换为 poet.tang（同书完整抓取），
  御定保留卷结构/小传/题序；安全闸（更长 + 首句 3/5 相符）不过则保留待审
- [x] 产出 `data/corpus_patch.json`（4MB 覆盖层）：**修补 10,227 首，找回 324,577 字（+14.2%）**；
  688 首双源存疑待审（`mismatch_kept`，页面挂"文本待审"徽章）；odd_lines 7,622 → **430**（-94%）
- [x] `lib_qts.iter_yuding()/load_volume()` 默认应用覆盖层（P2 对齐固定用 raw）；全管线+全站重建
- [x] 渲染升级：□ 阙字样式化、联句 `——作者` 转为行内作者标签
- [x] 修复的连锁验证：**七律从榜外跃升至 6,993 首**（截断时被误判为七絕/古體）；
  实体命中 17,601 → 19,197；全文搜索索引覆盖找回的文本
- [x] 报告：`data/analysis/corpus_cleaning_report.md`；残留：1,644 首无匹配（缺文无从考订，
  留待维基文库第三源仲裁）
- [x] **拉丁乱码修复**（2026-08-31 追加）：御定罕用字（gaiji）被上游转成字母数字乱码
  （玉z1↔玉䪥、醴z0↔𨣧、接z5↔䍦），涉及 343 首正文 + 20 个题目；poet.tang 全库零乱码，
  以其为对照做前后文对齐/题目锚定正则，**找回真字 245 处**，无对照的 209 处以 □ 阙字占位
  （flag=latin_fixed / latin_title_fixed）；覆盖层新增 title 字段；全库拉丁字符清零；
  连锁效应：雜言 3,279→3,070（乱码曾破坏齐言判定）

### Phase 3d — 自索引后端与诗歌 API（P10）✅ 2026-08-31 完成
- [x] `build_search_db.py`（P10）：`data/poems.db`（SQLite + **FTS5**，54.9MB，.gitignore）——
  全部 43,103 首（修复后正文+来源+旗标+诗体+三百首标签）+ 诗人表；中文检索用
  **逐字空格分词 + 简体折叠** 短语匹配（任意长度子串、简繁均可）
- [x] `server/api_server.py` + `./api.sh`：零第三方依赖（stdlib http.server + sqlite3，
  对标 shiji-kb serve.py 模式），同时服务静态站与 `/api/*`：
  ping / poem（prev-next）/ volume / author / search（5 种 mode + bm25 加权排序 + 原文摘要）/ stats
- [x] **自索引**：启动时检测 poems.db 缺失或旧于语料（corpus_patch/rhymes/authors_merged）
  自动重建 —— 后端自己维护自己的索引；修 http.server 裸 UTF-8 查询编码
- [x] 搜索页渐进增强：探测 `/api/ping` → 走后端（免下载索引，状态栏示"后端索引"）；
  无后端（GitHub Pages）回退静态分片索引，两条路径共存
- [x] 验收：curl 全端点 + 浏览器实测（明月 meta 25 首 / 全文 874 首带摘要；简繁查询均命中）

### Phase 3e — 首页 API 化重设计 ✅ 2026-08-31 完成
- [x] **今日一诗**（首页签名元素）：按日期从三百首确定一首，**竖排右起、去标点**渲染
  （仿御定刻本书叶版式——语料本身就是竖排刻本），朱色「今日一詩」印章 + 日期 +
  题目朱字首列 + 作者落款列；「换一首」随机再抽；点击进全诗
- [x] 数据双路：API 在线走 `/api/poem`（权威库），离线用构建烘焙的
  `data/tang300_poems.json`（321 首全文，build_tang300_page.py 生成）——GitHub Pages 同样可用
- [x] **Hero 即时搜索**：API 在线时输入即出下拉（`/api/search mode=meta limit=8`，
  180ms 防抖、过期响应丢弃、Esc/点外关闭、"全部结果 →"直达搜索页）；无 API 保持表单跳转
- [x] 新增诗体分布 chips 行（P5 数据）；名篇/今日一诗 双栏布局，移动端堆叠；
  prefers-reduced-motion 支持
- [x] `js/tangshi-home.js` + CSS（竖排卡、印章、下拉）；lint 资产扩充；
  浏览器实测：API 模式（"登高"下拉 8 条+54 总数）与纯静态模式（卡片同样渲染）均通过

### Phase 4 — 增强展示 ✅ 2026-08-31 完成
- [x] 三百首/诗体徽章（已随 Phase 2 挂载）；简繁方案已落地（前端 JS 字表，P7 结论）
- [x] **平仄展示**：`build_strains_data.py` 按卷烘焙（服务端对齐渲染行，**39,414 首/95.1%**
  字数吻合才输出，杜绝前端错位）→ `docs/data/strains/NNN.json`（900 文件）；
  settings 新增"平仄"开关（默认关，仅卷页），**逐字对位 ruby 注于字下**
  （○平●仄◌未定，v1 行末缀式已升级），联末韵脚位标红 —— 史记没有、唐诗独有的
  "语法高亮"；与实体高亮/简繁转换共存（诗行统一自原始繁体重建的管线）

### Phase 5 — 实体标注与高亮（词表法已落地；LLM 精标留远期）✅ 词表版 2026-08-31
- [x] **行内实体高亮**：渲染时用 P8 词表（有页面的 447 实体）最长匹配，命中片段包成
  `<a class="ent ent-{person|place|nation|time}">` 链向实体页；配色沿用 shiji-kb 语义
  （人名褐/地名赭/邦国紫/时节青，淡底+特征下划线）
- [x] settings 新增"实体"开关（默认开；关闭时 CSS 还原为正文，链接仍可点）
- [x] 与简繁转换/平仄标注共存无冲突；浏览器实测（001-03：新城/流沙 高亮+链接）
- [x] **LLM 精标（三百首全量已落地，见 Phase 7 ④）**：词表法有一词多义误报与覆盖缺口
  （如 新豐 不在史记词表），精标以 `pilot_annotations.json` 阅读序游标格式覆盖全部
  三百首 327 首；全库 4.9 万首扩标留远期；典故实体与 shiji wiki 互链已在实体页实现

### Phase 3f — 单诗页与三百首成册 ✅ 2026-08-31 完成
- [x] **单诗页** `poem.html?id=VVV-PP`：任意一首可单独查看（大字诗体版式、作者/卷信息、
  卷内上一首/下一首、「在卷中查看」回卷页锚点）。数据源为按卷烘焙的
  `data/volumes/NNN.json`（900 文件 22MB，含预渲染实体链接行 + prev/next），
  纯静态、GitHub Pages 可用；卷页每首标题旁加 ❐ 单独页入口 —— **卷中读与单独读自由切换**
- [x] **三百首独立成册** `docs/tang300/`（321 页服务端生成）：按目录序
  上一首/下一首翻阅（"三百首 第 N/321 首"），附体裁标签与「在卷中查看」；
  tang300.html 目录与首页名篇均改链成册页；今日一诗卡改链单诗页
- [x] 平仄/简繁/实体开关在三种诗文页（卷页/单诗页/成册页）统一生效：
  settings 的诗文语境识别泛化 + `QTS_REFRESH` 钩子（动态注入内容渲染后补装饰）
- [x] lint 扩充（成册页数与目录一致、单诗页资产、卷数据抽查）全绿
- [x] **平滑翻页**（2026-08-31 追加）：单诗页 SPA 化 —— 上一首/下一首原地更新 DOM +
  pushState（同卷零网络、跨卷预取相邻卷数据），支持 ←/→ 方向键与浏览器前进后退，
  切换加 View Transitions 160ms 淡入淡出；成册页/卷页等静态跳转启用跨文档
  View Transitions + 相邻页 prefetch，全站无白闪（prefers-reduced-motion 尊重）
- [x] **搜索默认进单诗页**：搜索结果与首页即时搜索下拉均链 `poem.html?id=`，
  卷中上下文从单诗页「在卷中查看」一键达
- [x] **搜索结果带作者作品序**：索引第 5 位存规范作者名（与显示名同则省略省体积），
  静态/API/全文三路搜索与首页下拉的链接均带 `&author=` —— 点开即"某某 作品
  第 N/M 首"，可顺势逐首读该诗人
- [x] **今日一诗升级**（2026-08-31 追加）：整联智能截取（全诗 ≤8 行竖排全显，
  长诗取前 8 行标"节选"）、卡高随内容自适应（短诗紧凑）、落款列独立链诗人页、
  页脚加诗体、**应季优先**（按月份季节过滤三百首标签构成候选池，仍按日确定，
  池小回退全集）；烘焙数据补 canonical/tags
- [x] **诗人页逐首阅读**：诗人页升级（标题栏加生卒年、▶ 逐首阅读入口、作品双链——
  **题目默认进诗人作品序阅读**、（编号）保留卷中上下文）；`poem.html` 支持
  `&author=` 参数，按 `data/authors/{规范名}.json`（2,608 个作品序列）跨卷逐首
  推进（"李白 作品 第 N/896 首"，👤 回诗人页），SPA 翻页与三百首成册一致
- [x] **成册页同样 SPA 化**（`js/tangshi-book.js` + `data/tang300_order.json`）：
  上一首/下一首按目录序原地换数据 + pushState 到真实页面路径（跨卷翻页
  自动换取对应卷数据与平仄），服务端 321 页保留为入口/无 JS 回退；
  ←/→ 方向键、前进后退、View Transitions 淡入淡出与单诗页一致

### Phase 7 — 深化三件套 ✅ 2026-08-31 完成

**① 残留复审（数据修复三连）**
- [x] P2 匹配归一补 `fold_t2s`（嶽/岳、荊/荆 曾致漏配）→ 匹配率 **96.2% → 97.9%**（+750 首）
- [x] P9 认同闸加**三样片内容兜底**（御定首列亦可能丢失，首句闸误拒）→
  存疑 **688 → 122**（-82%），再补 820 首 / 7.6 万字，累计找回 **+17.5%**；七律 7,144 反超七絕
- [x] P6 三百首 join 加内容兜底（同诗异抄本按作者+折叠题、组诗子首按首句包含）→
  未匹配 **45 → 4**（余者均为上游选本缺陷：宋人蔡襄/釋明辯、黄拱误题）；
  新增学术别名 張佖=張泌、楊敬述進=楊敬述
- [x] P4 官称假阳性剪除（「送鄭明府」≠ 鄭明：名后接 府/君/曹/尹/丞/簿/尉 者弃）→ -85 边

**② 诗中地图**（`app/map/`，Phase 6 欠账清偿）
- [x] 人工坐标表 `data/place_coords.json`（**133 处**唐代地望 + 邦国族群约略中心，r 标泛称）
- [x] 写意 SVG 底图（手绘简化海岸线 + 黄河/长江），**123 点上图**：点面积∝诗数、
  虚线圈=泛称地域、紫=邦国族群、点击进实体页；长安墨团/江南密簇/湘楚贬谪走廊/
  北疆戍边带/塞外游牧诸部一目了然

**③ 实体精标试点（LLM 逐字标注）**
- [x] 标注格式 `data/annotations/pilot_annotations.json`（表面形+类型+可选目标键，
  阅读序游标应用；空数组=精审无实体并抑制词表误标）+ 渲染管线（apply_pilot，
  precedence 高于词表匹配，「精標」徽章遍布卷页/单诗页/成册页）
- [x] **40 首名篇精标**（~90 条）：含词表做不到的判定——单字邦国（秦/漢/胡/楚/燕/越/吳）、
  典故人物（龍城飛將、蠶叢魚鳧、太真/小玉/雙成）、别称归并（鳳城/丹鳳城→长安、
  岱宗→泰山、錦城→锦官城、華清池/驪宮→华清宫）、词表停用词回捞（雲中=魏尚典故、
  太白=山名）；長恨歌全篇 24 处
- [x] **精标注释**：条目第 4 位为学术性注解（~70 条：典故出处、别称考释、
  以汉代唐惯例等），渲染为悬停即显的样式化气泡（data-note + CSS tooltip），
  「精標」徽章在卷页/单诗页/成册页齐备
- [x] 试点验证了远期全量 LLM 标注的格式与管线；扩标只需增补 JSON

**④ 三百首全量精标 ✅ 2026-08-31**（试点 40 首 → **全 327 首**）
- [x] 逐首 LLM 精标 **984 条**（地名 600 / 人物 232 / 邦国族群 134 / 时节 18），
  其中 **874 条带学术注释**（典故出处、地望考释、以汉代唐、官称辨析）；
  **76 首精审判定无实体**（空数组抑制词表误标，如「春眠不覺曉」）
- [x] 阅读序游标暴露的次序错误两处（435-19 長恨歌 七月七日、220-34 寄韓諫議 玉京）
  均已修正，`generate_all_volumes` 零未命中告警
- [x] tang300 目录页标注「全部实体精标」；成册页/卷页/单诗页「精標」徽章全覆盖

### Phase 6 — 可视化实验 ✅ 2026-08-31 完成（地图已于 Phase 7 补齐）
- [x] **诗人交游网络**（`app/network/`，对标史记地铁图的探索式交互）：零依赖 canvas
  力导向图（网格分桶斥力 + 弹簧引力，渐进布局动画），P4 数据聚合为 802 节点 /
  1,269 组往来对；节点大小=往来次数、红色=三百首诗人；拖拽/缩放/悬停（含样例诗题
  tooltip）/点击进诗人页/搜索定位/「显示全部」过滤（默认仅 ≥2 次往来，246 节点）
- [x] **诗人长河**（`app/timeline/`，服务端生成整页 SVG）：横轴为**公元纪年**——
  新增人工核对表 `data/poet_years.json`（159 位诗人生卒年，约略者标记；月份史料多无考，
  精确到年），存诗 ≥30 首者 **126 位可考**上图 + 72 位"生卒无考"chips 列出；
  初唐/盛唐/中唐/晚唐/五代**分期底带**；虚线框=约略、圆点=仅单端可考、
  红色=三百首入选、透明度≈存诗数、点击进诗人页
  （v1 曾用御定编次卷号作时代近似，已被生卒年版取代）
- [x] `build_viz.py` 入 build_site.sh；首页导航加"交游网络 / 诗人长河"；lint 资产扩充全绿
- [ ] 地名地图：待坐标数据（可借 shiji-kb 的谭其骧地图工作流 + CHGIS），另立计划

---

## 7. 关键决策与风险

| 决策/风险 | 结论 |
|---|---|
| 主干选御定还是 poet.tang？ | **御定**：卷结构天然对应章节阅读器，含小传与校注；poet.tang 作增强层 |
| 900 页会不会太多？ | 不会。均值 ~64 首/卷，页面体量与 shiji 章节页相当；生成耗时预计分钟级 |
| 两源匹配不准 | 增强字段全部**可缺省**；匹配表进 `data/` 可人工修订 |
| `no#` 键名 | JSON 解析用 `poem["no#"]`，不要当注释处理 |
| 简繁问题 | 数据为繁体；默认繁体 + 前端切换起步，效果不好再预渲染双版本 |
| 搜索索引体积 | 一级索引全量、全文按卷分片懒加载 |
| 上游数据只读 | 渲染脚本以只读方式访问 `../chinese-poetry`，绝不写回；本项目派生数据独立版本管理 |
| 许可 | chinese-poetry 为 MIT，需在首页/README 署名；本项目代码 MIT |

---

## 8. MVP 验收标准

1. `python scripts/generate_all_volumes.py` 一条命令再生整站，无报错
2. 900 卷页 + 首页 + `lint_html.py` 全部通过
3. 任意诗可通过 `（VVV-PP）` 链接直达并高亮定位
4. 卷页在手机宽度下可读（继承 shiji CSS 的响应式）
5. 上游 `chinese-poetry/` 目录 `git status` 干净（零修改）

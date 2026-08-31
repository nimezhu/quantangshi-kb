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
| P8 | **名句/典故抽取**（延后） | `extract_chengyu.py`、`extract_citations.py` 模式 | 热度数据 + LLM | `data/analysis/famous_lines.json` → 名句页；属 LLM 管线，随 Phase 5 一起做 |

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

### Phase 3 — 诗人页与搜索（1–2 天）
- [ ] 诗人页生成（P1 的 `authors_merged.json` + P4 交游节 + P6 热度排序）+ 卷页作者名挂链
- [ ] `build_search_index.py`：一级索引（题目+作者，全量 ~4.9 万题，单 JSON 预计 3–5 MB，可接受）；全文索引按卷分片 900 个小 JSON，搜索页按需加载
- [ ] 三百首精选页（`唐诗三百首.json` 的 tags 做标签筛选）

### Phase 4 — 增强展示（1 天）
- [ ] `enrich_poems.py`：热度徽章（P6）、三百首徽章挂到卷页
- [ ] 平仄展示：settings 开关打开后，借 strains 数据在诗行下方以 ○●（平/仄）标注 —— **这是史记没有、唐诗独有的"语法高亮"**；韵脚字着色（P5）
- [ ] 简繁方案落地（按 P7 结论：前端 JS 转换或 opencc 预渲染双版本）

### Phase 5 — 实体标注与高亮（远期，另立计划）
- 借鉴 shiji 标注体系的**子集**（人名/地名/典故/时间 4–6 类即可，诗歌不需要 22 类）
- 若启动：引入 `volume_md/NNN.tagged.md` 作为 Base Copy，完整继承 shiji-kb 的标注铁律（全角引号、无嵌套、文本完整性 lint）与 SKILL 驱动的 agent 批量标注流程
- 典故实体可与 shiji-kb 的 wiki 页互链（跨库知识网络的第一步）

### Phase 6 — 可视化实验（远期）
- 诗人生卒年时间线（对标"史记地铁图"）、诗人交游网络（P4 数据可视化）、地名地图

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

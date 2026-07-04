---
name: youtube-transcript-doc
description: >-
  Turn a YouTube video (or any video with subtitles) into a polished, readable
  transcript document in Feishu/Lark — fetch the subtitles, parse them into
  clean speaker-turn paragraphs, remove filler words and ASR errors, translate
  (e.g. English→Chinese bilingual), add clickable timestamp jump-links back to
  the video, pull out highlight-moment cards, and publish to a Lark doc. Use this
  whenever the user shares a YouTube/video link and wants a transcript, 逐字稿,
  timeline, meeting-notes-style writeup, subtitle extraction, or a "watch this
  video and write it up" task — even if they don't say the word "skill". Also use
  it when they want to clean up / bilingualize / re-lay-out an existing video
  transcript, or to add a visual summary whiteboard distilling the key points.
  Do NOT use it for local audio files (use a transcription tool) or
  for Feishu Minutes/妙记 (use the minutes skill).
---

# YouTube 视频 → 精修逐字稿文档

把一条 YouTube（或带字幕的）视频，做成一篇**可读、可跳转、可沉淀**的飞书逐字稿文档。

整条链路：**读到视频 → 抓 SRT → 解析成段 → 清洗+翻译 → 生成飞书文档 → 可视化总结白板（必做）**。

## 何时用
用户丢来一个视频链接，想要逐字稿 / timeline / 会议纪要式整理 / 字幕提取 / 中英对照 / "帮我看看这个视频并整理出来"。

## 流程

### 1. 拿到 video_id 和基本信息
从 URL 提取 11 位 video id。若能顺手拿到标题、时长、嘉宾/发布者，记下来——写进文档头部信息框。

### 2. 抓字幕（最容易卡的一步）
直连 YouTube 取字幕基本会被反爬挡掉，**不要死磕**。按 `references/fetch-srt.md` 的降级链走：
第三方字幕站（downsub 首选，用 remote browser 打开→提取 `download.subtitle.to` 下载 blob→curl 直取）
→ browser 抓页面文字 → 让用户手动导出。拿到后存成 `transcript.srt`。

### 3. 解析成说话人段落
```bash
python scripts/parse_srt.py transcript.srt --video-id <VIDEO_ID> --out turns.json
```
按 `>>` 说话人标记切分（无标记则退回定长切分）。**这一步根治"一句话被拆成两段"**——
之前按固定秒数硬切会拦腰截断句子，按说话人 turn 切每段都是完整发言。脚本同时删掉纯语气词的独立段。

### 4. 清洗 + 翻译
按 `references/clean-translate.md`：删语气词、删口吃重复、修 ASR 错误（人名/术语/公司名）、
逐段翻译。近百段时拆 2–3 批用并行子 agent 处理，共享一张术语修正表，各自输出 `{index:{en,zh}}` 的 JSON，合并成一个 content 文件。

内容备好后，按 `scripts/build_doc.py` 头部注释的结构拼一个 `content.json`，然后：
```bash
python scripts/build_doc.py turns.json content.json --outdir frags/
```
生成 `frags/intro.xml` 和 `frags/sec_0.xml … sec_N.xml`。

`content.json` 的 schema（`build_doc.py` 头部有完整示例，别推翻）：
- `meta`：标题、来源、视频链接、时长、嘉宾——写进头部信息框。标题朴素，不加"中英对照"之类标签。
- `sections[]`：主题分节。`title` 用**双语** `"English / 中文"`；`summary` 是这一节的一句话「重点」概述（渲染成节标题下的 💡 卡片，带可点击时间戳）。
- `highlights[]`：编辑精选的核心观点，渲染成顶部 ⭐ 黄色卡片。
- `paras{}`：正文，以段索引为键。每段带 `speaker`（说话人名，加粗前缀）、`en`、`zh`，以及 `key` 布尔值。
- `bilingual`：true = 每段渲染成「灰色英文参考行 + 黑色中文主行」两行扁平段落；false = 单行中文段落。

**版式铁律**（沉淀自真实用户反馈，`build_doc.py` 已内置，别推翻）：
- 标题朴素，不在标题里塞"中英对照"之类标签。
- **正文是扁平段落，不是卡片**：每个 turn 就是一行（或双语两行）`<p>`，不要把 turn 包成 callout 卡片、更不要做两列网格——用户明确否掉了卡片化正文，卡片正文太重、反而难读。
- **每段都标说话人**：发言人名加粗做前缀（`Federico：…`），让读者一眼看清谁在说，长对话尤其重要。
- **双语靠颜色区分，不显式标 EN/ZH**：英文用灰色（`text-color="gray"`）当参考行，中文用默认黑色当主行放在下面。
- **不要整段加粗**：`key` 的重点强调交给节标题下的 💡「重点」卡片，正文段落保持不加粗（整段加粗=噪音，用户和原设计都否过）。
- **每节标题下加一张 💡「重点」卡片**（可点击时间戳 + 一句话概述），这是全篇唯一的正文卡片，先给读者本节主旨。
- 高光段只用 ⭐ 标记，黄色高亮留给顶部 highlights 卡片。

### 5. 发布到飞书
用 lark-doc skill（`docs +create` 建文档写入 intro，再 `docs +update --command append` 逐节追加）。
调用细节见 `references/publish-lark.md`。发布后把文档 URL 给用户。

### 6.（必做）生成可视化总结白板
逐字稿发布后**必须**再产出一张**提炼重点的可视化总结白板**，嵌进同一篇文档——这一步不是可选项，是标准交付物的一部分。

**直接调用 `beautiful-feishu-whiteboard` skill 来画**（本环境已安装的专业绘图引擎，用 Skill 工具启动），不要自己手搓 SVG 排版逻辑。交给它：
1. 从 `content.json` / turns 里提炼出 4–8 个**主题簇**、每簇 3–5 条要点（短句，不要搬逐字稿原句）；
2. 把这些结构 + 已发布的飞书文档 `document_id` 传给该 skill，让它选构图模式、生成 SVG、写入白板、回查线上真图；
3. 白板要**嵌进本篇逐字稿文档**，而不是新建一篇文档；**位置放在「⭐ 高光时刻」和「📝 完整逐字稿」之间**（不是尾部）——用 `block_insert_after` 插到高光区结尾的分割线块之后。

具体的构图/配色/写入/回查细节由 `beautiful-feishu-whiteboard` 自己的 SKILL.md 负责；本 skill 只负责把提炼好的结构和目标文档交过去。补充踩坑见 `references/whiteboard-summary.md`。

## 迭代
用户常会在文档里留**评论**再让你改。用 lark-doc 的 `+get-comments` 拉评论，逐条落实。
若涉及断句错误——回到第 3 步用说话人 turn 重切，别在错误的分段上打补丁。

## 资源
- `scripts/parse_srt.py` — SRT → 说话人段落 JSON
- `scripts/build_doc.py` — 段落+译文 → 飞书 XML 片段（版式已内置）
- `references/fetch-srt.md` — 抓字幕降级链（重点）
- `references/clean-translate.md` — 清洗/翻译/版式规范
- `references/publish-lark.md` — lark-doc 建档与追加、拉评论
- `references/whiteboard-summary.md` — 可视化总结白板：交给 `beautiful-feishu-whiteboard` skill 来画（含“文字必须上浅底”的踩坑）

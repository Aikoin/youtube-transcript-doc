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
逐段翻译，并把 ASR 合并的「提问+回答」按语义切点拆成有序 `segs`（每个 `{speaker, en, zh}`；字幕没带名字就 `speaker=""`，绝不硬编）。
近百段时拆 2–3 批用并行子 agent 处理，共享一张术语修正表，各自输出 `{index: {segs:[...], key:bool}}` 的 JSON，合并成一个 content 文件。

内容备好后，按 `scripts/build_doc.py` 头部注释的结构拼一个 `content.json`，然后：
```bash
python scripts/build_doc.py turns.json content.json --outdir frags/
```
生成 `frags/intro.xml` 和 `frags/sec_0.xml … sec_N.xml`。

`content.json` 的 schema（`build_doc.py` 头部有完整示例，别推翻）：
- `meta`：标题、来源、视频链接、时长、嘉宾——写进头部信息框。标题朴素，不加"中英对照"之类标签。
- `sections[]`：主题分节。`title` 用**双语** `"English / 中文"`；`summary` 是这一节的一句话「重点」概述（渲染成节标题下的 💡 卡片，带可点击时间戳）。
- `highlights[]`：编辑精选的核心观点，渲染成顶部 ⭐ 黄色卡片。
- `paras{}`：正文，以段索引为键。每段用 `segs`（有序子发言列表，每个 `{speaker, en, zh}`）承载卡内多说话人，外加 `key` 布尔值。**`speaker` 只在字幕自带名字或你非常确定时才填；不确定就留空 `""`**（详见下条铁律）。单人段也可用扁平 `{speaker,en,zh,key}`（无 segs）向后兼容。
- `bilingual`：true = 每段渲染成两列 callout 卡片（左 💬 灰卡英文、右 💬 蓝卡中文）；false = 单张蓝卡中文。

**版式铁律**（沉淀自真实用户反馈 + 对标 codex 更清爽的同类产出，`build_doc.py` 已内置，别推翻）：
- 标题朴素，不在标题里塞"中英对照"之类标签。
- **正文用双列 callout 卡片**：每个 turn 渲染成一张两列网格卡片——左列英文、右列中文，比一堵 `<p>` 墙更好扫读。
- **靠「卡片颜色」区分角色，不靠加粗**：这是踩过坑的关键。左列英文用**中性 light-gray**卡片（💬，正文灰字）当参考/原文列；右列中文用**主色 light-blue**卡片（💬，正文黑字）当主读列；节「重点」卡片用**绿色 light-green**（💡）；顶部高光卡片用**黄色 light-yellow**（⭐）。四种卡片四种颜色，一眼分得清角色——**别让所有卡片同一个背景色**（用户明确否掉过"同一 callout 背景色、同一字色、满屏加粗"的杂乱版）。
- **卡内多说话人拆 segs，换人处标记不硬安名字（铁律，踩过坑）**：ASR 常把「提问+回答」并进一段。把它拆成有序 segs，换到的子段前加加粗前缀——**有确定名字**标 `名字：`，**没名字**（`>>` 无标签字幕，谁说的纯属推断）就用中性破折号 `— `，**绝不编造说话人**免得张冠李戴误导读者。时间戳 + ⭐ 单独成头部一行。
- **绝不整段加粗**：卡片正文任何时候都不整段加粗（整段加粗=噪音，用户反复否过）；加粗只留给说话人名字/换人破折号前缀。`key` 的重点强调交给节标题下的 💡 绿色「重点」卡片。
- **每节标题下加一张 💡 绿色「重点」卡片**（可点击时间戳 + 一句话概述），先给读者本节主旨。
- 高光段只在卡片头部加 ⭐ 标记，黄色高亮留给顶部 highlights 卡片。

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

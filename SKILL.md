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
  transcript. Do NOT use it for local audio files (use a transcription tool) or
  for Feishu Minutes/妙记 (use the minutes skill).
---

# YouTube 视频 → 精修逐字稿文档

把一条 YouTube（或带字幕的）视频，做成一篇**可读、可跳转、可沉淀**的飞书逐字稿文档。

整条链路：**读到视频 → 抓 SRT → 解析成段 → 清洗+翻译 → 生成飞书文档**。

## 何时用
用户丢来一个视频链接，想要逐字稿 / timeline / 会议纪要式整理 / 字幕提取 / 中英对照 / "帮我看看这个视频并整理出来"。

## 五步流程

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

内容备好后，按 `scripts/build_doc.py` 头部注释的结构拼一个 `content.json`（含 meta / sections 主题分节 / highlights 高光卡片 / paras 正文 / bilingual 开关），然后：
```bash
python scripts/build_doc.py turns.json content.json --outdir frags/
```
生成 `frags/intro.xml` 和 `frags/sec_0.xml … sec_N.xml`。

**版式铁律**（沉淀自真实用户反馈，`build_doc.py` 已内置，别推翻）：
- 标题朴素，不加"中英对照"之类标签；
- 中英用**颜色**区分（英文灰、中文黑），不写 EN/ZH 字样；
- **不整段高亮**，高光段只用 ⭐ 标记，黄色高亮留给顶部卡片；加粗/高亮的具体短句留给人工。

### 5. 发布到飞书
用 lark-doc skill（`docs +create` 建文档写入 intro，再 `docs +update --command append` 逐节追加）。
调用细节见 `references/publish-lark.md`。发布后把文档 URL 给用户。

## 迭代
用户常会在文档里留**评论**再让你改。用 lark-doc 的 `+get-comments` 拉评论，逐条落实。
若涉及断句错误——回到第 3 步用说话人 turn 重切，别在错误的分段上打补丁。

## 资源
- `scripts/parse_srt.py` — SRT → 说话人段落 JSON
- `scripts/build_doc.py` — 段落+译文 → 飞书 XML 片段（版式已内置）
- `references/fetch-srt.md` — 抓字幕降级链（重点）
- `references/clean-translate.md` — 清洗/翻译/版式规范
- `references/publish-lark.md` — lark-doc 建档与追加、拉评论

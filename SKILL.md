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

整条链路：**读到视频 → 抓 SRT → 解析成段 → 清洗+翻译 → 生成飞书文档 → 规划并交付可视化总结白板（必做）**。
（末步分两半：本 skill 先规划白板的**内容结构/风格/构图**，再交给 `beautiful-feishu-whiteboard` skill 画。）

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
逐段翻译，并把 ASR 合并的「提问+回答」按语义切点拆成有序 `segs`（每个 `{speaker, zh, en_keep}`；字幕没带名字就 `speaker=""`，绝不硬编）。
近百段时拆 2–3 批用并行子 agent 处理，共享一张术语修正表，各自输出 `{index: {segs:[...], key:bool}}` 的 JSON，合并成一个 content 文件。

**内容清洗规律**（沉淀自逐轮用户 comment，已成铁律，新项目照做）：
- **中文段落用中文全角标点**：中文子句里的 `,;:?!` 一律转全角。判定用「CJK 相邻」——只在前一个或后一个字符是汉字时才转，**保住英文 token 内的半角**（如 `productpass.com`、`SSO:`、代码）。两个英文词之间但明显是中文分隔的逗号（如「Ambrosino,OpenAI」）属漏网，手工补成全角。
- **删广告/赞助口播**：productpass、WorkOS、Mercury 这类插播赞助整段删。启发式：凡「访问 xx 网站了解更多 / 用码 xx 打折」= 广告。结尾的自我推广也裁掉，只留真诚的道别/致谢。
- **别硬翻俚语/行话，保留英文原词**：如「吃自己狗粮」硬翻很别扭，写成 `dogfooding（内部试用）`；技术黑话同理，保原文加简短括注即可。
- **合并被 ASR 拆断的同一句**：ASR 常在停顿处把一句连续发言拦腰切成好几段。**同一说话人**、语义连续的碎段合并成一个 turn（首段吸收后段，后段清空 `{'speaker':'','zh':'','en_keep':''}`）；但**真正的短插话/附和/回声**（别人的一句「对」「没错」）保留成独立 turn，别误并。
- **高光卡时间戳必须指向金句真实出现的位置**：`highlights[].sec` 要落在这句话实际被说出的秒数，不能挂到一个它根本没出现的小节；一句金句不属于某节就别塞进那节的「重点」卡，节 summary 只写该节自己的主旨。

内容备好后，按 `scripts/build_doc.py` 头部注释的结构拼一个 `content.json`，然后：
```bash
python scripts/build_doc.py turns.json content.json --outdir frags/
```
生成 `frags/intro.xml` 和 `frags/sec_0.xml … sec_N.xml`。

`content.json` 的 schema（`build_doc.py` 头部有完整示例，别推翻）：
- `meta`：标题、来源、视频链接、时长、嘉宾——写进头部信息框。标题朴素，不加"中英对照"之类标签。
- `sections[]`：主题分节。`title` 用**双语** `"English / 中文"`；`summary` 是这一节的一句话「重点」概述（渲染成节标题下的 💡 绿色卡片，带可点击时间戳）。
- `highlights[]`：编辑精选的核心观点，渲染成顶部 ⭐ 黄色卡片。`sec` 必须指向金句真实出现的秒数。
- `paras{}`：正文，以段索引为键。每段用 `segs`（有序子发言列表，每个 `{speaker, zh, en_keep}`）承载多说话人，外加 `key` 布尔值。**`speaker` 只在字幕自带名字或你非常确定时才填；不确定就留空 `""`**（详见下条铁律）。**`en_keep` 只在值得展示英文原文的重点 seg 上填**，普通闲聊留 `""`——正文不逐句中英对照，以免上下翻倍。单人段也可用扁平 `{speaker,zh,en_keep,key}`（无 segs）向后兼容。
- `_no_ts_sections`：要**隐藏全部时间戳**的小节索引数组（如 Cold Open 蒙太奇，逐句时间戳纯是噪音）。

**版式铁律 v3**（沉淀自真实用户反馈 + 对标 codex 更清爽的同类产出，`build_doc.py` 已内置，别推翻）：
- 标题朴素，不在标题里塞"中英对照"之类标签。
- **正文用普通段落，不用卡片**（v3 关键改版）：旧版把每个 turn 渲染成「双列 callout 卡片」，用户反馈太满、像一墙卡片。v3 正文就是普通 `<p>`——像文档而非卡片墙。卡片**只留给真正该强调的东西**：节「重点」、顶部高光、头部信息框。
- **中文为主线，英文原文作引用块**：每个 turn 先出中文普通段落；时间戳链接（+ ⭐ 若含高光）内联在**首个中文段落开头**。该 turn 若有 `en_keep`，英文原文渲染成中文下方的灰字 `<blockquote>` 引用块。
- **换说话人不硬安名字（铁律，踩过坑）**：ASR 常把「提问+回答」并进一段。拆成有序 segs，换到的子段——**有确定名字**标 `名字：`，**没名字**（`>>` 无标签字幕，谁说的纯属推断）就用中性 **🗣️** 前缀（不是生硬的破折号 `— `），**绝不编造说话人**免得张冠李戴误导读者。
- **绝不整段加粗**：正文任何时候不整段加粗（整段加粗=噪音，用户反复否过）；加粗只留给说话人名字前缀、节「重点」标签。
- **靠「卡片颜色」区分强调角色**：节「重点」卡用**绿色 light-green**（💡）；顶部高光卡用**黄色 light-yellow**（⭐）；头部信息框用**蓝色 light-blue**（🎙️）。三种卡三种颜色，一眼分得清。
- **每节标题下加一张 💡 绿色「重点」卡片**（可点击时间戳 + 一句话概述），先给读者本节主旨；`_no_ts_sections` 里的节则不带时间戳。
- 高光段只在正文头部加 ⭐ 标记，黄色高亮留给顶部 highlights 卡片。

### 5. 发布到飞书
用 lark-doc skill（`docs +create` 建文档写入 intro，再 `docs +update --command append` 逐节追加）。
调用细节见 `references/publish-lark.md`。发布后把文档 URL 给用户。

### 6.（必做）生成可视化总结白板
逐字稿发布后**必须**再产出一张**提炼重点的可视化总结白板**，嵌进同一篇文档——这一步不是可选项，是标准交付物的一部分。

**分工铁律：本 skill 先想清楚「画什么、什么风格、怎么画」，再把这份 brief 交给 `beautiful-feishu-whiteboard` skill 去画（渲染/写入画板/回查线上真图）。** 别跳过规划直接甩要点——那样出来的是「PPT 罗列」而非「关系地图」，风格构图全靠绘图 skill 猜；也别反过来去改 `beautiful-feishu-whiteboard` 的内部逻辑，它是通用引擎，本 skill 只是它的调用方。

**先规划（6.1，交给绘图 skill 前必须先定下三件事，写成一份 brief）：**
1. **内容结构**：从最新 `content.json` / turns 提炼 4–8 个**主题簇**、每簇 3–5 条要点（短句，不搬原句），每簇标时间戳，编号①②③…；**并想清楚簇之间的叙事主线**（递进 / 收束 / 并列），骨架跟着主线走，不是把框摆成网格。
2. **风格基调**：按视频调性定一句话偏好（冷静克制 / 暖色有节奏）+ 2–3 个强调色的用法（分区/标记不同「幕」）。**把「想要什么感觉」讲清楚，让绘图 skill 从它自己的 35 套色板里挑**，不替它指定具体色板名。
3. **构图骨架**：递进→单主轴+分支；收束→多路汇聚到一个决定框；并列→分栏对比。连线**只画真实关系**（依赖/产出/对应），不因「挨着」就连；给「终点/升华」框更强视觉权重。

**再交付（6.2）：** 把这份 brief + 已发布文档的 `document_id` 交给 `beautiful-feishu-whiteboard`（用 Skill 工具启动），要求：
- **嵌进本篇逐字稿文档**，不新建文档；**位置放在「⭐ 高光时刻」和「📝 完整逐字稿」之间**（不是尾部）——用 `block_insert_after` 插到高光区结尾的分割线块之后；
- 走完它自己的「渲染 → 检查 → 写入画板 → 回查线上真图」全流程。

**两条必盯的坑**（详见 `references/whiteboard-summary.md`）：
- **写图前重新 `docs +fetch` 拿当前生效的 `<whiteboard token>`**：若文档在插板后又被 `overwrite` 整篇重写，旧白板块会被换成新块、旧 token 变孤儿——往孤儿 token 写图，本地查得到、用户在文档里却看不到更新。
- **文字必须放浅色底用深墨色**：飞书线上会把文字压深色，别信本地 PNG 预览的字色，写入后回查线上真图再确认对比度。

构图模式实现、配色体系、形状规范、写入/回查细节由 `beautiful-feishu-whiteboard` 自己的 SKILL.md 负责；本 skill 到 6.1 的 brief 为止。

## 迭代
用户常会在文档里留**评论**再让你改。用 lark-doc 的 `+get-comments` 拉评论，逐条落实。
若涉及断句错误——回到第 3 步用说话人 turn 重切，别在错误的分段上打补丁。

## 资源
- `scripts/parse_srt.py` — SRT → 说话人段落 JSON
- `scripts/build_doc.py` — 段落+译文 → 飞书 XML 片段（版式已内置）
- `references/fetch-srt.md` — 抓字幕降级链（重点）
- `references/clean-translate.md` — 清洗/翻译/版式规范
- `references/publish-lark.md` — lark-doc 建档与追加、拉评论
- `references/whiteboard-summary.md` — 可视化总结白板：先规划（内容结构/风格/构图）再交给 `beautiful-feishu-whiteboard` skill 画（含“写前重取白板 token”“文字必须上浅底”两条踩坑）

# 抓取 YouTube 字幕（SRT）的实战策略

YouTube 对程序化取字幕有强反爬。直连 API 几乎必失败，要按下面的**降级链**逐级尝试，命中即停。

## 为什么直连会失败
- `youtube-transcript-api` / `yt-dlp`：会报 `RequestBlocked`、`Sign in to confirm you're not a bot`、SSL 证书错误——YouTube 按 IP 封杀数据中心出口。
- 官方 timedtext 接口：需要登录态的签名参数，拿不到。

结论：**不要在这上面反复重试**。3 次失败就切下一级。

## 降级链（按顺序）

### 1. 第三方字幕站（首选，成功率最高）
用 remote browser 打开这些站，输入视频 URL，它们服务端帮你取字幕：
- `downsub.com`（首选）—— 输入 `https://downsub.com/?url=<youtube_url>`
- `editsub.com` / `download.subtitle.to`
- `kome.ai`、`youtubetotranscript.com`（常有 Cloudflare 盾，备选）

关键技巧——**下载 blob 直取**：downsub 页面上的 SRT 下载按钮指向一个形如
`https://download.subtitle.to/?title=...&url=<很长的加密 blob>` 的链接。
把这个完整链接用 `curl` 直接拉，就能拿到完整 SRT（HTTP 200）。
不要漏掉 `url=` 后那段加密串，截断会返回 `Invalid URL format`。

从 remote browser 拿到页面 DOM 后，提取 `download.subtitle.to` 开头的 href，再 curl 即可。

### 2. remote browser 直接抓页面文字
若下载 blob 拿不到，用 remote browser 打开 `youtubetotranscript.com/transcript?v=<VIDEO_ID>`
或类似站点，等页面渲染完，直接抓正文文本。缺点：没有精确时间戳，只能得到纯文本段落，
timeline 跳转链接会退化。

### 3. 让用户提供
以上都失败时，直接请用户手动导出字幕文件（YouTube「显示字幕转录」→复制，或用浏览器插件），
把 SRT/文本发给你。不要无限重试自动方案。

## 拿到 SRT 之后
存成 `transcript.srt`，交给 `scripts/parse_srt.py` 解析。SRT 里的说话人换行用 `>>` 标记，
解析脚本据此切分成"说话人 turn"——这是保证段落完整、不把一句话拆两半的关键。

## 提取 video_id
从任意 YouTube URL 提取 11 位 id：`watch?v=<ID>`、`youtu.be/<ID>`、`/shorts/<ID>` 均取那 11 位字符。

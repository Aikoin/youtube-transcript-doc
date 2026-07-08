# youtube-transcript-doc

A [Mira](https://mira.byteintl.net) / Claude **skill** that turns a YouTube video into a polished, readable transcript document — end to end.

**Pipeline:** watch/read a YouTube video → scrape its SRT subtitles (past YouTube's anti-bot blocks) → parse into clean speaker-turn paragraphs → strip filler words & fix ASR errors → translate (e.g. English→Chinese bilingual) → add clickable timestamp jump-links → surface highlight-moment cards → publish to a Feishu/Lark doc → plan & deliver a visual summary whiteboard distilling the key points. The whiteboard is a **mandatory** final deliverable, not optional.

## Why this exists

Auto-generated captions are raw: filler words, stutters, mis-transcribed names, and — worst of all — sentences sliced in half when you merge cues by a fixed time window. This skill encodes the fixes:

- **Speaker-turn segmentation** (`>>` markers) so every paragraph is a complete thought, never a half-sentence.
- **A subtitle-fetch fallback chain** because direct YouTube APIs (`youtube-transcript-api`, `yt-dlp`) get IP-blocked. The reliable path: third-party subtitle sites → the `download.subtitle.to` blob trick → browser scrape → ask the user.
- **Layout rules distilled from real user feedback (v3)**: plain title (no "EN/ZH" or "bilingual" labels), a **plain-paragraph body** — not a wall of cards — with Chinese as the main line and the English original as a gray quote-block beneath only the segments worth showing; callout cards reserved for the few things that deserve emphasis (per-section 重点, top highlights, the head info box); a neutral 🗣️ prefix at speaker switches instead of inventing names; curated highlight cards on top; clickable timestamps throughout.
- **A mandatory visual-summary whiteboard step**: this skill first **plans** the board (content clusters + narrative spine, style mood, composition skeleton), then hands that brief to [beautiful-feishu-whiteboard](https://github.com/zarazhangrui/beautiful-feishu-whiteboard) to draw it — hand-composed SVG, not auto-layout. Two hard-won rules baked in: **Feishu forces whiteboard text dark on render, so all text must sit on light backgrounds** (accents only for borders/bars/markers), verified against the live board render (not the local PNG); and **re-fetch the live `<whiteboard>` token before writing**, since a doc `overwrite` orphans the old board block.

## Layout

```
youtube-transcript-doc/
├── SKILL.md                      # the skill: full workflow (5 transcript steps + a mandatory whiteboard step)
├── scripts/
│   ├── parse_srt.py              # SRT → speaker-turn paragraphs (drops pure filler)
│   └── build_doc.py              # paragraphs + translation → Lark XML fragments
└── references/
    ├── fetch-srt.md              # subtitle-scraping fallback chain (the tricky part)
    ├── clean-translate.md        # cleaning / translation / layout rules
    ├── publish-lark.md           # lark-doc create / append / get-comments
    └── whiteboard-summary.md     # mandatory visual summary board: plan (structure/style/composition) then hand off; text-on-light + live-token pitfalls
```

## Usage

Drop a YouTube link and ask for a transcript / 逐字稿 / timeline / bilingual writeup. The skill triggers automatically. See `SKILL.md` for the step-by-step flow.

## Scripts (standalone)

```bash
# 1. parse subtitles into speaker-turn paragraphs
python scripts/parse_srt.py transcript.srt --video-id VIDEO_ID --out turns.json

# 2. after cleaning+translating into content.json (schema in build_doc.py header),
#    build the Lark doc XML fragments
python scripts/build_doc.py turns.json content.json --outdir frags/
```

## License

MIT

# youtube-transcript-doc

A [Mira](https://mira.byteintl.net) / Claude **skill** that turns a YouTube video into a polished, readable transcript document — end to end.

**Pipeline:** watch/read a YouTube video → scrape its SRT subtitles (past YouTube's anti-bot blocks) → parse into clean speaker-turn paragraphs → strip filler words & fix ASR errors → translate (e.g. English→Chinese bilingual) → add clickable timestamp jump-links → surface highlight-moment cards → publish to a Feishu/Lark doc → *(optional)* hand-compose a visual summary whiteboard distilling the key points.

## Why this exists

Auto-generated captions are raw: filler words, stutters, mis-transcribed names, and — worst of all — sentences sliced in half when you merge cues by a fixed time window. This skill encodes the fixes:

- **Speaker-turn segmentation** (`>>` markers) so every paragraph is a complete thought, never a half-sentence.
- **A subtitle-fetch fallback chain** because direct YouTube APIs (`youtube-transcript-api`, `yt-dlp`) get IP-blocked. The reliable path: third-party subtitle sites → the `download.subtitle.to` blob trick → browser scrape → ask the user.
- **Layout rules distilled from real user feedback**: plain title, color (not "EN/ZH" labels) to distinguish languages, ⭐ markers instead of whole-paragraph highlighting, curated highlight cards on top, clickable timestamps throughout.
- **An optional visual-summary whiteboard step** built on [beautiful-feishu-whiteboard](https://github.com/zarazhangrui/beautiful-feishu-whiteboard) — hand-composed SVG, not auto-layout. Hard-won rule baked in: **Feishu forces whiteboard text dark on render, so all text must sit on light backgrounds** (accents only for borders/bars/markers), and you must verify against the live board render, not the local PNG.

## Layout

```
youtube-transcript-doc/
├── SKILL.md                      # the skill: workflow (5 core steps + optional whiteboard)
├── scripts/
│   ├── parse_srt.py              # SRT → speaker-turn paragraphs (drops pure filler)
│   └── build_doc.py              # paragraphs + translation → Lark XML fragments
└── references/
    ├── fetch-srt.md              # subtitle-scraping fallback chain (the tricky part)
    ├── clean-translate.md        # cleaning / translation / layout rules
    ├── publish-lark.md           # lark-doc create / append / get-comments
    └── whiteboard-summary.md     # optional visual summary board (text-on-light rule + pitfalls)
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

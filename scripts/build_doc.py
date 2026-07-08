#!/usr/bin/env python3
"""
Build lark-doc XML fragments from cleaned/translated turns — v3 plain-text layout.

Why v3 (learned from repeated user feedback): the earlier "two-column callout
card" layout felt cluttered — a wall of cards, each turn boxed twice (EN card +
ZH card). Users compared it to codex's tidier output and asked for a calmer,
document-like read. So v3 renders the BODY as ordinary paragraphs, and reserves
callout cards ONLY for the few things that truly deserve emphasis (section 重点,
top highlights, the head info box).

Input files:
  turns.json  : output of parse_srt.py  -> [{start, ts, link, text}, ...]
  content.json: your cleaned+translated content, keyed by paragraph index:
      {
        "meta": {
            "video_id": "P3KDebPTUrw",   # used to build fallback jump links
            "title": "...",              # doc title (keep it plain, no "bilingual" label)
            "source": "Sequoia ...",     # optional line in the info callout
            "video_url": "https://...",  # optional
            "duration": "44:52",         # optional
            "guests": "..."              # optional
        },
        "sections": [                    # topical grouping, by start-second
            # title bilingual "English / 中文"; summary is the one-line 重点 gist
            {"start": 0,   "title": "Cold Open / 开场", "emoji": "🎬",
             "summary": "一开场就把整期问题框定为：如何把私有上下文学进模型。"},
            {"start": 59,  "title": "Model always training / 模型始终在训练", "emoji": "🧠",
             "summary": "总论点:瓶颈不是原始智力,而是持续吸收并内化上下文。"}
        ],
        "highlights": [                  # editor-picked cards shown at the top
            # sec MUST be the timestamp where the quote ACTUALLY occurs — a
            # highlight must never point at a section where it doesn't appear.
            {"sec": 69, "label": "...", "quote": "..."}
        ],
        "paras": {                       # index-as-string -> a turn's content
            "0": {
                # A turn can hold MULTIPLE speakers (ASR / the ">>" marker often
                # merges a question + its answer into one cue). List each speaker
                # sub-turn in `segs`, in order.
                # SPEAKER-NAME POLICY (important): only put a `speaker` name when
                # the subtitles actually carried speaker labels, or you are truly
                # confident. If the SRT had only ">>" turn markers and no names,
                # who-said-what is a GUESS — do NOT invent names. Leave `speaker`
                # empty; build_doc renders a neutral 🗣️ emoji at each switch so
                # the reader sees a speaker change without us asserting a wrong
                # identity.
                # ENGLISH-ORIGINAL POLICY: `en_keep` is the English original that
                # is worth showing under the Chinese as a gray quote block. Keep
                # it ONLY on substantive / quotable segs; leave "" on routine
                # chatter so the doc isn't doubled top-to-bottom. (Legacy `en`
                # is still accepted as a fallback.)
                "segs": [
                    {"speaker": "", "zh": "...", "en_keep": "..."},
                    {"speaker": "", "zh": "...", "en_keep": ""}
                ],
                "key": true              # true = a substantive turn
            },
            # Back-compat: a single-speaker turn may still use the flat form
            # {"speaker","en"/"en_keep","zh","key"} with no `segs`.
            ...
        },
        "_no_ts_sections": [0]           # section indices that hide ALL timestamps
                                         # (e.g. a Cold Open montage where
                                         # per-sentence timestamps are just noise)
      }

Layout produced (v3, codex-clean, plain-text body):
  - Each topic is an <h2> with its bilingual title.
  - Right under it, a 💡 GREEN callout summary card: (optional clickable
    timestamp) + "重点" + a one-line gist of the section. Only card in the body.
  - Body turns are NORMAL paragraphs — NOT cards. The timestamp link (and ⭐ if
    the turn holds a highlight) sits inline at the head of the first Chinese
    paragraph. Speaker switches inside a turn get a neutral 🗣️ prefix when the
    subtitles gave no name (never invent one); a real name renders as "Name：".
  - The English original renders as a gray <blockquote> beneath the Chinese,
    ONLY for segs whose `en_keep` is non-empty.
  - highlights[] render as ⭐ yellow callout cards at the very top; a turn that
    contains a highlight second also gets a small ⭐ at its head.
  - Sections listed in `_no_ts_sections` hide every timestamp (head + 重点 card).

Usage:
  python build_doc.py turns.json content.json --outdir frags/
  # writes frags/intro.xml and frags/sec_0.xml ... sec_N.xml

Then create + append with lark-doc (see SKILL.md).
"""
import json, html, os, argparse

def esc(t):
    return html.escape(t or "", quote=False)

def hms(s):
    h, m, ss = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{ss:02d}" if h else f"{m}:{ss:02d}"

def seg_en(sg):
    """English original worth showing — prefer en_keep, fall back to legacy en."""
    return (sg.get("en_keep") or sg.get("en") or "").strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("turns")
    ap.add_argument("content")
    ap.add_argument("--outdir", default="frags")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    turns = json.load(open(args.turns))
    c = json.load(open(args.content))
    meta = c.get("meta", {})
    sections = c["sections"]
    highlights = c.get("highlights", [])
    paras = c["paras"]
    no_ts = set(c.get("_no_ts_sections", []))  # sections that hide all timestamps

    def link(sec):
        return f"https://www.youtube.com/watch?v={meta.get('video_id','')}&t={sec}s"
    turn_link = {t["start"]: t.get("link") for t in turns}
    def jump(sec):
        return turn_link.get(sec) or link(sec)

    # map a highlight second -> the turn index containing it (to place the ⭐)
    def turn_for(sec):
        best = 0
        for i, t in enumerate(turns):
            if t["start"] <= sec: best = i
            else: break
        return best
    star_turns = {turn_for(h["sec"]) for h in highlights}

    # assign each turn to a section by start-second
    def sec_for(sec):
        cur = sections[0]
        for s in sections:
            if sec >= s["start"]: cur = s
            else: break
        return cur
    groups = {s["start"]: [] for s in sections}
    for idx, t in enumerate(turns):
        groups[sec_for(t["start"])["start"]].append((idx, t))

    # ---- intro fragment ----
    x = [f'<title>{esc(meta.get("title","逐字稿"))}</title>']
    info = []
    if meta.get("source"):    info.append(f'<p><b>来源</b>:{esc(meta["source"])}</p>')
    if meta.get("video_url"): info.append(f'<p><b>视频</b>:<a href="{meta["video_url"]}">{esc(meta["video_url"])}</a></p>')
    if meta.get("duration"):  info.append(f'<p><b>时长</b>:{esc(meta["duration"])}</p>')
    if meta.get("guests"):    info.append(f'<p><b>嘉宾</b>:{esc(meta["guests"])}</p>')
    if info:
        x.append('<callout emoji="🎙️" background-color="light-blue" border-color="blue">' + "".join(info) + '</callout>')
    x.append('<p><span text-color="gray">以中文译文为主线整理,重要观点附英文原文(引用块)。时间戳可点击跳转视频。下方「高光时刻」为编辑精选核心观点。</span></p>')
    if highlights:
        x.append('<h1>⭐ 高光时刻</h1>')
        for h in highlights:
            x.append(f'<callout emoji="⭐" background-color="light-yellow" border-color="yellow"><p><b>{esc(h["label"])}</b>　<a href="{jump(h["sec"])}">[{hms(h["sec"])}]</a></p><p>{esc(h["quote"])}</p></callout>')
    x.append('<hr/>')
    x.append('<h1>📝 完整逐字稿</h1>')
    open(os.path.join(args.outdir, "intro.xml"), "w").write("\n".join(x))

    # ---- section fragments ----
    for i, s in enumerate(sections):
        hide_ts = i in no_ts
        title = s.get("title", "")
        y = [f'<h2>{s.get("emoji","")} {esc(title)}</h2>']

        # per-section 重点: a green callout, clickable timestamp unless hidden.
        # Green so it reads distinct from the blue info box and yellow highlights.
        if s.get("summary"):
            ts = hms(s["start"])
            if hide_ts:
                y.append(
                    '<callout emoji="💡" background-color="light-green" border-color="green">'
                    f'<p><b>重点</b>　{esc(s["summary"])}</p></callout>'
                )
            else:
                y.append(
                    '<callout emoji="💡" background-color="light-green" border-color="green">'
                    f'<p><a href="{jump(s["start"])}"><b>{ts}</b></a> '
                    f'<b>重点</b>　{esc(s["summary"])}</p></callout>'
                )

        for idx, t in groups[s["start"]]:
            p = paras.get(str(idx), {})
            star = "⭐ " if idx in star_turns else ""
            ts_a = "" if hide_ts else f'<a href="{jump(t["start"])}">[{t["ts"]}]</a>'
            segs = p.get("segs") or [{"speaker": p.get("speaker",""),
                                      "zh": p.get("zh",""),
                                      "en_keep": p.get("en_keep", p.get("en",""))}]

            # Chinese body as plain paragraphs. Timestamp inline at the head of
            # the first non-empty zh paragraph; speaker switches get a neutral
            # 🗣️ prefix when unnamed (never invent a name), or "Name：" when known.
            first = True
            for sg in segs:
                sp = (sg.get("speaker") or "").strip()
                body = (sg.get("zh") or "").strip()
                if not body:
                    continue
                if first:
                    lead = f'{star}{ts_a}　' if ts_a else star
                    if sp: lead += f'<b>{esc(sp)}:</b>'
                    y.append(f'<p>{lead}{esc(body)}</p>')
                    first = False
                else:
                    prefix = f'<b>{esc(sp)}:</b>' if sp else '🗣️ '
                    y.append(f'<p>{prefix}{esc(body)}</p>')

            # English original — ONLY segs whose en_keep is worth showing.
            en_kept = [(sg.get("speaker",""), seg_en(sg))
                       for sg in segs if seg_en(sg)]
            if en_kept:
                bq = []
                for sp, body in en_kept:
                    prefix = f'<b>{esc(sp)}:</b>' if sp else ''
                    bq.append(f'<p><span text-color="gray">{prefix}{esc(body)}</span></p>')
                y.append('<blockquote>' + "".join(bq) + '</blockquote>')

        open(os.path.join(args.outdir, f"sec_{i}.xml"), "w").write("\n".join(y))

    print(f"wrote intro.xml + {len(sections)} section fragments to {args.outdir}/")
    print(f"highlights={len(highlights)} star_turns={sorted(star_turns)} no_ts={sorted(no_ts)}")

if __name__ == "__main__":
    main()

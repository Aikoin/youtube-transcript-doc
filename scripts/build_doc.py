#!/usr/bin/env python3
"""
Build lark-doc XML fragments from cleaned/translated turns.

Input files:
  turns.json  : output of parse_srt.py  -> [{start, ts, link, text}, ...]
  content.json: your cleaned+translated content, keyed by paragraph index:
      {
        "meta": {
            "title": "...",              # doc title (keep it plain, no "bilingual" label)
            "source": "Sequoia ...",     # optional line in the info callout
            "video_url": "https://...",  # optional
            "duration": "44:52",         # optional
            "guests": "..."              # optional
        },
        "sections": [                    # topical grouping, by start-second
            {"start": 0,   "title": "Intro", "emoji": "🎬"},
            {"start": 59,  "title": "...",   "emoji": "🧠"}
        ],
        "highlights": [                  # editor-picked cards shown at the top
            {"sec": 69, "label": "...", "quote": "..."}
        ],
        "paras": {                       # index-as-string -> translated text
            "0": {"en": "cleaned english", "zh": "中文翻译"},
            ...
        },
        "bilingual": true                # true = show en(gray)+zh, false = zh only
      }

Design choices baked in (learned from user feedback):
  - Do NOT print literal "EN"/"ZH" labels. Distinguish languages by color:
    English is gray (a reference/source line), Chinese is default black (primary).
  - Do NOT highlight whole paragraphs. Mark highlight turns with a small ⭐ and
    keep the yellow highlight for the curated cards at the top only. Bold/inline
    highlight is for the human to add later on specific phrases.
  - Every paragraph timestamp is a clickable jump link into the video.

Usage:
  python build_doc.py turns.json content.json --outdir frags/
  # writes frags/intro.xml and frags/sec_0.xml ... sec_N.xml

Then create + append with lark-doc (see SKILL.md).
"""
import json, html, os, argparse

def esc(t):
    return html.escape(t, quote=False)

def hms(s):
    h, m, ss = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{ss:02d}" if h else f"{m}:{ss:02d}"

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
    bilingual = c.get("bilingual", True)

    def link(sec):
        # reuse the link already computed in turns if present, else build
        return f"https://www.youtube.com/watch?v={meta.get('video_id','')}&t={sec}s"
    # prefer per-turn link field
    turn_link = {t["start"]: t.get("link") for t in turns}

    def jump(sec):
        return turn_link.get(sec) or link(sec)

    # map a highlight second -> the turn index containing it (to place the ⭐)
    def turn_for(sec):
        best = 0
        for i, t in enumerate(turns):
            if t["start"] <= sec:
                best = i
            else:
                break
        return best
    star_turns = {turn_for(h["sec"]) for h in highlights}

    # assign each turn to a section by start-second
    def sec_for(sec):
        cur = sections[0]
        for s in sections:
            if sec >= s["start"]:
                cur = s
            else:
                break
        return cur
    groups = {s["start"]: [] for s in sections}
    for idx, t in enumerate(turns):
        groups[sec_for(t["start"])["start"]].append((idx, t))

    # ---- intro fragment ----
    x = [f'<title>{esc(meta.get("title","逐字稿"))}</title>']
    info = []
    if meta.get("source"):   info.append(f'<p><b>来源</b>：{esc(meta["source"])}</p>')
    if meta.get("video_url"):info.append(f'<p><b>视频</b>：<a href="{meta["video_url"]}">{esc(meta["video_url"])}</a></p>')
    if meta.get("duration"): info.append(f'<p><b>时长</b>：{esc(meta["duration"])}</p>')
    if meta.get("guests"):   info.append(f'<p><b>嘉宾</b>：{esc(meta["guests"])}</p>')
    if info:
        x.append('<callout emoji="🎙️" background-color="light-blue" border-color="blue">' + "".join(info) + '</callout>')
    note = "中英对照，" if bilingual else ""
    x.append(f'<p><span text-color="gray">{note}基于视频字幕整理、清洗并翻译。时间戳可点击跳转视频。下方「高光时刻」为编辑精选核心观点。</span></p>')
    if highlights:
        x.append('<h1>⭐ 高光时刻</h1>')
        for h in highlights:
            x.append(f'<callout emoji="⭐" background-color="light-yellow" border-color="yellow"><p><b>{esc(h["label"])}</b>　<a href="{jump(h["sec"])}">[{hms(h["sec"])}]</a></p><p>{esc(h["quote"])}</p></callout>')
    x.append('<hr/>')
    x.append('<h1>📝 完整逐字稿</h1>')
    open(os.path.join(args.outdir, "intro.xml"), "w").write("\n".join(x))

    # ---- section fragments ----
    for i, s in enumerate(sections):
        y = [f'<h2>{s.get("emoji","")} {esc(s["title"])}</h2>']
        for idx, t in groups[s["start"]]:
            p = paras.get(str(idx), {})
            en = (p.get("en") or "").strip()
            zh = (p.get("zh") or "").strip()
            star = "⭐ " if idx in star_turns else ""
            ts_a = f'<a href="{jump(t["start"])}">[{t["ts"]}]</a>'
            if bilingual:
                y.append(f'<p>{star}{ts_a}　<span text-color="gray">{esc(en)}</span></p>')
                if zh:
                    y.append(f'<p>{esc(zh)}</p>')
            else:
                body = zh or en
                y.append(f'<p>{star}{ts_a}　{esc(body)}</p>')
        open(os.path.join(args.outdir, f"sec_{i}.xml"), "w").write("\n".join(y))

    print(f"wrote intro.xml + {len(sections)} section fragments to {args.outdir}/")
    print(f"bilingual={bilingual} highlights={len(highlights)} star_turns={sorted(star_turns)}")

if __name__ == "__main__":
    main()

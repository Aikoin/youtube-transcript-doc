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
            # title is bilingual "English / 中文"; summary is the one-line 重点 gist
            {"start": 0,   "title": "Opening Question / 开场问题", "emoji": "🎬",
             "summary": "一开场就把整期问题框定为：如何把私有上下文学进模型。"},
            {"start": 59,  "title": "Always Training / 模型始终在训练", "emoji": "🧠",
             "summary": "总论点：瓶颈不是原始智力，而是持续吸收并内化上下文。"}
        ],
        "highlights": [                  # editor-picked cards shown at the top
            {"sec": 69, "label": "...", "quote": "..."}
        ],
        "paras": {                       # index-as-string -> a turn's content
            "0": {
                "speaker": "Jessy Lin",  # speaker name shown bold at the head of the turn
                "en": "cleaned english",
                "zh": "中文翻译",
                "key": true              # true = a substantive turn -> bold the body
            },
            ...
        },
        "bilingual": true                # true = EN card + ZH card grid; false = ZH only
      }

Layout produced (learned from a well-received reference transcript):
  - Each topic is an <h2> with a BILINGUAL "English / 中文" title.
  - Right under it, a 💡 callout summary card: a clickable timestamp (bold MM:SS,
    jumps into the video) + "重点：" + a one-line gist of the section.
  - Each speaker turn renders as a 2-COLUMN <grid>: left = English inside a 💡
    callout card, right = Chinese inside a 🈶 callout card. This "card" layout is
    what makes the long transcript skimmable instead of a wall of <p>.
  - Every turn is prefixed with the SPEAKER NAME in bold ("Jessy Lin: ...").
  - SUBSTANTIVE turns are bolded (key=true) so the eye lands on the real answers;
    framing / setup questions stay unbolded. Bold whole answer turns, not phrases.
  - highlights[] still render as ⭐ yellow cards at the very top; a section turn
    that contains a highlight second also gets a small ⭐ before its timestamp.
  - Monolingual (bilingual=false): a single 💡 callout card per turn, ZH only.

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
        return f"https://www.youtube.com/watch?v={meta.get('video_id','')}&t={sec}s"
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

    def speaker_prefix(sp):
        return f'{esc(sp)}：' if sp else ''

    def turn_body(text, sp, key):
        """One line of body text: bold speaker + (bold body if key else plain)."""
        sp_html = f'<b>{esc(sp)}：</b>' if sp else ''
        body = esc(text)
        if key:
            return f'<p>{sp_html}<b>{body}</b></p>'
        # even when not a key turn, keep the speaker name bold for scanability
        return f'<p>{sp_html}{body}</p>'

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
        title = s.get("title", "")
        y = [f'<h2>{s.get("emoji","")} {esc(title)}</h2>']

        # per-section summary callout: clickable timestamp + 重点 one-liner
        if s.get("summary"):
            ts = hms(s["start"])
            y.append(
                '<callout emoji="💡">'
                f'<p><a href="{jump(s["start"])}"><b>{ts}</b></a> '
                f'<b>重点：</b> {esc(s["summary"])}</p></callout>'
            )

        for idx, t in groups[s["start"]]:
            p = paras.get(str(idx), {})
            en = (p.get("en") or "").strip()
            zh = (p.get("zh") or "").strip()
            sp = (p.get("speaker") or "").strip()
            key = bool(p.get("key"))
            star = "⭐ " if idx in star_turns else ""
            ts_a = f'<a href="{jump(t["start"])}">[{t["ts"]}]</a>'

            if bilingual:
                en_body = turn_body(en, sp, key)
                zh_body = turn_body(zh, sp, key) if zh else ""
                # 2-column grid of callout cards: EN (💡) | ZH (🈶).
                # Plain callouts (no background/border) render cleanest; the emoji
                # alone distinguishes the two languages. Valid callout fills are
                # only `gray` / `light-{color}` / `medium-{color}` — don't invent others.
                y.append(
                    '<grid>'
                    '<column width-ratio="0.5">'
                    '<callout emoji="💡">'
                    f'<p>{star}{ts_a}</p>{en_body}</callout>'
                    '</column>'
                    '<column width-ratio="0.5">'
                    '<callout emoji="🈶">'
                    f'{zh_body or "<p></p>"}</callout>'
                    '</column>'
                    '</grid>'
                )
            else:
                text = zh or en
                body = turn_body(text, sp, key)
                y.append(
                    '<callout emoji="💡">'
                    f'<p>{star}{ts_a}</p>{body}</callout>'
                )
        open(os.path.join(args.outdir, f"sec_{i}.xml"), "w").write("\n".join(y))

    print(f"wrote intro.xml + {len(sections)} section fragments to {args.outdir}/")
    print(f"bilingual={bilingual} highlights={len(highlights)} star_turns={sorted(star_turns)}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Parse an SRT subtitle file into speaker-turn paragraphs.

Why speaker turns instead of fixed time-chunks:
  Auto-generated YouTube captions arrive as ~2-second cues. If you merge them
  by a fixed window (e.g. every 45s) you routinely slice a sentence in half,
  which produces the classic "one thought split across two paragraphs" bug.
  Most transcripts mark a change of speaker with a ">>" token; splitting on
  that gives each paragraph a complete thought and clean boundaries.

Also drops paragraphs that are pure filler ("Um,", "Yeah.", "Y") so they don't
become their own standalone blocks in the final doc.

Usage:
  python parse_srt.py transcript.srt --video-id VIDEO_ID --out turns.json
  # optional: --keep-filler to disable filler removal

Output JSON: list of {start, ts, link, text}
  start : int seconds
  ts    : "M:SS" or "H:MM:SS"
  link  : YouTube deep link that jumps to that second
  text  : cleaned English text of the turn
"""
import re, json, argparse

def parse_cues(raw):
    cues = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        m = re.search(r"(\d\d):(\d\d):(\d\d)[,.]\d+", lines[1])
        if not m:
            continue
        start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        text = " ".join(l.strip() for l in lines[2:]).strip()
        cues.append((start, text))
    return cues

def to_turns(cues):
    """Group cues into speaker turns using the '>>' marker."""
    turns, cur = [], None
    for s, t in cues:
        if t.strip().startswith(">>"):
            if cur:
                turns.append(cur)
            cur = {"start": s, "text": t}
        else:
            if cur is None:
                cur = {"start": s, "text": t}
            else:
                cur["text"] += " " + t
    if cur:
        turns.append(cur)
    return turns

def to_timechunks(cues, chunk):
    """Fallback when the transcript has no '>>' speaker markers."""
    turns, cur = [], None
    for s, t in cues:
        if cur is None:
            cur = {"start": s, "text": t}
        elif s - cur["start"] >= chunk:
            turns.append(cur)
            cur = {"start": s, "text": t}
        else:
            cur["text"] += " " + t
    if cur:
        turns.append(cur)
    return turns

def clean(t):
    t = t.replace(">>", "").strip()
    t = re.sub(r"\[music\]", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    return t

FILLERS = {"um","uh","y","yeah","yes","okay","ok","right","mhm","hmm","so","well","and","uhhuh","mm"}

def is_pure_filler(t):
    s = re.sub(r"\[laughter\]", "", t, flags=re.I)
    s = re.sub(r"[^a-zA-Z ]", "", s).strip().lower()
    toks = s.split()
    return (len(toks) > 0 and all(w in FILLERS for w in toks)) or s == ""

def fmt(sec):
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--out", default="turns.json")
    ap.add_argument("--chunk", type=int, default=45, help="fallback seconds/para when no >> markers")
    ap.add_argument("--keep-filler", action="store_true")
    args = ap.parse_args()

    raw = open(args.srt, encoding="utf-8").read()
    cues = parse_cues(raw)
    n_speaker = sum(1 for _, t in cues if t.strip().startswith(">>"))
    turns = to_turns(cues) if n_speaker >= 3 else to_timechunks(cues, args.chunk)

    out = []
    for tn in turns:
        txt = clean(tn["text"])
        if not txt:
            continue
        if not args.keep_filler and is_pure_filler(txt):
            continue
        sec = tn["start"]
        out.append({
            "start": sec,
            "ts": fmt(sec),
            "link": f"https://www.youtube.com/watch?v={args.video_id}&t={sec}s",
            "text": txt,
        })
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    mode = "speaker-turns" if n_speaker >= 3 else f"time-chunks({args.chunk}s)"
    print(f"cues={len(cues)} mode={mode} paragraphs={len(out)} -> {args.out}")
    if out:
        print(f"duration≈{fmt(cues[-1][0])}")

if __name__ == "__main__":
    main()

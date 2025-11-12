#!/usr/bin/env python3
# 04_time_fit_and_concat.py
# Build a single VO track aligned to the absolute SRT timeline.
# Requires ffmpeg/ffprobe in PATH. No extra Python deps.

import argparse, pathlib, re, subprocess, sys, tempfile, math, glob, json

TIME_RE = re.compile(r"(\d+):(\d+):(\d+),(\d+)")

def to_seconds(ts: str) -> float:
    m = TIME_RE.match(ts.strip())
    if not m: raise ValueError(f"Bad SRT timestamp: {ts}")
    h, mnt, s, ms = map(int, m.groups())
    return h*3600 + mnt*60 + s + ms/1000.0

def read_srt(p: pathlib.Path):
    blocks, cur, buf = [], None, []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip()=="":
            if cur:
                text = "\n".join(buf).strip()
                blocks.append((cur[0], cur[1], text))
                cur, buf = None, []
            continue
        if cur is None and line.strip().isdigit():
            cur = [line.strip(), None]
            continue
        if cur and cur[1] is None and "-->" in line:
            start, end = [x.strip() for x in line.split("-->")]
            cur[1] = (start, end)
            continue
        buf.append(line)
    if cur:
        text = "\n".join(buf).strip()
        blocks.append((cur[0], cur[1], text))
    # normalize to (i, start_sec, end_sec, text)
    out = []
    for idx, (start, end), text in blocks:
        out.append((int(idx), to_seconds(start), to_seconds(end), text))
    return out

def sh(cmd, quiet=False):
    if not quiet:
        print(">>", " ".join(cmd), file=sys.stderr)
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr}")
    return p

def ffprobe_duration(path: pathlib.Path) -> float:
    cmd = ["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(path)]
    out = sh(cmd, quiet=True).stdout
    return float(json.loads(out)["format"]["duration"])

def make_silence(out: pathlib.Path, dur: float, sr: int, ch: int):
    dur = max(0.0, dur)
    if dur <= 0: 
        # still generate a 1 ms tick to keep concat stable (will be trimmed later)
        dur = 0.001
    sh([
        "ffmpeg","-v","error","-f","lavfi",
        "-i", f"anullsrc=r={sr}:cl={'mono' if ch==1 else 'stereo'}",
        "-t", f"{dur:.6f}",
        "-ar", str(sr), "-ac", str(ch),
        "-y", str(out)
    ], quiet=True)

def trim_lead_trail_silence(inp: pathlib.Path, out: pathlib.Path, sr: int, ch: int):
    # Common & robust pattern: remove leading silence, reverse, remove again, reverse back.
    # Threshold mildly conservative to keep breaths: -35dB
    af = "silenceremove=start_periods=1:start_duration=0:start_threshold=-35dB," \
         "areverse," \
         "silenceremove=start_periods=1:start_duration=0:start_threshold=-35dB," \
         "areverse"
    sh([
        "ffmpeg","-v","error","-i", str(inp),
        "-af", af, "-ar", str(sr), "-ac", str(ch),
        "-y", str(out)
    ], quiet=True)

def atempo_chain(factor: float) -> str:
    # Build a safe atempo chain (each link 0.5..2.0)
    if factor <= 0: factor = 1.0
    chain = []
    # Split into chunks to keep each between 0.5 and 2.0
    while factor < 0.5:
        chain.append(0.5)
        factor /= 0.5
    while factor > 2.0:
        chain.append(2.0)
        factor /= 2.0
    chain.append(factor)
    return ",".join(f"atempo={x:.6f}" for x in chain)

def stretch_to_duration(inp: pathlib.Path, out: pathlib.Path, target_sec: float, sr: int, ch: int):
    # Guard for tiny/zero durations
    target_sec = max(0.001, target_sec)
    src_dur = max(0.001, ffprobe_duration(inp))
    tempo = target_sec / src_dur
    chain = atempo_chain(tempo)
    # Pad a hair, then hard trim to exact duration for sample-accurate length
    af = f"{chain},apad=whole_dur={target_sec:.6f},atrim=end={target_sec:.6f}"
    sh([
        "ffmpeg","-v","error","-i", str(inp),
        "-af", af, "-ar", str(sr), "-ac", str(ch),
        "-y", str(out)
    ], quiet=True)

def find_tts_file(i: int, tts_dir: pathlib.Path):
    # Accept files like 00001.wav or 00001_line.wav
    patterns = [
        tts_dir / f"{i:05d}.wav",
        tts_dir / f"{i:05d}_*.wav",
        tts_dir / f"{i:05d}.mp3",
        tts_dir / f"{i:05d}_*.mp3",
    ]
    for pat in patterns:
        if "*" in str(pat):
            matches = sorted(glob.glob(str(pat)))
            if matches:
                return pathlib.Path(matches[0])
        else:
            if pat.exists(): return pat
    return None

def build_concat(concat_list, out_wav: pathlib.Path, sr: int, ch: int):
    with tempfile.TemporaryDirectory() as td:
        concat_txt = pathlib.Path(td) / "concat.txt"
        concat_txt.write_text("".join(f"file '{str(p.resolve())}'\n" for p in concat_list), encoding="utf-8")
        sh([
            "ffmpeg","-v","error",
            "-f","concat","-safe","0","-i", str(concat_txt),
            "-ar", str(sr), "-ac", str(ch),
            "-c:a","pcm_s16le",  # keep lossless for downstream mix
            "-y", str(out_wav)
        ], quiet=False)

def main():
    ap = argparse.ArgumentParser(description="Fit per-line TTS to SRT windows and place on absolute timeline.")
    ap.add_argument("--srt", required=True, type=pathlib.Path)
    ap.add_argument("--tts-dir", required=True, type=pathlib.Path, help="Directory containing 00001_*.wav ...")
    ap.add_argument("--out", required=True, type=pathlib.Path, help="Output WAV path for the full VO")
    ap.add_argument("--workdir", type=pathlib.Path, default=None, help="Optional work dir for intermediates")
    ap.add_argument("--sr", type=int, default=48000)
    ap.add_argument("--ch", type=int, default=1)
    ap.add_argument("--total-duration", type=float, default=None, help="Optional final target length (sec) to pad tail")
    args = ap.parse_args()

    srt_blocks = read_srt(args.srt)
    if not srt_blocks:
        print("SRT appears empty.", file=sys.stderr); sys.exit(1)

    work = args.workdir or args.out.parent / "tts_fit"
    work.mkdir(parents=True, exist_ok=True)

    segments = []
    sr, ch = args.sr, args.ch

    # 1) Leading silence up to first cue
    first_start = srt_blocks[0][1]
    lead = work / "00000_lead.wav"
    if first_start > 0.0005:
        make_silence(lead, first_start, sr, ch)
        segments.append(lead)

    # 2) For each cue: fit TTS (or silence) to (end-start), and add gap after it
    prev_end = 0.0
    for idx, start, end, text in srt_blocks:
        dur = max(0.0, end - start)
        # Gap from previous end to this start (if any)
        gap = max(0.0, start - prev_end)
        if gap > 0.0005:
            gap_wav = work / f"{idx:05d}_gap_before.wav"
            make_silence(gap_wav, gap, sr, ch)
            segments.append(gap_wav)

        tts_in = find_tts_file(idx, args.tts_dir)
        target = work / f"{idx:05d}_fitted.wav"

        if tts_in and dur > 0:
            # Trim head/tail silence, then time-fit
            trimmed = work / f"{idx:05d}_trim.wav"
            try:
                trim_lead_trail_silence(tts_in, trimmed, sr, ch)
                # If trimming nuked everything (rare), fall back to original
                if ffprobe_duration(trimmed) <= 0.005:
                    trimmed = tts_in
            except Exception:
                trimmed = tts_in  # be resilient

            try:
                stretch_to_duration(trimmed, target, dur, sr, ch)
            except Exception:
                # Last resort: generate silence for this cue
                make_silence(target, dur, sr, ch)
        else:
            # Missing/empty cue → silence keeps alignment intact
            make_silence(target, dur, sr, ch)

        segments.append(target)
        prev_end = end

    # 3) Optional tail padding to reach total-duration
    if args.total_duration is not None and args.total_duration > prev_end:
        tail = work / f"{len(srt_blocks)+1:05d}_tail.wav"
        make_silence(tail, args.total_duration - prev_end, sr, ch)
        segments.append(tail)

    # 4) Concatenate losslessly
    build_concat(segments, args.out, sr, ch)
    print(f"Done. VO written to: {args.out}")

if __name__ == "__main__":
    main()

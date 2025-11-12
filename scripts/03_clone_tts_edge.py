#!/usr/bin/env python3
"""
German TTS with speaker cloning via Coqui XTTS v2.

Inputs:
  --srt_de <path>           # German SRT with timestamps & text
  --out_segments_dir <dir>  # Output dir for per-line wavs (00001.wav, ...)
  --voice_ref <path>        # Reference wav of original speaker (e.g., clone_ref.wav)
  --model <name>            # Optional; default: xtts_v2
Outputs:
  - <out_segments_dir>/00001.wav, 00002.wav, ...
  - <out_segments_dir>/tts_report.json (cloned: true/false, reason)
Notes:
  - If cloning fails, falls back to a generic German voice and records it in report.
"""
import argparse, json, pathlib, re, wave, contextlib, sys

def read_srt(p):
    """Return list of (index, ts, text)."""
    blocks, cur, buf = [], None, []
    for line in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        if line.strip()=="":
            if cur: blocks.append((cur[0],cur[1],"\n".join(buf).strip())); cur=None; buf=[]
            continue
        if cur is None and re.match(r"^\d+$", line.strip()): cur=[line.strip(), None]; continue
        if cur and cur[1] is None and "-->" in line: cur[1]=line.strip(); continue
        buf.append(line)
    if cur: blocks.append((cur[0],cur[1],"\n".join(buf).strip()))
    return blocks

def dur_seconds(wav_path):
    try:
        with contextlib.closing(wave.open(str(wav_path), "rb")) as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0

def sanitize_text(t):
    return " ".join(t.replace("\n", " ").split())

def load_tts(model_name):
    # Workaround for PyTorch 2.6+ weights_only default change
    import torch
    if hasattr(torch, 'serialization'):
        try:
            from TTS.tts.configs.xtts_config import XttsConfig
            torch.serialization.add_safe_globals([XttsConfig])
        except:
            pass
    
    from TTS.api import TTS
    return TTS(model_name)

def synth_xtts(tts, text, out_file, speaker_wav, lang="de"):
    # XTTS v2 API: pass speaker_wav and language for cloning
    tts.tts_to_file(text=text, speaker_wav=str(speaker_wav), language=lang, file_path=str(out_file))

def synth_generic(tts_generic, text, out_file):
    # Small, fast German single-speaker fallback (Thorsten)
    tts_generic.tts_to_file(text=text, file_path=str(out_file))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt_de", required=True)
    ap.add_argument("--out_segments_dir", required=True)
    ap.add_argument("--voice_ref", required=True)
    ap.add_argument("--model", default="tts_models/multilingual/multi-dataset/xtts_v2")
    ap.add_argument("--fallback_model", default="tts_models/de/thorsten/vits")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_segments_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "tts_report.json"
    report = {"model": args.model, "fallback_model": args.fallback_model,
              "cloned": False, "reason": "", "segments": []}

    # Basic checks on reference audio
    ref = pathlib.Path(args.voice_ref)
    if not ref.exists():
        report["reason"] = f"voice_ref not found: {ref}"
        # We'll try generic immediately below
    elif dur_seconds(ref) < 3.0:
        report["reason"] = "voice_ref too short (<3s); cloning skipped"

    blocks = read_srt(args.srt_de)
    blocks = [(i, ts, sanitize_text(txt)) for i,ts,txt in blocks if sanitize_text(txt)]

    # Try XTTS cloning first iff ref is valid
    tts_clone = tts_generic = None
    cloning_available = ref.exists() and dur_seconds(ref) >= 3.0

    try:
        if cloning_available:
            tts_clone = load_tts(args.model)  # first run downloads weights
    except Exception as e:
        cloning_available = False
        report["reason"] = f"failed to init XTTS: {e.__class__.__name__}"
        print(f"[DEBUG] XTTS init error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    # Prepare generic fallback ahead of time
    try:
        tts_generic = load_tts(args.fallback_model)
    except Exception as e:
        # We still proceed; if both fail, we'll error out later per segment
        report.setdefault("warnings", []).append(f"failed to init fallback: {e.__class__.__name__}")
        print(f"[DEBUG] Fallback init error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    used_clone_success = False
    for idx,(i,_,txt) in enumerate(blocks, start=1):
        out_wav = out_dir / f"{idx:05d}.wav"
        ok = False
        # Try cloning
        if cloning_available and tts_clone:
            try:
                synth_xtts(tts_clone, txt, out_wav, ref, lang="de")
                ok = True
                used_clone_success = True
                src = "clone"
            except Exception as e:
                src = f"clone_error:{e.__class__.__name__}"
        else:
            src = "clone_unavailable"

        # Fallback to generic German voice
        if not ok:
            if tts_generic:
                try:
                    synth_generic(tts_generic, txt, out_wav)
                    ok = True
                except Exception as e:
                    src = f"generic_error:{e.__class__.__name__}"
            else:
                src = "generic_unavailable"

        report["segments"].append({"i": idx, "text": txt, "ok": ok, "source": src})

        if not ok:
            print(f"[WARN] Segment {idx}: TTS failed ({src}).", file=sys.stderr)

    report["cloned"] = bool(used_clone_success)
    if not report["cloned"]:
        if not report["reason"]:
            report["reason"] = "XTTS cloning not used or failed; generic German voice used."

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if report["cloned"]:
        print("OK: TTS generated with speaker cloning (XTTS v2).")
    else:
        print("DONE with fallback: original voice could NOT be cloned. See tts_report.json for details.")

if __name__ == "__main__":
    main()

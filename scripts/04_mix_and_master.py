#!/usr/bin/env python3
"""
Mix & master:
- If the original track is speech-only (no bed), OUTPUT = German VO only (loudnorm @ -16 LUFS).
- Otherwise, gate the source to -inf whenever VO is present (no EN bleed), keep bed subtle, loudnorm.
"""
import argparse, pathlib, subprocess
import numpy as np
import soundfile as sf

def run(cmd): subprocess.run(cmd, check=True)

def background_score_mono(path, speech_low=150, speech_high=5000):
    """Heuristic: proportion of energy OUTSIDE the speech band.
       If very low, the track is mostly voice (no real background)."""
    x, sr = sf.read(path, always_2d=False)
    if x.ndim > 1: x = np.mean(x, axis=1)
    if len(x) == 0: return 0.0
    n = 1 << (int(np.ceil(np.log2(len(x)))) )  # zero-pad FFT
    X = np.fft.rfft(x, n=n)
    freqs = np.fft.rfftfreq(n, d=1.0/sr)
    total = np.sum(np.abs(X)**2) + 1e-12
    mask_ns = (freqs < speech_low) | (freqs > speech_high)
    non_speech = np.sum((np.abs(X[mask_ns])**2))
    return float(non_speech / total)

def loudnorm_inplace(in_wav, out_wav):
    run([
        "ffmpeg","-y","-i",in_wav,
        "-af","loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar","48000", out_wav
    ])

def mix_with_gate(src_bed_wav, de_vo_wav, out_wav):
    """
    Gate the source bed to -inf whenever VO is active (no English bleed),
    keep any bed that remains very low, then loudnorm.
    """
    pathlib.Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
    fc = (
      # Normalize formats
      "[0:a]aformat=channel_layouts=mono,volume=1.0[bed];"
      "[1:a]aformat=channel_layouts=mono,volume=1.0[vo];"
      # High-pass the sidechain detector at 120 Hz to avoid low rumbles triggering the gate
      "[vo]highpass=f=120[vo_sc];"
      # Hard gate: when VO sidechain crosses threshold, reduce bed to near silence (range=1 means full reduction)
      # Tighter release (90ms) for snappier entrances, makeup=0 keeps bed floor low
      "[bed][vo_sc]sidechaingate=threshold=0.015:range=1:attack=5:release=90[bedg];"
      # Keep any residual bed subtle even when gate is open (~ -14 dB)
      "[bedg]volume=0.2[bedshy];"
      # Mix and loudness normalize
      "[bedshy][vo]amix=inputs=2:duration=first:dropout_transition=0[mix];"
      "[mix]loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    run(["ffmpeg","-y","-i",src_bed_wav,"-i",de_vo_wav,"-filter_complex",fc,"-ar","48000", out_wav])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src_audio", required=True)   # data/work/src_full.wav
    ap.add_argument("--de_audio", required=True)    # data/work/de_voice.wav
    ap.add_argument("--out_mix", required=True)     # data/work/de_mix.wav (not mp4)
    ap.add_argument("--no_bed_threshold", type=float, default=0.04,
                    help="If background_score < threshold => treat as speech-only (mute src).")
    args = ap.parse_args()

    score = background_score_mono(args.src_audio)
    # If mostly speech (very little non-speech energy), drop the source entirely.
    if score < args.no_bed_threshold:
        loudnorm_inplace(args.de_audio, args.out_mix)
        print(f"OK: Detected no real background (score={score:.4f}). Used VO only.")
    else:
        mix_with_gate(args.src_audio, args.de_audio, args.out_mix)
        print(f"OK: Mixed with hard gate (score={score:.4f}).")

if __name__ == "__main__":
    main()

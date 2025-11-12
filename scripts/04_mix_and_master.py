#!/usr/bin/env python3
"""
Mix & master:
- Mix instrumental background music with German voice-over
- If the instrumental track has no real music content, OUTPUT = German VO only (loudnorm @ -16 LUFS).
- Otherwise, duck the instrumental whenever VO is present, keep music subtle, loudnorm.
"""
import argparse, pathlib, subprocess
import numpy as np
import soundfile as sf

def run(cmd): subprocess.run(cmd, check=True)

def background_score_mono(path, speech_low=150, speech_high=5000):
    """Heuristic: proportion of energy OUTSIDE the speech band.
       If very low, the track has no real music/background content."""
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
    """Apply loudness normalization to a single audio file."""
    pathlib.Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg","-y","-i",in_wav,
        "-af","loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar","48000", out_wav
    ])

def mix_instrumental_with_voice(instrumental_wav, voice_wav, out_wav):
    """
    Mix instrumental background music with German voice-over.
    Duck the instrumental whenever voice is active using sidechaincompress,
    keep music subtle in the background, then loudness normalize.
    """
    pathlib.Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
    fc = (
      # Convert instrumental to mono and boost volume VERY significantly (instrumental is extremely quiet)
      "[0:a]pan=mono|c0=0.5*c0+0.5*c1,volume=15.0[music];"
      # Keep voice at normal level and split for sidechain
      "[1:a]asplit=2[voice][voice_sc];"
      # Duck the music when voice is present using sidechaincompress
      # threshold=0.03 (-30dB), ratio=3:1 for gentle ducking, attack=5ms, release=300ms
      "[music][voice_sc]sidechaincompress=threshold=0.03:ratio=3:attack=5:release=300[music_ducked];"
      # Mix voice (foreground) with ducked music (background) - voice still gets priority
      "[voice][music_ducked]amix=inputs=2:duration=longest:weights=3 2[premix];"
      # Loudness normalize the final mix
      "[premix]loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    run(["ffmpeg","-y","-i",instrumental_wav,"-i",voice_wav,"-filter_complex",fc,"-ar","48000", out_wav])

def simple_mix(instrumental_wav, voice_wav, out_wav):
    """
    Simple mix without ducking - for testing/debugging.
    Boost the quiet instrumental, keep voice at normal level.
    """
    pathlib.Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
    fc = (
      # Convert instrumental stereo to mono and boost volume significantly (instrumental is very quiet)
      "[0:a]pan=mono|c0=0.5*c0+0.5*c1,volume=6.0[music];"
      # Keep voice at normal level
      "[1:a]volume=1.0[voice];"
      # Mix with voice getting more weight
      "[music][voice]amix=inputs=2:duration=longest:weights=1 2[premix];"
      "[premix]loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    run(["ffmpeg","-y","-i",instrumental_wav,"-i",voice_wav,"-filter_complex",fc,"-ar","48000", out_wav])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src_audio", required=True, help="Instrumental background music (e.g., data/work/src_instrumental.wav)")
    ap.add_argument("--de_audio", required=True, help="German voice-over (e.g., data/work/de_voice.wav)")
    ap.add_argument("--out_mix", required=True, help="Output mixed audio (e.g., data/work/de_mix.wav)")
    ap.add_argument("--no_music_threshold", type=float, default=0.04,
                    help="If background_score < threshold => treat instrumental as empty (use voice only).")
    ap.add_argument("--simple_mix", action="store_true",
                    help="Use simple mixing without ducking (for testing)")
    args = ap.parse_args()

    # Check if instrumental track has actual music content
    score = background_score_mono(args.src_audio)
    
    # If instrumental has no real music content, output voice only
    if score < args.no_music_threshold:
        loudnorm_inplace(args.de_audio, args.out_mix)
        print(f"OK: No music detected in instrumental (score={score:.4f}). Output is voice-only.")
    else:
        # Mix instrumental background with German voice-over
        if args.simple_mix:
            simple_mix(args.src_audio, args.de_audio, args.out_mix)
            print(f"OK: Simple mix (no ducking) - instrumental with voice (score={score:.4f}).")
        else:
            mix_instrumental_with_voice(args.src_audio, args.de_audio, args.out_mix)
            print(f"OK: Mixed instrumental with voice + ducking (score={score:.4f}).")

if __name__ == "__main__":
    main()

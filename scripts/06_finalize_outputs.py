#!/usr/bin/env python3
import argparse, pathlib, shutil

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--video", required=True)      # data/input/Tanzania-2.mp4
    ap.add_argument("--mix_wav", required=True)    # data/work/de_mix.wav
    ap.add_argument("--srt_de", required=True)     # data/work/Tanzania-caption.de.srt
    ap.add_argument("--out_dir", required=True)    # data/output
    args=ap.parse_args()

    out_dir = pathlib.Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    base = pathlib.Path(args.video).stem
    out_mp4 = out_dir/f"{base}.de.mp4"
    out_wav = out_dir/f"{base}.de.wav"
    out_srt = out_dir/f"{base}.de.srt"

    # 05: mux - call ffmpeg directly instead of shell script
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-i", args.video, "-i", args.mix_wav,
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(out_mp4)
    ], check=True)

    shutil.copy2(args.mix_wav, out_wav)
    shutil.copy2(args.srt_de, out_srt)
    print("OK: outputs ->", out_mp4, out_wav, out_srt)

if __name__=="__main__":
    main()

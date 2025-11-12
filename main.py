#!/usr/bin/env python3
import argparse, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
INP = DATA / "input"
WRK = DATA / "work"
OUT = DATA / "output"

def run(cmd): subprocess.run([sys.executable] + [str(c) for c in cmd], check=True)

def main():
    ap = argparse.ArgumentParser(description="EN->DE dubbing MVP pipeline")
    ap.add_argument("--video", required=True, help="Input video file path")
    ap.add_argument("--transcript", required=True, help="Input transcript file path (.srt or .txt)")
    args = ap.parse_args()

    WRK.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)

    # Derive base name from video file
    video_stem = pathlib.Path(args.video).stem
    
    src_full = WRK/"src_full.wav"
    clone_ref = WRK/"clone_ref.wav"
    # 01 extract audio
    run([SCRIPTS/"01_extract_audio.py","--video",args.video,"--out_wav",src_full,"--clone_ref",clone_ref])

    # 02 timestamps: use given SRT or force-align TXT
    transcript = pathlib.Path(args.transcript)
    if transcript.suffix.lower()==".srt":
        en_srt = transcript
    else:
        en_srt = WRK/"segments_en.srt"
        run([SCRIPTS/"02_force_align.py","--audio",src_full,"--text",args.transcript,"--out_srt",en_srt])

    # 02b translate EN->DE SRT
    de_srt = WRK/f"{video_stem}.de.srt"
    run([SCRIPTS/"02_translate_srt.py","--in_srt_en",en_srt,"--out_srt_de",de_srt])

    # 03 synth segments (German), style-clone best-effort
    seg_dir = WRK/"tts_segments_edge"
    run([SCRIPTS/"03_clone_tts_edge.py","--srt_de",de_srt,"--out_segments_dir",seg_dir,"--voice_ref",clone_ref])

    # 04 fit + concat
    fit_dir = WRK/"tts_fit"
    de_voice = WRK/"de_voice.wav"
    run([SCRIPTS/"04_time_fit_and_concat.py","--srt",de_srt,"--tts-dir",seg_dir,
         "--workdir",fit_dir,"--out",de_voice])

    # 04b mix & master with original bed
    de_mix = WRK/"de_mix.wav"
    run([SCRIPTS/"04_mix_and_master.py","--src_audio",src_full,"--de_audio",de_voice,"--out_mix",de_mix])

    # 06 finalize (mux, copy artifacts)
    run([SCRIPTS/"06_finalize_outputs.py","--video",args.video,"--mix_wav",de_mix,
         "--srt_de",de_srt,"--out_dir",OUT])

    print("Pipeline complete ✅")

if __name__ == "__main__":
    main()

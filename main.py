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
    ap = argparse.ArgumentParser(description="EN->DE dubbing pipeline with TTS and voice cloning")
    ap.add_argument("--video", required=True, help="Input video file path")
    ap.add_argument("--transcript", required=True, help="Input transcript file path (.srt or .txt)")
    args = ap.parse_args()

    WRK.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)

    # Derive base name from video file
    video_stem = pathlib.Path(args.video).stem
    
    src_full = WRK/"src_full.wav"
    src_vocals = WRK/"src_vocals.wav"
    clone_ref = WRK/"clone_ref.wav"
    src_instrumental = WRK/"src_instrumental.wav"
    
    print("=" * 60)
    print("Step 1: Extract audio from video")
    print("=" * 60)
    run([SCRIPTS/"01_extract_audio.py","--video",args.video,"--out_wav",src_full])
    
    print("\n" + "=" * 60)
    print("Step 1b: Extract vocals and create clone reference")
    print("=" * 60)
    run([SCRIPTS/"01b_extract_vocal.py","--input",src_full,"--out_vocals",src_vocals,"--clone_ref",clone_ref])
    
    print("\n" + "=" * 60)
    print("Step 1c: Extract background music")
    print("=" * 60)
    run([SCRIPTS/"01b_extract_background.py","--input",src_full,"--out_instrumental",src_instrumental])

    # 02 timestamps: use given SRT or force-align TXT
    transcript = pathlib.Path(args.transcript)
    if transcript.suffix.lower()==".srt":
        en_srt = transcript
        print("\n" + "=" * 60)
        print("Step 2: Using provided SRT file")
        print("=" * 60)
    else:
        en_srt = WRK/"segments_en.srt"
        print("\n" + "=" * 60)
        print("Step 2: Force-align text transcript")
        print("=" * 60)
        run([SCRIPTS/"02_force_align.py","--audio",src_full,"--text",args.transcript,"--out_srt",en_srt])

    # 02b translate EN->DE SRT
    de_srt = WRK/f"{video_stem}.de.srt"
    print("\n" + "=" * 60)
    print("Step 2b: Translate EN->DE")
    print("=" * 60)
    run([SCRIPTS/"02_translate_srt.py","--in_srt_en",en_srt,"--out_srt_de",de_srt])

    # 03 synth segments (German), style-clone best-effort
    seg_dir = WRK/"tts_segments_edge"
    print("\n" + "=" * 60)
    print("Step 3: Generate German TTS with voice cloning")
    print("=" * 60)
    run([SCRIPTS/"03_clone_tts_edge.py","--srt_de",de_srt,"--out_segments_dir",seg_dir,"--voice_ref",clone_ref])

    # 04 fit + concat
    fit_dir = WRK/"tts_fit"
    de_voice = WRK/"de_voice.wav"
    print("\n" + "=" * 60)
    print("Step 4: Time-fit and concatenate TTS segments")
    print("=" * 60)
    run([SCRIPTS/"04_time_fit_and_concat.py","--srt",de_srt,"--tts-dir",seg_dir,
         "--workdir",fit_dir,"--out",de_voice])

    # 04b mix & master with instrumental-only background
    de_mix = WRK/"de_mix.wav"
    print("\n" + "=" * 60)
    print("Step 5: Mix and master (instrumental + voice)")
    print("=" * 60)
    run([SCRIPTS/"04_mix_and_master.py","--src_audio",src_instrumental,"--de_audio",de_voice,"--out_mix",de_mix])

    # 06 finalize (mux, copy artifacts)
    print("\n" + "=" * 60)
    print("Step 6: Finalize outputs (mux video, copy artifacts)")
    print("=" * 60)
    run([SCRIPTS/"06_finalize_outputs.py","--video",args.video,"--mix_wav",de_mix,
         "--srt_de",de_srt,"--out_dir",OUT])

    print("\n" + "=" * 60)
    print("✓ Pipeline complete!")
    print("=" * 60)
    print(f"Output files in: {OUT}")
    print(f"  - {video_stem}.de.mp4 (dubbed video)")
    print(f"  - {video_stem}.de.wav (dubbed audio)")
    print(f"  - {video_stem}.de.srt (German subtitles)")

if __name__ == "__main__":
    main()

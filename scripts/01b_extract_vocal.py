#!/usr/bin/env python3
"""
Extract vocals-only from full audio using Demucs.
Also creates a clone reference segment from the clean vocals for voice cloning.
"""
import argparse
import pathlib
import subprocess
import sys
import json

def run(cmd):
    subprocess.run(cmd, check=True)

def ffprobe_duration(path):
    """Get the duration of an audio file using ffprobe."""
    out = subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","json",path
    ], stderr=subprocess.PIPE)
    data = json.loads(out)
    return float(data["format"]["duration"])

def extract_vocals(input_wav, output_vocals):
    """
    Use Demucs to extract vocals from full audio.
    Demucs outputs to: separated/htdemucs/<stem>/vocals.wav
    """
    input_path = pathlib.Path(input_wav)
    output_vocals_path = pathlib.Path(output_vocals)
    output_vocals_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for demucs output
    temp_dir = output_vocals_path.parent / "demucs_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting vocals from: {input_wav}")
    print("This may take a few minutes...")
    
    try:
        # Run demucs with 2-stem model (vocals + instrumental only)
        # --two-stems=vocals is faster than full 4-stem separation
        run([
            "demucs",
            "--two-stems=vocals",
            "-o", str(temp_dir),
            "-n", "htdemucs",
            str(input_path)
        ])
        
        # Demucs creates: temp_dir/htdemucs/<input_stem>/vocals.wav
        stem_name = input_path.stem
        demucs_output = temp_dir / "htdemucs" / stem_name
        vocals_src = demucs_output / "vocals.wav"
        
        if not vocals_src.exists():
            raise FileNotFoundError(f"Demucs output not found: {vocals_src}")
        
        # Copy vocals to desired output location with 48kHz sample rate
        run(["ffmpeg", "-y", "-i", str(vocals_src),
             "-ar", "48000", str(output_vocals_path)])
        
        print(f"✓ Vocals saved to: {output_vocals}")
        
    finally:
        # Clean up temp directory
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def extract_clone_ref(vocals_wav, out_ref, ref_sec=6.0):
    """Extract a reference segment from the vocals-only audio for voice cloning."""
    print(f"Extracting clone reference from vocals: {vocals_wav}...")
    dur = ffprobe_duration(vocals_wav)
    start = max(0.0, (dur - ref_sec)/2.0)
    print(f"  Vocals duration: {dur:.2f}s, extracting {ref_sec}s starting at {start:.2f}s")
    run(["ffmpeg","-y","-i",vocals_wav,"-ss",f"{start:.3f}","-t",str(ref_sec),
         "-c","copy",out_ref])
    print(f"✓ Clone reference created: {out_ref}")

def main():
    ap = argparse.ArgumentParser(description="Extract vocals and create clone reference")
    ap.add_argument("--input", required=True, help="Input full audio file (src_full.wav)")
    ap.add_argument("--out_vocals", required=True, help="Output vocals-only file")
    ap.add_argument("--clone_ref", required=True, help="Output clone reference file")
    args = ap.parse_args()
    
    extract_vocals(args.input, args.out_vocals)
    extract_clone_ref(args.out_vocals, args.clone_ref)
    print("OK: Vocal extraction and clone_ref creation complete.")

if __name__ == "__main__":
    main()

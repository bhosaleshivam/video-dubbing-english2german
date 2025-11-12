#!/usr/bin/env python3
"""
Separate vocals from background music using Demucs.
Outputs instrumental-only track for mixing with translated VO.
"""
import argparse
import pathlib
import subprocess
import sys

def run(cmd):
    subprocess.run(cmd, check=True)

def separate_vocals(input_wav, output_instrumental, output_vocals=None):
    """
    Use Demucs to separate vocals from instrumental.
    Demucs outputs to: separated/htdemucs/<stem>/vocals.wav and no_vocals.wav
    """
    input_path = pathlib.Path(input_wav)
    output_inst_path = pathlib.Path(output_instrumental)
    output_inst_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp directory for demucs output
    temp_dir = output_inst_path.parent / "demucs_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Separating vocals from: {input_wav}")
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
        
        # Demucs creates: temp_dir/htdemucs/<input_stem>/vocals.wav and no_vocals.wav
        stem_name = input_path.stem
        demucs_output = temp_dir / "htdemucs" / stem_name
        
        instrumental_src = demucs_output / "no_vocals.wav"
        vocals_src = demucs_output / "vocals.wav"
        
        if not instrumental_src.exists():
            raise FileNotFoundError(f"Demucs output not found: {instrumental_src}")
        
        # Copy instrumental to desired output location
        run(["ffmpeg", "-y", "-i", str(instrumental_src), 
             "-ar", "48000", str(output_inst_path)])
        
        # Optionally copy vocals if requested
        if output_vocals and vocals_src.exists():
            run(["ffmpeg", "-y", "-i", str(vocals_src),
                 "-ar", "48000", str(output_vocals)])
        
        print(f"✓ Instrumental saved to: {output_instrumental}")
        
    finally:
        # Clean up temp directory
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    ap = argparse.ArgumentParser(description="Separate vocals from background music")
    ap.add_argument("--input", required=True, help="Input audio file (src_full.wav)")
    ap.add_argument("--out_instrumental", required=True, help="Output instrumental-only file")
    ap.add_argument("--out_vocals", help="Optional: output vocals-only file")
    args = ap.parse_args()
    
    separate_vocals(args.input, args.out_instrumental, args.out_vocals)
    print("OK: Vocal separation complete.")

if __name__ == "__main__":
    main()

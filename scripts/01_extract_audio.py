#!/usr/bin/env python3
import argparse, subprocess, json, tempfile, os, math, shutil, pathlib, sys

def run(cmd):
    """Run a command and handle errors gracefully."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"Exit code: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"STDOUT: {e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"STDERR: {e.stderr}", file=sys.stderr)
        raise
    except FileNotFoundError as e:
        print(f"ERROR: Command not found: {cmd[0]}", file=sys.stderr)
        print(f"Please make sure {cmd[0]} is installed and in your PATH", file=sys.stderr)
        raise

def check_video_file(video):
    """Check if video file exists and is valid."""
    if not os.path.exists(video):
        raise FileNotFoundError(f"Input video file not found: {video}")
    
    # Check file size
    size = os.path.getsize(video)
    size_mb = size / (1024 * 1024)
    print(f"Video file: {video} ({size_mb:.2f} MB)")
    
    if size == 0:
        raise ValueError(f"Video file is empty: {video}")
    if size < 1024:  # Less than 1KB is suspicious
        print(f"WARNING: Video file is very small ({size} bytes), may be corrupted", file=sys.stderr)
    
    # Try to probe the file to check if it's valid
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=format_name,duration", "-of", "json", video],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            error_msg = result.stderr.lower()
            if "moov atom not found" in error_msg or "invalid data" in error_msg:
                raise ValueError(
                    f"Video file appears to be corrupted or incomplete: {video}\n"
                    f"This usually means:\n"
                    f"  - The file download was interrupted\n"
                    f"  - The file is still being transferred\n"
                    f"  - The file is corrupted\n"
                    f"Please re-download or re-transfer the video file."
                )
            else:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timed out while checking {video}")
    except FileNotFoundError:
        # ffprobe not found, skip validation
        pass

def extract_audio(video, out_wav, sr=48000, ch=1):
    """Extract audio from video file."""
    check_video_file(video)
    print(f"Extracting audio from {video} to {out_wav}...")
    pathlib.Path(out_wav).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        run(["ffmpeg","-y","-i",video,"-vn","-ac",str(ch),"-ar",str(sr),
             "-c:a","pcm_s16le",out_wav])
    except subprocess.CalledProcessError as e:
        # Check for specific corruption errors in stderr
        if e.stderr and ("moov atom not found" in e.stderr.lower() or "invalid data" in e.stderr.lower()):
            raise ValueError(
                f"Video file is corrupted or incomplete: {video}\n"
                f"Error: moov atom not found - this usually means the file is incomplete.\n"
                f"Please re-download or re-transfer the video file."
            )
        raise
    
    if not os.path.exists(out_wav):
        raise RuntimeError(f"Output file was not created: {out_wav}")
    print(f"✓ Audio extracted successfully: {out_wav}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out_wav", required=True)            # e.g. data/work/src_full.wav
    args = ap.parse_args()
    
    try:
        extract_audio(args.video, args.out_wav)
        print("\n✓ SUCCESS: Audio extracted")
    except Exception as e:
        print(f"\n✗ FAILED: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

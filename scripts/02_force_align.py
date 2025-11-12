#!/usr/bin/env python3
import argparse
import re
import json
import subprocess
import pathlib
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

TIME = lambda s: f"{int(s//3600):02d}:{int(s%3600//60):02d}:{s%60:06.3f}".replace('.',',')

def ffprobe_duration(path):
    """Extract audio duration using ffprobe."""
    try:
        logger.debug(f"Getting duration for audio file: {path}")
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            stderr=subprocess.PIPE
        )
        duration = float(json.loads(out)["format"]["duration"])
        logger.info(f"Audio duration: {duration:.3f} seconds")
        return duration
    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe failed: {e.stderr.decode() if e.stderr else str(e)}")
        raise RuntimeError(f"Failed to get audio duration from {path}") from e
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse ffprobe output: {e}")
        raise RuntimeError(f"Failed to parse audio duration from {path}") from e

def naive_sentences(text):
    """Split text into sentences using simple punctuation-based splitting."""
    try:
        logger.debug("Splitting text into sentences")
        parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', text) if p.strip()]
        result = parts or [text.strip()]
        logger.info(f"Split text into {len(result)} sentence(s)")
        return result
    except Exception as e:
        logger.error(f"Failed to split text into sentences: {e}")
        raise RuntimeError("Failed to process text") from e

def write_srt(segments, out_path):
    """Write segments to SRT file."""
    try:
        logger.debug(f"Writing SRT file with {len(segments)} segments to {out_path}")
        out = []
        for i, (start, end, txt) in enumerate(segments, 1):
            out += [str(i), f"{TIME(start)} --> {TIME(end)}", txt, ""]
        
        out_dir = pathlib.Path(out_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created output directory: {out_dir}")
        
        pathlib.Path(out_path).write_text("\n".join(out), encoding="utf-8")
        logger.info(f"Successfully wrote SRT file: {out_path}")
    except Exception as e:
        logger.error(f"Failed to write SRT file to {out_path}: {e}")
        raise RuntimeError(f"Failed to write output SRT file") from e

def force_align(audio, text, out_srt):
    """Force align audio with text using aeneas or fallback to naive chunking."""
    logger.info("Starting force alignment process")
    logger.info(f"Audio file: {audio}")
    logger.info(f"Text file: {text}")
    logger.info(f"Output SRT: {out_srt}")
    
    # Validate input files exist
    audio_path = pathlib.Path(audio)
    text_path = pathlib.Path(text)
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio}")
    if not text_path.exists():
        raise FileNotFoundError(f"Text file not found: {text}")
    
    logger.debug("Input files validated")
    
    # Prefer aeneas if available, else naive equal-chunking
    try:
        logger.info("Attempting to use aeneas for force alignment...")
        from aeneas.executetask import ExecuteTask
        from aeneas.task import Task
        
        logger.debug("aeneas library imported successfully")
        cfg = "task_language=eng|is_text_type=plain|os_task_file_format=srt"
        task = Task(config_string=cfg)
        task.audio_file_path = str(audio_path.absolute())
        task.text_file_path = str(text_path.absolute())
        task.sync_map_file_path = str(pathlib.Path(out_srt).absolute())
        
        logger.info("Executing aeneas alignment task...")
        ExecuteTask(task).execute()
        task.output_sync_map_file()
        logger.info("✓ Force alignment completed successfully using aeneas")
        return
    except ImportError:
        logger.warning("aeneas library not available, falling back to naive equal-chunking")
    except Exception as e:
        logger.warning(f"aeneas alignment failed: {e}, falling back to naive equal-chunking")
    
    # Fallback to naive equal-chunking
    try:
        logger.info("Using naive equal-chunking method...")
        duration = ffprobe_duration(audio)
        
        logger.info("Reading text file...")
        text_content = text_path.read_text(encoding="utf-8")
        logger.debug(f"Text length: {len(text_content)} characters")
        
        sentences = naive_sentences(text_content)
        num_sentences = len(sentences)
        
        if num_sentences == 0:
            raise ValueError("No sentences found in text file")
        
        logger.info(f"Distributing {num_sentences} sentence(s) over {duration:.3f} seconds")
        per = duration / num_sentences
        logger.debug(f"Average segment duration: {per:.3f} seconds per sentence")
        
        logger.info("Creating segments...")
        segs = [(i * per, min((i + 1) * per, duration), s) for i, s in enumerate(sentences)]
        
        logger.info(f"Generated {len(segs)} segment(s)")
        write_srt(segs, out_srt)
        logger.info("✓ Naive alignment completed successfully")
    except Exception as e:
        logger.error(f"Naive alignment failed: {e}")
        raise RuntimeError(f"Force alignment failed: {e}") from e

def main():
    """Main entry point."""
    ap = argparse.ArgumentParser(
        description="Force align audio with text transcript",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--audio", required=True, help="Input audio file (e.g., data/work/src_full.wav)")
    ap.add_argument("--text", required=True, help="Input text file (e.g., data/input/transcript.txt)")
    ap.add_argument("--out_srt", required=True, help="Output SRT file (e.g., data/work/segments_en.srt)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    
    args = ap.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        logger.info("=" * 60)
        logger.info("Force Alignment Script")
        logger.info("=" * 60)
        
        force_align(args.audio, args.text, args.out_srt)
        
        logger.info("=" * 60)
        logger.info("✓ SUCCESS: EN SRT created")
        logger.info(f"Output file: {args.out_srt}")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

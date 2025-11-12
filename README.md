# Video Dubbing Pipeline

EN->DE video dubbing pipeline with TTS and voice cloning using CoquiTTS.

## Quick Start

```cmd
conda create -n video_dub python=3.9 pip -y
conda activate video_dub
python -m pip install -r requirements.txt
```

**Note:** CoquiTTS was chosen over OpenVoice due to dependency issues.

## Troubleshooting

**av (PyAV) installation issues:**
```cmd
conda install -c conda-forge av -y
```

**TTS requires Visual C++:** Install "Desktop development with C++" workload from Visual Studio 2022 Build Tools with MSVC v143 and Windows SDK.

**Optional - aeneas for force alignment:**
```cmd
python -m pip install --no-build-isolation aeneas
```

**Optional - PyTorch with CUDA:**
```cmd
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Usage

### Full Pipeline

```cmd
python main.py --video data/input/your-video.mp4 --transcript data/input/your-captions.srt
```

### Step-by-Step

**0. Prep**
```cmd
rmdir /s /q data\work data\output 2>nul & mkdir data\work data\output
```

**1. Extract Audio**
```cmd
python scripts/01_extract_audio.py --video data/input/your-video.mp4 --out_wav data/work/src_full.wav --clone_ref data/work/clone_ref.wav
```

**2. Translate SRT**
```cmd
python scripts/02_translate_srt.py --in_srt_en data/input/your-captions.srt --out_srt_de data/work/your-video.de.srt
```

**3. Generate TTS**
```cmd
python scripts/03_clone_tts_edge.py --srt_de data/work/your-video.de.srt --out_segments_dir data/work/tts_segments_edge --voice_ref data/work/clone_ref.wav
```

**4. Time-fit & Concatenate**
```cmd
python scripts/04_time_fit_and_concat.py --srt_de data/work/your-video.de.srt --segments_dir data/work/tts_segments_edge --fit_dir data/work/tts_fit --out_concat_wav data/work/de_voice.wav
```

**5. Mix & Master**
```cmd
python scripts/04_mix_and_master.py --src_audio data/work/src_full.wav --de_audio data/work/de_voice.wav --out_mix data/work/de_mix.wav
```

**6. Mux Video**
```cmd
ffmpeg -i data/input/your-video.mp4 -i data/work/de_mix.wav -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 data/output/your-video.de.mp4
```

**7. Finalize Outputs**
```cmd
python scripts/06_finalize_outputs.py --video data/input/your-video.mp4 --mix_wav data/work/de_mix.wav --srt_de data/work/your-video.de.srt --out_dir data/output
```

## Output

Final files in `data/output/`:
- `your-video.de.mp4` - Dubbed video
- `your-video.de.wav` - Dubbed audio
- `your-video.de.srt` - German subtitles

REM Install PyTorch (CUDA version - adjust if you need CPU-only)
python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

REM Or for CPU-only:
REM pip install torch torchaudio
```

## Quick check that you're device is setup

## 0) Prep

**Make clean work/output dirs**
```cmd
rmdir /s /q data\work data\output 2>nul
mkdir data\work data\output
```

**Sanity: ffmpeg present?**
```cmd
ffmpeg -version
ffprobe -version
```

NOTE: If ffprobe is not installing, then you  need to add FFMPEG path in your user variables under PATH.

---

## 1) `scripts/01_extract_audio.py`

**Run**
```cmd
python scripts/01_extract_audio.py --video data/input/your-video.mp4 --out_wav data/work/src_full.wav --clone_ref data/work/clone_ref.wav
```

**Verify**
```cmd
dir data\work\src_full.wav data\work\clone_ref.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/src_full.wav
```

---

## 2a) `scripts/02_force_align.py` (force-align a plain text transcript)

**Make a TXT from the SRT for testing**
```cmd
REM Extract text lines from SRT (manual filtering needed or use a text editor)
type data\input\your-captions.srt > data\input\transcript.txt
```

**Run**
```cmd
python scripts/02_force_align.py --audio data/work/src_full.wav --text data/input/transcript.txt --out_srt data/work/segments_en.srt
```

**Verify**
```cmd
type data\work\segments_en.srt | more
find /c /v "" data\work\segments_en.srt
```

---

## 2b) `scripts/02_translate_srt.py`

*(Use either the original SRT or the aligned one from 2a.)*

**Run**
```cmd
python scripts/02_translate_srt.py --in_srt_en data/input/your-captions.srt --out_srt_de data/work/your-video.de.srt
```

**Verify**
```cmd
type data\work\your-video.de.srt | more
```

---

## 3) `scripts/03_clone_tts_edge.py`

**Prerequisites:**
- `data/work/your-video.de.srt` (from your translate step)
- `data/work/clone_ref.wav` (from 01_extract_audio)
- CoquiTTS installed (included in requirements.txt)

**Run (make sure conda environment is activated):**
```cmd
python scripts/03_clone_tts_edge.py --srt_de data/work/your-video.de.srt --out_segments_dir data/work/tts_segments_edge --voice_ref data/work/clone_ref.wav
```

**Verify (Number of generated WAVs equals SRT cues)**
```cmd
dir /b data\work\tts_segments_edge\*.wav | find /c /v ""
REM Compare with number of cues in SRT
```

**Check TTS report:**
```cmd
REM Check TTS generation report
type data\work\tts_segments_edge\tts_report.json
```

**Listen to a sample located at data/work/tts_segments_edge/**


## 4) `scripts/04_time_fit_and_concat.py`

**Run**
```cmd
python scripts/04_time_fit_and_concat.py --srt_de data/work/your-video.de.srt --segments_dir data/work/tts_segments_edge --fit_dir data/work/tts_fit --out_concat_wav data/work/de_voice.wav
```

**Verify**
```cmd
dir data\work\de_voice.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/de_voice.wav
```

---

## 5) `scripts/04_mix_and_master.py`

**Run**
```cmd
python scripts/04_mix_and_master.py --src_audio data/work/src_full.wav --de_audio data/work/de_voice.wav --out_mix data/work/de_mix.wav
```

**Verify**
```cmd
dir data\work\de_mix.wav
ffprobe -v error -show_streams -select_streams a data/work/de_mix.wav | findstr "codec_name sample_rate channels"
```

---

## 6) `scripts/05_mux_and_export.sh`

**Run**
```cmd
REM Note: This script is a bash script. Convert to batch or run the ffmpeg command directly:
ffmpeg -i data/input/your-video.mp4 -i data/work/de_mix.wav -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 data/output/your-video.de.mp4
```

**Verify**
```cmd
ffprobe -v error -show_streams -select_streams a data/output/your-video.de.mp4 | findstr codec_name
```

---

## 7) `scripts/06_finalize_outputs.py`

**Run**
```cmd
python scripts/06_finalize_outputs.py --video data/input/your-video.mp4 --mix_wav data/work/de_mix.wav --srt_de data/work/your-video.de.srt --out_dir data/output
```

**Verify (final artifacts)**
```cmd
dir data\output\your-video.de.mp4 data\output\your-video.de.wav data\output\your-video.de.srt
```

---

## 8) (Optional full-pipeline sanity) `main.py`

**Run via SRT path**
```cmd
python main.py --video data/input/your-video.mp4 --transcript data/input/your-captions.srt
```

**Or via TXT path (tests force-align branch)**
```cmd
python main.py --video data/input/your-video.mp4 --transcript data/input/transcript.txt
```

**Verify**
```cmd
dir data\output\your-video.de.*
```

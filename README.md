# Video Dubbing Pipeline

EN->DE video dubbing pipeline with TTS and voice cloning using CoquiTTS.

**Note:** CoquiTTS was chosen over OpenVoice due to dependency issues.

**Platform Compatibility:** This code has been developed and tested on Windows. It has not been tested on Mac or Linux systems.

## Sample Videos

<table>
<tr>
<td width="50%">

**Input (English):**

<video width="100%" controls>
  <source src="./data/input/Tanzania-2.mp4" type="video/mp4">
  Your browser does not support the video tag. <a href="./data/input/Tanzania-2.mp4">Download video</a>
</video>

</td>
<td width="50%">

**Output (German Dubbed):**

<video width="100%" controls>
  <source src="./data/output/Tanzania-2.de.mp4" type="video/mp4">
  Your browser does not support the video tag. <a href="./data/output/Tanzania-2.de.mp4">Download video</a>
</video>

</td>
</tr>
</table>

## Assumptions

1. **Inputs:** One English video (.mp4) and the original English transcript (may be SRT or plain text). If not time-coded, force-align using aeneas (if available) or naive equal-chunking fallback.
2. **Output:** A German-dubbed video (.mp4), separate German audio file (.wav), and German subtitles (.srt).
3. **Quality targets:**
   - a. Global A/V drift managed via per-segment time-fitting with padding (default 0.1s per cue);
   - b) Speech intelligible and natural using Coqui XTTS v2 for voice cloning or Thorsten VITS as fallback;
   - c) Loudness normalized to −16 LUFS (I=-16, TP=-1.5, LRA=11);
   - d) Original music/FX preserved via Demucs vocal separation with automatic ducking (sidechaincompress) when voice is present.
4. **Language:** EN→DE only. Translation via argostranslate (auto-downloads EN→DE package on first run).
5. **Voice:** Speaker cloning via Coqui XTTS v2 using 6-second reference extracted from clean vocals. Falls back to generic German voice (Thorsten) if cloning fails or reference is too short (<3s).
6. **Tooling:** OSS/local stack; no paid APIs. Requires ffmpeg, ffprobe, and optional aeneas for better alignment.
7. **Speakers:** Optimized for one primary speaker; multi-speaker diarization is not supported.
8. **Noise:** Demucs vocal separation handles moderate background noise. Heavy noise may affect voice cloning quality.
9. **Sync strategy:** Per-segment duration fit using atempo chains (0.5-2.0x per link) with silence trimming and padding. Segments are concatenated losslessly (PCM) before final mix.
10. **Scope:** Lip-sync is out of scope. Video stream is copied without modification (no visual retiming).

## Limitations / Future Work

- **Multi-speaker diarization and per-speaker voice cloning:** Current implementation optimized for single primary speaker.
- **True lip-sync (phoneme-level retiming):** Audio-only dubbing; video frames are not modified. Future integration with Wav2Lip or similar tools could enable visual lip-sync.
- **Visual smoothing:** Video stream is copied without modification (no frame interpolation or scene-cut smoothing). The pipeline focuses on audio dubbing; visual retiming is intentionally out of scope for this MVP.
- **Broader formats:** Support for MKV, MOV, and embedded/"burned-in" subtitle OCR.
- **Language pair expansion:** Currently EN→DE only; could expand to EN↔️X with additional translation models.
- **Optional music/FX stem separation:** Instead of global ducking, separate music and effects into individual stems for finer control.
- **Better MT quality controls:** Glossary support, style guides, and human post-edit pass integration.

## Glossary

1. **`.mp4`** → MP4 stands for MPEG-4 Part 14, which is a digital multimedia container format used to store video, audio, subtitles, and still images
2. **`.srt`** → SRT format stands for SubRip Subtitle and is a plain text file format used to store subtitles for videos
3. **ASR** → ASR stands for Automatic Speech Recognition, a technology that converts spoken audio into written text.
4. **EN** → The ISO 639-1 two-letter shortform for English is EN
5. **DE** → The ISO 639-1 two-letter shortform for German is DE
6. **Demux** → Demux is the shortened form of demultiplexer or demultiplexing, which is the process of separating a single, composite signal into its individual components
7. **Diarization** → Diarization is the process of partitioning an audio recording to identify and label "who spoke when" by segmenting speech segments into homogeneous clusters of a single speaker.

## OS Prerequisites

Before installing Python dependencies, ensure you have the following system-level tools installed:

### Required

1. **FFmpeg & FFprobe**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add FFmpeg's `bin` directory to your system PATH
   - Verify installation: `ffmpeg -version` and `ffprobe -version`

2. **Python 3.9+**
   - Recommended: Use Conda or Miniconda for environment management

### Windows-Specific

3. **Visual Studio Build Tools** (required for TTS compilation)
   - Download [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
   - Install the "Desktop development with C++" workload
   - Ensure MSVC v143 and Windows SDK are selected

### Optional but Recommended

4. **Demucs Model Download**
   - The first run will automatically download the Demucs `htdemucs` model (~2GB)
   - This happens when running vocal separation (step 1b)
   - Ensure stable internet connection for initial setup

5. **aeneas** (for better force-alignment)
   - Install after main dependencies: `python -m pip install --no-build-isolation aeneas`

6. **PyTorch with CUDA** (for GPU acceleration)
   - Install after main dependencies: `python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121`
   - Significantly speeds up TTS generation and vocal separation

## Quick Start

```cmd
conda create -n video_dub python=3.9 pip -y
conda activate video_dub
python -m pip install -r requirements.txt
```

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

## Sample Media for Testing

To quickly test the pipeline, you can use the included sample files or prepare your own:

### Included Sample (if available)
- **Input video:** `data/input/Tanzania-2.mp4` (English)
- **Input transcript:** `data/input/Tanzania-2.srt` (English SRT)
- **Expected output:** `data/output/Tanzania-2.de.mp4` (German dubbed)
- **Expected output:** `data/output/Tanzania-2.de.wav` (German audio)
- **Expected output:** `data/output/Tanzania-2.de.srt` (German subtitles)

### Prepare Your Own Test Media
If sample files are not included, prepare:
1. A short English video (`.mp4`, 30-60 seconds recommended for testing)
2. English subtitles (`.srt` format) or plain text transcript (`.txt`)
3. Place both in `data/input/` directory

### Quick Test Run
```cmd
REM Using included sample
python main.py --video data/input/Tanzania-2.mp4 --transcript data/input/Tanzania-2.srt

REM Or with your own media
python main.py --video data/input/your-video.mp4 --transcript data/input/your-captions.srt
```

Expected processing time: ~2-5 minutes for a 1-minute video (CPU), ~1-2 minutes with GPU acceleration.

## Usage

### Full Pipeline

```cmd
python main.py --video data/input/your-video.mp4 --transcript data/input/your-captions(.srt o

### Step-by-Step

**0. Prep**
```cmd
rmdir /s /q data\work data\output 2>nul & mkdir data\work data\output
```

**1. Extract Audio**
```cmd
python scripts/01_extract_audio.py --video data/input/your-video.mp4 --out_wav data/work/src_full.wav
```

**1b. Extract Vocals & Clone Reference**
```cmd
python scripts/01b_extract_vocal.py --input data/work/src_full.wav --out_vocals data/work/src_vocals.wav --clone_ref data/work/clone_ref.wav
```

**1c. Extract Background Music**
```cmd
python scripts/01b_extract_background.py --input data/work/src_full.wav --out_instrumental data/work/src_instrumental.wav
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
python scripts/04_time_fit_and_concat.py --srt data/work/your-video.de.srt --tts-dir data/work/tts_segments_edge --workdir data/work/tts_fit --out data/work/de_voice.wav
```

**5. Mix & Master (Instrumental + Voice)**
```cmd
python scripts/04_mix_and_master.py --src_audio data/work/src_instrumental.wav --de_audio data/work/de_voice.wav --out_mix data/work/de_mix.wav
```
*Note: Mixes instrumental background music with German voice-over. The instrumental is automatically ducked when voice is present.*

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

---

## Detailed Step-by-Step Verification

### 0) Prep

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

### 1) `scripts/01_extract_audio.py`

**Run**
```cmd
python scripts/01_extract_audio.py --video data/input/your-video.mp4 --out_wav data/work/src_full.wav
```

**Verify**
```cmd
dir data\work\src_full.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/src_full.wav
```

---

### 1b) `scripts/01b_extract_vocal.py`

**Run (extracts vocals-only and creates clone reference from clean vocals)**
```cmd
python scripts/01b_extract_vocal.py --input data/work/src_full.wav --out_vocals data/work/src_vocals.wav --clone_ref data/work/clone_ref.wav
```

**Verify**
```cmd
dir data\work\src_vocals.wav data\work\clone_ref.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/src_vocals.wav
```

---

### 1c) `scripts/01b_extract_background.py`

**Run (extracts instrumental-only background music)**
```cmd
python scripts/01b_extract_background.py --input data/work/src_full.wav --out_instrumental data/work/src_instrumental.wav
```

**Verify**
```cmd
dir data\work\src_instrumental.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/src_instrumental.wav
```

---

### 2a) `scripts/02_force_align.py` (force-align a plain text transcript)

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

### 2b) `scripts/02_translate_srt.py`

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

### 3) `scripts/03_clone_tts_edge.py`

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

---

### 4) `scripts/04_time_fit_and_concat.py`

**Run**
```cmd
python scripts/04_time_fit_and_concat.py --srt data/work/your-video.de.srt --tts-dir data/work/tts_segments_edge --workdir data/work/tts_fit --out data/work/de_voice.wav
```

**Verify**
```cmd
dir data\work\de_voice.wav
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/de_voice.wav
```

---

### 5) `scripts/04_mix_and_master.py`

**Run (mixes instrumental background with German voice-over)**
```cmd
python scripts/04_mix_and_master.py --src_audio data/work/src_instrumental.wav --de_audio data/work/de_voice.wav --out_mix data/work/de_mix.wav
```

**What it does:**
- Mixes instrumental background music (`src_instrumental.wav`) with German voice-over (`de_voice.wav`)
- Automatically ducks (reduces) the instrumental volume when voice is present using sidechaincompress
- Keeps music subtle in the background (~-16.5 dB)
- Applies loudness normalization to the final mix (-16 LUFS)
- If no music is detected in the instrumental, outputs voice-only

**Troubleshooting - If you only hear music (no voice):**
```cmd
REM Try simple mix without ducking
python scripts/04_mix_and_master.py --src_audio data/work/src_instrumental.wav --de_audio data/work/de_voice.wav --out_mix data/work/de_mix.wav --simple_mix

REM Check if voice file has audio
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 data/work/de_voice.wav

REM Listen to voice file directly
ffplay data/work/de_voice.wav
```

**Verify**
```cmd
dir data\work\de_mix.wav
ffprobe -v error -show_streams -select_streams a data/work/de_mix.wav | findstr "codec_name sample_rate channels"
```

---

### 6) `scripts/05_mux_and_export.sh`

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

### 7) `scripts/06_finalize_outputs.py`

**Run**
```cmd
python scripts/06_finalize_outputs.py --video data/input/your-video.mp4 --mix_wav data/work/de_mix.wav --srt_de data/work/your-video.de.srt --out_dir data/output
```

**Verify (final artifacts)**
```cmd
dir data\output\your-video.de.mp4 data\output\your-video.de.wav data\output\your-video.de.srt
```

---

### 8) (Optional full-pipeline sanity) `main.py`

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

---
name: qwen3-tts
version: 1.4.0
description: >
  Run Qwen3-TTS text-to-speech locally on Apple Silicon (MLX preferred)
  or GPU/CPU (PyTorch). Supports voice cloning, voice design, and preset
  custom voices. 10 languages, 3-second voice cloning, emotional control.
author: Alberto Gonzalez Rouille
license: Apache-2.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [tts, speech, voice-cloning, voice-design, mlx, apple-silicon, qwen]
    config:
      - key: qwen3-tts.spanish-tts-path
        description: "Path to the qwen3-tts-spanish-voices repository clone"
        default: "~/Code/spanish-tts"
        prompt: "Spanish TTS repo path"
required_environment_variables:
  - name: QWEN_TTS_OUTPUT_DIR
    prompt: "Output directory for generated audio files"
    help: "Defaults to ~/tts-output/ if not set"
    required_for: "custom output directory"
  - name: QWEN_TTS_MODEL
    prompt: "HuggingFace model ID override"
    help: "Defaults to the recommended 8-bit MLX model for each mode"
    required_for: "custom model selection"
---

# Qwen3-TTS Local Inference

## Overview

Qwen3-TTS is a state-of-the-art TTS system from Alibaba supporting 10 languages
(Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian).

Three model variants:
- **CustomVoice**: 9 preset speakers with emotion/style control
- **VoiceDesign**: Create voices from natural language descriptions
- **Base**: 3-second voice cloning from reference audio

Sizes: 1.7B (best quality) and 0.6B (faster, lighter)

## When to Use

- User asks to convert text to speech or generate audio from text
- User wants to clone a voice from a reference audio sample
- User wants to design a custom voice from a natural language description
- User needs multilingual speech synthesis (especially CJK + European languages)

## Approach Selection

### Apple Silicon (M1/M2/M3/M4) — Use MLX (Recommended)
- 2-3GB RAM vs 10+GB for PyTorch
- 40-50°C vs 80-90°C CPU temperature
- Quantized models (8-bit or 4-bit) available
- Uses `mlx-audio` framework

### NVIDIA GPU — Use PyTorch + CUDA
- Official `qwen-tts` pip package
- FlashAttention 2 recommended (Ampere+)
- `device_map="cuda:0"`, `dtype=torch.bfloat16`

### Apple Silicon Fallback — PyTorch MPS
- Works but slower and heavier than MLX
- `device_map="mps"`, `dtype=torch.bfloat16`
- Do NOT use float16 or cpu — will hang or be extremely slow

---

## Step 1: Environment Setup

### MLX Approach (Apple Silicon)

```bash
# Create isolated environment
conda create -n qwen3-tts python=3.12 -y
conda activate qwen3-tts

# Install MLX dependencies
pip install "mlx-audio>=0.3.0" "mlx-lm>=0.30.0" numpy soundfile

# System dependency
brew install sox ffmpeg
```

### PyTorch Approach (CUDA or MPS fallback)

```bash
conda create -n qwen3-tts python=3.12 -y
conda activate qwen3-tts

# Official package
pip install -U qwen-tts

# For CUDA only (NOT available on Apple Silicon):
# pip install -U flash-attn --no-build-isolation

brew install sox ffmpeg
```

## Step 2: Model Download

### MLX Models (Apple Silicon)

Available on HuggingFace under `mlx-community/`:

| Model | 8-bit (Better Quality) | 4-bit (Faster/Lighter) |
|-------|----------------------|----------------------|
| CustomVoice 1.7B | mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit | mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit |
| CustomVoice 0.6B | mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit | mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit |
| VoiceDesign 1.7B | mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit | mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-4bit |
| Base 1.7B (Clone) | mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit | mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit |
| Base 0.6B (Clone) | mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit | mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit |

Download manually:
```bash
hf download mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  --local-dir ~/Models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit
```

Models auto-download on first use if not pre-cached.

### PyTorch Models

```bash
hf download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
  --local-dir ~/Models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-CustomVoice
```

## Step 3: Generate Speech

### MLX — Custom Voice (Preset Speakers)

Use the bundled script: `${HERMES_SKILL_DIR}/scripts/tts_mlx.py`

```bash
python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Hello, this is a test!" \
  --speaker Ryan --language English --speed 1.0 \
  --output ~/tts-output/test.wav
```

Available speakers:
- Chinese: Vivian (bright), Serena (warm), Uncle_Fu (seasoned), Dylan (Beijing), Eric (Sichuan)
- English: Ryan (dynamic), Aiden (sunny American)
- Japanese: Ono_Anna
- Korean: Sohee

### MLX — Voice Design

```bash
python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Welcome to the future of AI." \
  --mode voice-design \
  --instruct "A deep, calm male narrator with a British accent" \
  --language English \
  --output ~/tts-output/designed.wav
```

### MLX — Voice Cloning

```bash
python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Text to speak in cloned voice." \
  --mode voice-clone \
  --ref-audio /path/to/reference.wav \
  --ref-text "Transcript of the reference audio." \
  --language English \
  --output ~/tts-output/cloned.wav
```

### PyTorch MPS (Fallback)

```python
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    device_map="mps",        # CRITICAL: not "cpu", not "cuda"
    dtype=torch.bfloat16,    # CRITICAL: not float16
)

wavs, sr = model.generate_custom_voice(
    text="Hello world!",
    language="English",
    speaker="Ryan",
    instruct="Speak in a cheerful, energetic tone.",
)
sf.write("output.wav", wavs[0], sr)
```

## Step 4: Verify Output

```bash
# Check audio file
afplay output.wav          # macOS native playback
aplay output.wav           # Linux (ALSA) alternative
ffprobe output.wav         # Check format/duration
```

---

## Preset Speakers Reference

The open-source CustomVoice model has only 9 preset speakers. No Spanish, Portuguese,
German, French, Russian, or Italian preset speakers exist — but the model supports
synthesizing text in all 10 languages using any speaker (cross-lingual).

| Speaker | Language | Style |
|---------|----------|-------|
| Vivian | Chinese | Bright, clear |
| Serena | Chinese | Warm, gentle |
| Uncle_Fu | Chinese | Seasoned, mature |
| Dylan | Chinese | Beijing dialect |
| Eric | Chinese | Sichuan dialect |
| Ryan | English | Dynamic, versatile |
| Aiden | English | Sunny American |
| Ono_Anna | Japanese | Natural female |
| Sohee | Korean | Natural female |

### Spanish (and other unsupported-preset languages)

For languages without a preset speaker, use one of these approaches:

1. **Cross-lingual with existing speaker** — use Ryan or Vivian with `--language Spanish`:
   ```bash
   python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Hola, ¿cómo estás?" --speaker Ryan --language Spanish
   ```

2. **Voice Design** — describe the desired voice in natural language:
   ```bash
   python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Hola, bienvenidos." \
     --mode voice-design \
     --instruct "A warm 30-year-old Colombian male with a calm, friendly tone" \
     --language Spanish
   ```

3. **Voice Clone** — provide a 5-10s reference audio of a native speaker:
   ```bash
   python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Texto en español." \
     --mode voice-clone \
     --ref-audio /path/to/spanish_speaker.wav \
     --ref-text "Transcripción del audio de referencia." \
     --language Spanish
   ```

Note: The Alibaba Cloud DashScope API offers 49 timbres with broader language coverage
(including Dolce for Italian), but the open-source model is limited to these 9.

For a curated library of Spanish voices with a dedicated CLI, see the **Spanish Voices** section below.

## Performance Notes

- **RTF (Real-Time Factor)**: ~3.0 on M3 Max for 1.7B PyTorch (slower than real-time)
- MLX 8-bit is significantly faster and lighter than PyTorch MPS
- 0.6B models are ~3x faster than 1.7B with some quality tradeoff
- First run on MPS/MLX is slower due to kernel compilation (29% improvement by run 3)
- For faster-than-realtime TTS, consider F5-TTS (0.64 RTF) as alternative

## MLX API Reference (mlx-audio)

The unified `model.generate()` method handles all modes:

```python
from mlx_audio.tts import load_model

# Voice cloning (Base model)
model = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit")
results = model.generate(
    text="Texto a sintetizar.",
    lang_code="auto",        # auto-detects language from text
    ref_audio="/path/to/reference.wav",
    ref_text="Transcripción exacta del audio de referencia.",
)

# Voice design (VoiceDesign model — different model from above)
model = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit")
# IMPORTANT: always pass explicit lang_code for non-English targets
# Keep instruct in English — Spanish instructs cause gender/quality issues
results = model.generate(
    text="Texto en español.",
    lang_code="spanish",     # NEVER use "auto" — causes English accent
    instruct="A warm 30-year-old male with calm tone",
)

# Custom voice (CustomVoice model — different model from above)
model = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit")
results = model.generate_custom_voice(
    text="Hello!",
    speaker="Ryan",
    language="english",      # full word, lowercase
)

# All return generators:
first_result = next(iter(results))
audio_np = np.array(first_result.audio)
sf.write("out.wav", audio_np, model.sample_rate)
```

**Method availability** (mlx-audio API):
- `model.generate_voice_clone()` — does NOT exist; use `model.generate(ref_audio=..., ref_text=...)` instead
- `model.generate_voice_design()` — exists and works; `model.generate(instruct=...)` also works as an alternative
- `model.generate_custom_voice()` — exists and works; the standard method for preset speakers

## Spanish Voices (qwen3-tts-spanish-voices)

The [qwen3-tts-spanish-voices](https://github.com/alblez/qwen3-tts-spanish-voices) project
provides a dedicated CLI for Spanish TTS with curated voices. Clone voices sourced from
VoxForge Spanish (Creative Commons). Design voices use natural language descriptions.

### Prerequisites

Requires the qwen3-tts conda env already set up (Step 1 above). Then install from the repo directory:

```bash
conda activate qwen3-tts
cd ~/Code/spanish-tts   # or the path configured in qwen3-tts.spanish-tts-path
pip install -e ".[mlx]"
```

Run from the repo path configured in `qwen3-tts.spanish-tts-path` (default: `~/Code/spanish-tts`).

### Quick Reference

Requires the `qwen3-tts` conda env to be active (`conda activate qwen3-tts`).

```bash
# Generate speech with a specific voice
spanish-tts say "Hola, bienvenidos al programa." --voice neutral_male --play

# List all available voices
spanish-tts list

# Generate with ALL voices for side-by-side comparison
spanish-tts demo "Texto de prueba para comparar voces."

# Options
spanish-tts say "Texto." --voice carlos_mx --speed 1.1 --output ~/tts-output/custom.wav
```

### Shipped Voices

Four design voices are available out of the box (no reference audio needed):

| Voice | Gender | Description |
|-------|--------|-------------|
| `neutral_male` (default) | Male | Neutral, clear Latin American accent |
| `neutral_female` | Female | Neutral, clear Latin American accent |
| `energetic_male` | Male | Energetic, cheerful tone |
| `warm_female` | Female | Warm, comforting tone |

Clone voices (better accent fidelity) require running the curation pipeline below.

### Managing Voices

```bash
# Add a clone voice from reference audio (5-10s, clean, no background noise)
spanish-tts add-ref carlos_mx /path/to/audio.wav "Transcripción exacta del audio." \
  --accent mexico --gender male

# Add a design voice from a text description
spanish-tts add-design narrator "A calm 40-year-old male narrator" --gender male

# Remove a voice
spanish-tts remove carlos_mx
```

Voice registry lives at `~/.spanish-tts/voices.yaml`. Reference audio is copied to `~/.spanish-tts/references/`.

### Curation Pipeline (Adding Clone Voices from VoxForge)

Run from the spanish-tts repo directory to source clone voices from the
`ciempiess/voxforge_spanish` HuggingFace dataset (21,692 samples — Spain, Argentina,
Mexico, Chile, Latin America):

```bash
# Browse dataset stats by country/gender
python scripts/curate.py browse

# Find best speakers for a country/gender
python scripts/curate.py pick --country mexico --gender male

# Preview a speaker's clips
python scripts/curate.py listen SPEAKER_ID

# Export best clip as a voice (registers in voices.yaml automatically)
python scripts/curate.py export SPEAKER_ID --name carlos_mx --accent mexico --gender male
```

## Pitfalls

1. **NEVER use device_map="cpu" on Mac** — will hang for 20+ minutes and may never complete
2. **NEVER use float16 on MPS** — use bfloat16 only
3. **flash-attn does NOT compile on Apple Silicon** — skip it, not needed for MLX
4. **sox must be installed** — `brew install sox` or audio processing will fail
5. **First inference is slow** — kernel compilation warmup, subsequent runs faster
6. **MLX models need exact folder names** — HuggingFace repo name must match local dir name
7. **mlx-audio returns generators, not lists** — use `next(iter(results))` not `results[0]`
8. **huggingface-cli is deprecated** — use `hf download` instead
9. **Warnings about tokenizer regex and model type are harmless** — they don't affect generation quality
10. **For voice cloning**: reference audio should be 5-10s, clean (no background noise)
11. **The `--instruct` flag**: controls emotion/prosody for CustomVoice, is REQUIRED for VoiceDesign
12. **datasets v4.8+ requires torchcodec for audio decoding** — if torch is not installed, use `ds.with_format("arrow")` then decode raw bytes with soundfile: `sf.read(io.BytesIO(row.column("audio")[0].as_py()["bytes"]))`
13. **lang_code uses "auto" or lowercase full words** ("english", "chinese") — NOT "English" or "Spanish"
14. **speed parameter accepted but not yet functional** — `model.generate()` accepts `speed=` but silently ignores it (docstring: "not directly supported yet"). The bundled script adjusts the sample rate as a workaround. Do not rely on the API's speed parameter.
15. **VoiceDesign with lang_code="auto" produces English accent** — "auto" skips the codec language token entirely, so the model defaults to English prosody (especially when the instruct prompt is in English). ALWAYS pass explicit `lang_code="spanish"` (or target language) for VoiceDesign. Clone mode is not affected because the reference audio provides the acoustic prior.
16. **VoiceDesign instruct prompts should stay in ENGLISH, not the target language** — the model was trained primarily on English/Chinese voice descriptions. Writing instructs in Spanish causes severe gender confusion (male->female, female->male) and anime-like artifacts. Use English instructs + explicit `lang_code="spanish"` for best results. Even so, VoiceDesign produces "American TTS reading Spanish" prosody for most voices — only ~1 in 4 designs sounds near-native. For reliable native accent, always prefer voice cloning (Base model + reference audio).
17. **VoiceDesign is unreliable for non-English/Chinese native accents** — the model fundamentally cannot produce native Spanish (or likely other non-English) prosody from text descriptions alone. Clone voices using real speaker audio are far superior for accent fidelity. Use VoiceDesign only as a fallback when no reference audio is available, and expect English-accented output.
18. **qwen-tts (PyTorch) conflicts with mlx-audio/mlx-lm** — The official `qwen-tts` pip package pins `transformers==4.57.3`, but `mlx-audio`/`mlx-lm` require `transformers>=5.0.0`. They cannot coexist. On Apple Silicon using MLX, do NOT install `qwen-tts` — it's the CUDA/PyTorch path and unnecessary. If accidentally installed, remove with `pip uninstall qwen-tts`.
19. **conda run --no-banner incompatible with conda 25.x** — The `--no-banner` flag does not exist in conda 25.5.1+. If you see `conda: error: unrecognized arguments: --no-banner` in stderr, remove the flag. This affects any code calling `conda run` in a subprocess, not just spanish-tts. The hermes-agent provider was patched to remove it. Always use `conda run -n <env> <command>` without `--no-banner`.
20. **WAV-to-MP3 rename vs convert** — `spanish-tts say` always outputs WAV (PCM). Never use `os.rename()` or `shutil.move()` to change the extension to .mp3. Always convert with ffmpeg: `ffmpeg -y -i input.wav -acodec libmp3lame -b:a 128k output.mp3`. A renamed WAV will have wrong magic bytes (`RIFF` header instead of MP3 framing) and may break downstream tools (Telegram Opus conversion, media players expecting MP3 framing, any format-sniffing code).

## Hermes Native TTS Provider Integration

The `qwen3tts` provider in hermes-agent's `tools/tts_tool.py` wraps the `spanish-tts`
CLI so that `text_to_speech(text=...)` uses Qwen3-TTS directly.

**The agent does NOT need to use terminal() manually.** Just call `text_to_speech()`
and it works.

### Pipeline

```
text_to_speech() → _generate_qwen3tts() → conda run → spanish-tts say → WAV → ffmpeg → MP3/OGG
```

### Configuration

In hermes `config.yaml`:

```yaml
tts:
  provider: qwen3tts
  qwen3tts:
    voice: carlos_mx       # male Mexican Spanish (default)
    speed: 1.0             # synthesis speed multiplier
    conda_env: qwen3-tts   # conda environment name
```

### Key details

- Uses `conda run -n qwen3-tts` to invoke `spanish-tts say` (no conda activate needed)
- 120-second subprocess timeout (MLX on M1/M2/M3 Max takes ~15-30s for typical paragraphs)
- Checks both exit code and output file existence/size before returning
- Handles WAV→MP3 conversion via ffmpeg when the caller requests .mp3 output
- After generation, the caller's Opus conversion logic handles WAV/MP3→OGG for Telegram voice bubbles
- Edge TTS remains available as fallback by changing `provider` back to `edge`

### Patch documentation

The provider is a local modification to `tools/tts_tool.py`. It will be lost on
`hermes update`. See `references/tts_tool_provider_patch.md` in this skill for the
full code and re-application instructions.

## Troubleshooting text_to_speech() with qwen3tts Provider

### Provider returns success but audio is wrong voice or silent

1. Check conda env exists: `conda env list | grep qwen3-tts`
2. Test CLI directly: `conda run -n qwen3-tts spanish-tts say -v carlos_mx -o /tmp/test.wav "Hola mundo"`
3. Check the WAV: `file /tmp/test.wav` — should show `RIFF ... WAVE audio`
4. If `conda run` fails, check conda version: `conda --version` (25.x removed `--no-banner` — see pitfall 19)

### Provider silently falls back to Edge TTS

The caller in `tts_tool.py` has a broad try/except. If `_generate_qwen3tts` raises an
exception, some code paths may fall through to Edge TTS without logging. Check hermes
logs for "Qwen3-TTS" vs "Edge TTS" in the log output to confirm which provider was
actually used.

### Telegram sends audio but it doesn't play as voice bubble

Telegram requires Opus-in-OGG for voice bubbles. The provider auto-converts via
`_convert_to_opus()` after generation. If this fails, the MP3 is sent as a document
instead. Ensure ffmpeg is installed with libopus support:

```bash
ffmpeg -codecs | grep opus
```

### Output file has .mp3 extension but is actually WAV

This means the ffmpeg WAV→MP3 conversion failed and the code fell back to renaming.
Check that ffmpeg has libmp3lame:

```bash
ffmpeg -codecs | grep mp3lame
```

See pitfall 20 for details.

## Voice Selection for Hermes Agent

When the user asks for audio in Spanish without specifying a voice:
- **Default**: `carlos_mx` (male, Mexican Spanish, most tested)
- **Female voice**: use `lucia_es` when the user says "voz femenina" or context implies female voice

To list all available voices:

```bash
conda run -n qwen3-tts spanish-tts list
```

The voice is set in config.yaml under `tts.qwen3tts.voice`, but the agent can also
invoke `spanish-tts` directly via `terminal()` with `-v <voice_name>` for one-off
voice changes without modifying the config.

## Sources

- Official: https://qwen.ai/blog?id=qwen3-tts-1128
- HuggingFace: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- Apple Silicon MLX: https://github.com/kapi2800/qwen3-tts-apple-silicon
- MLX Audio: https://github.com/Blaizzy/mlx-audio
- Benchmark: https://tinycomputers.io/posts/the-real-cost-of-running-qwen-tts-locally-three-machines-compared.html
- MPS fix: https://github.com/QwenLM/Qwen3-TTS/issues/69

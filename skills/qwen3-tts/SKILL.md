---
name: qwen3-tts
version: 1.5.0
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
    requires_toolsets: [tts]
    config:
      - key: qwen3-tts.spanish-tts-path
        description: "Path to the qwen3-tts-spanish-voices repository clone"
        default: "~/Code/spanish-tts"
        prompt: "Spanish TTS repo path"
required_environment_variables:
  - name: QWEN_TTS_OUTPUT_DIR
    prompt: "Output directory for generated audio files"
    help: "Defaults to ~/tts-output/ if not set"
  - name: QWEN_TTS_MODEL
    prompt: "HuggingFace model ID override"
    help: "Defaults to the recommended 8-bit MLX model for each mode"
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

## Hermes Agent Quick Reference

### Primary method: terminal()

For Spanish TTS, use `terminal()` directly — no patching or setup beyond the conda env:

```bash
conda run -n qwen3-tts spanish-tts say -v carlos_mx -o /tmp/output.wav "Texto en español"
```

To convert WAV to MP3 (for non-Telegram delivery):
```bash
conda run -n qwen3-tts spanish-tts say -v carlos_mx -o /tmp/out.wav "Texto" && \
  ffmpeg -y -i /tmp/out.wav -acodec libmp3lame -b:a 128k /tmp/out.mp3
```

For Telegram voice bubbles (Opus-in-OGG):
```bash
conda run -n qwen3-tts spanish-tts say -v carlos_mx -o /tmp/out.wav "Texto" && \
  ffmpeg -y -i /tmp/out.wav -c:a libopus -b:a 64k /tmp/out.ogg
```

### Alternative: text_to_speech() (requires provider patch)

If the `qwen3tts` provider has been patched into `tts_tool.py` (see "Advanced"
section below), `text_to_speech(text="...")` works directly with no terminal()
calls needed. If the provider is not configured, Hermes uses Edge TTS instead.

### Voice selection

- **Default (male)**: `carlos_mx` — Mexican Spanish, most tested
- **Female voice**: `lucia_es` — use when the user says "voz femenina" or context implies female
- **List all voices**: `conda run -n qwen3-tts spanish-tts list`
- For one-off voice changes, pass `-v <voice_name>` in the terminal() command

### For non-Spanish languages

Use the bundled MLX script directly (the `spanish-tts` CLI is Spanish-only):

```bash
conda run -n qwen3-tts python scripts/tts_mlx.py "Hello world!" \
  --speaker Ryan --language English -o /tmp/english.wav
```

Script path: `scripts/tts_mlx.py` relative to this skill directory
(e.g. `~/.hermes/skills/qwen3-tts/scripts/tts_mlx.py`).

## Troubleshooting

### TTS command produces no output or wrong voice

1. Check conda env exists: `conda env list | grep qwen3-tts`
2. Test CLI directly: `conda run -n qwen3-tts spanish-tts say -v carlos_mx -o /tmp/test.wav "Hola mundo"`
3. Check the WAV: `file /tmp/test.wav` — should show `RIFF ... WAVE audio`
4. If `conda run` fails, check conda version: `conda --version` (25.x removed `--no-banner` — see pitfall 19)

### text_to_speech() silently falls back to Edge TTS

If the `qwen3tts` provider is patched but failing, `tts_tool.py`'s broad try/except
may fall through to Edge TTS without logging. Check hermes logs for "Qwen3-TTS" vs
"Edge TTS" to confirm which provider was actually used.

### Telegram sends audio but it doesn't play as voice bubble

Telegram requires Opus-in-OGG. Ensure ffmpeg has libopus: `ffmpeg -codecs | grep opus`.
If using terminal() directly, convert to OGG before sending (see Quick Reference above).

### Output file has .mp3 extension but is actually WAV

ffmpeg WAV-to-MP3 conversion failed and the code fell back to renaming.
Check that ffmpeg has libmp3lame: `ffmpeg -codecs | grep mp3lame`. See pitfall 20.

---

## Setup & Reference Material

Everything below is for environment setup, manual CLI usage, and advanced configuration.
The agent's primary workflow is covered in the Quick Reference above.

## Approach Selection

### Apple Silicon (M1/M2/M3/M4) — Use MLX (Recommended)
- 2-3GB RAM vs 10+GB for PyTorch
- 40-50C vs 80-90C CPU temperature
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
- See `references/pytorch_mps_example.md` for code example

## Step 1: Environment Setup

### MLX Approach (Apple Silicon)

```bash
conda create -n qwen3-tts python=3.12 -y
conda activate qwen3-tts
pip install "mlx-audio>=0.3.0,<1.0" "mlx-lm>=0.30.0,<1.0" "transformers>=5.0.0" numpy soundfile
brew install sox ffmpeg
```

### PyTorch Approach (CUDA or MPS fallback)

```bash
conda create -n qwen3-tts python=3.12 -y
conda activate qwen3-tts
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

Models auto-download on first use. Manual download:
```bash
hf download mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  --local-dir ~/Models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit
```

### PyTorch Models

```bash
hf download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
  --local-dir ~/Models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-CustomVoice
```

## Step 3: Generate Speech (CLI)

### MLX — Custom Voice (Preset Speakers)

```bash
python scripts/tts_mlx.py "Hello, this is a test!" \
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
python scripts/tts_mlx.py "Welcome to the future of AI." \
  --mode voice-design \
  --instruct "A deep, calm male narrator with a British accent" \
  --language English \
  --output ~/tts-output/designed.wav
```

### MLX — Voice Cloning

```bash
python scripts/tts_mlx.py "Text to speak in cloned voice." \
  --mode voice-clone \
  --ref-audio /path/to/reference.wav \
  --ref-text "Transcript of the reference audio." \
  --language English \
  --output ~/tts-output/cloned.wav
```

## Step 4: Verify Output

```bash
afplay output.wav          # macOS native playback
ffprobe output.wav         # Check format/duration
```

## Preset Speakers Reference

9 preset speakers (no Spanish/Portuguese/German/French/Russian/Italian presets —
but the model supports all 10 languages using any speaker cross-lingually).

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

For Spanish and other languages without presets: use cross-lingual mode
(`--language Spanish` with any speaker), Voice Design, or Voice Clone.

## Spanish Voices (qwen3-tts-spanish-voices)

The [qwen3-tts-spanish-voices](https://github.com/alblez/qwen3-tts-spanish-voices) project
provides a CLI for Spanish TTS with curated voices (Creative Commons, VoxForge).

### Prerequisites

```bash
conda activate qwen3-tts
cd ~/Code/spanish-tts   # or the path configured in qwen3-tts.spanish-tts-path
pip install -e ".[mlx]"
```

### Quick Reference

```bash
spanish-tts say "Hola, bienvenidos." --voice carlos_mx --play
spanish-tts list                          # List all voices
spanish-tts demo "Texto de prueba."       # Generate with ALL voices
spanish-tts say "Texto." --voice carlos_mx --speed 1.1 --output ~/tts-output/custom.wav
```

### Shipped Voices

| Voice | Gender | Description |
|-------|--------|-------------|
| `neutral_male` (default) | Male | Neutral, clear Latin American accent |
| `neutral_female` | Female | Neutral, clear Latin American accent |
| `energetic_male` | Male | Energetic, cheerful tone |
| `warm_female` | Female | Warm, comforting tone |

Clone voices with better accent fidelity can be added from VoxForge.
See `references/voxforge_curation.md` for the curation pipeline.

### Managing Voices

```bash
spanish-tts add-ref carlos_mx /path/to/audio.wav "Transcripción." --accent mexico --gender male
spanish-tts add-design narrator "A calm 40-year-old male narrator" --gender male
spanish-tts remove carlos_mx
```

Voice registry: `~/.spanish-tts/voices.yaml`. Reference audio: `~/.spanish-tts/references/`.

## Performance Notes

- **RTF (Real-Time Factor)**: ~3.0 on M3 Max for 1.7B PyTorch (slower than real-time)
- MLX 8-bit is significantly faster and lighter than PyTorch MPS
- 0.6B models are ~3x faster than 1.7B with some quality tradeoff
- First run on MPS/MLX is slower due to kernel compilation (29% improvement by run 3)
- Each `conda run` call spawns a new process, reloading the model (~5-15s overhead).
  Expect 20-40s total per TTS call on M1/M2, 15-25s on M3/M4 Max.

## Pitfalls

### Critical

1. **NEVER use device_map="cpu" on Mac** — will hang for 20+ minutes and may never complete
2. **NEVER use float16 on MPS** — use bfloat16 only
18. **qwen-tts (PyTorch) conflicts with mlx-audio/mlx-lm** — `qwen-tts` pins `transformers==4.57.3`, but `mlx-audio`/`mlx-lm` require `transformers>=5.0.0`. They cannot coexist. On Apple Silicon using MLX, do NOT install `qwen-tts`. If accidentally installed: `pip uninstall qwen-tts`.
19. **conda run --no-banner incompatible with conda 25.x** — The `--no-banner` flag does not exist in conda 25.5.1+. Always use `conda run -n <env> <command>` without `--no-banner`.
20. **WAV-to-MP3 rename vs convert** — `spanish-tts say` always outputs WAV. Never rename to .mp3. Always convert: `ffmpeg -y -i input.wav -acodec libmp3lame -b:a 128k output.mp3`.

### Important

3. **flash-attn does NOT compile on Apple Silicon** — skip it, not needed for MLX
6. **MLX models need exact folder names** — HuggingFace repo name must match local dir name
7. **mlx-audio returns generators, not lists** — use `next(iter(results))` not `results[0]`
13. **lang_code is case-insensitive** — both "english" and "English" work (APIs call `.lower()` internally). Convention: MLX docs use lowercase, PyTorch uses capitalized. Either works.
14. **speed parameter accepted but not yet functional** — `model.generate()` accepts `speed=` but silently ignores it. The bundled script adjusts sample rate as a workaround (changes pitch). Do not rely on the API's speed parameter.
15. **VoiceDesign with lang_code="auto" produces English accent** — ALWAYS pass explicit `lang_code="spanish"` (or target language) for VoiceDesign. Clone mode is not affected.
16. **VoiceDesign instruct prompts should stay in ENGLISH** — Spanish instructs cause gender confusion and artifacts. Use English instructs + explicit `lang_code="spanish"`.
17. **VoiceDesign is unreliable for non-English/Chinese accents** — Clone voices using real speaker audio are far superior. Use VoiceDesign only as fallback when no reference audio is available.

### Informational

See `references/pitfalls_informational.md` for lower-severity notes (sox install,
first-inference warmup, deprecated CLI, harmless warnings, cloning tips, datasets torchcodec).

## Advanced: Native text_to_speech() Provider (Optional)

> **This requires a local patch to `tools/tts_tool.py` in hermes-agent.**
> The patch is lost on `hermes update`. For most use cases, the terminal()
> approach in the Quick Reference above is simpler and maintenance-free.

The `qwen3tts` provider wraps `spanish-tts` CLI so that `text_to_speech(text=...)`
uses Qwen3-TTS directly.

Pipeline: `text_to_speech() -> _generate_qwen3tts() -> conda run -> spanish-tts say -> WAV -> ffmpeg -> MP3/OGG`

Config in `config.yaml`:
```yaml
tts:
  provider: qwen3tts
  qwen3tts:
    voice: carlos_mx       # male Mexican Spanish (default)
    speed: 1.0             # synthesis speed multiplier
    conda_env: qwen3-tts   # conda environment name
```

Key details:
- 120-second subprocess timeout (typical synthesis: 15-30s on M-series Max)
- Validates exit code and output file existence/size
- Converts WAV to MP3 via ffmpeg; falls back with warning if ffmpeg fails
- Edge TTS available as fallback by setting `provider: edge`
- **Does NOT use the hermes terminal backend** — always runs locally

Full patch code and re-application steps: see `references/tts_tool_provider_patch.md`.

## MLX API Reference

See `references/mlx_api_reference.md` for Python code examples covering all three
modes (custom voice, voice design, voice clone) with the mlx-audio API.

## Sources

- Official: https://qwen.ai/blog?id=qwen3-tts-1128
- HuggingFace: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- Apple Silicon MLX: https://github.com/kapi2800/qwen3-tts-apple-silicon
- MLX Audio: https://github.com/Blaizzy/mlx-audio
- Spanish Voices: https://github.com/alblez/qwen3-tts-spanish-voices
- Benchmark: https://tinycomputers.io/posts/the-real-cost-of-running-qwen-tts-locally-three-machines-compared.html
- MPS fix: https://github.com/QwenLM/Qwen3-TTS/issues/69

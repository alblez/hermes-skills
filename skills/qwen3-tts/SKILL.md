---
name: qwen3-tts
version: 1.2.0
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
| Base 1.7B (Clone) | mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit | mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit |
| Base 0.6B (Clone) | mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit | mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit |

Download manually:
```bash
huggingface-cli download mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit \
  --local-dir ~/Models/qwen3-tts/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit
```

Models auto-download on first use if not pre-cached.

### PyTorch Models

```bash
huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
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

model = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit")

# Voice cloning (Base model)
results = model.generate(
    text="Texto a sintetizar.",
    lang_code="auto",        # auto-detects language from text
    ref_audio="/path/to/reference.wav",
    ref_text="Transcripción exacta del audio de referencia.",
    speed=1.0,
)

# Voice design (VoiceDesign model)
# IMPORTANT: always pass explicit lang_code for non-English targets
# Keep instruct in English — Spanish instructs cause gender/quality issues
results = model.generate(
    text="Texto en español.",
    lang_code="spanish",     # NEVER use "auto" — causes English accent
    instruct="A warm 30-year-old male with calm tone",
    speed=1.0,
)

# Custom voice (CustomVoice model)
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

**WRONG methods** (do NOT use):
- `model.generate_voice_clone()` — does NOT exist
- `model.generate_voice_design()` — exists but `model.generate(instruct=...)` is preferred

## Spanish Voice References

The `ciempiess/voxforge_spanish` HuggingFace dataset (21,692 samples) provides good
clone references. Countries available: spain (16K), argentina (1.7K), latin_america (1.6K),
mexico (758), chile (719). No Colombian speakers.

## Companion Project: qwen3-tts-spanish-voices

The [qwen3-tts-spanish-voices](https://github.com/alblez/qwen3-tts-spanish-voices) repo
provides 14 pre-curated Spanish voices (12 clones + 2 designs) as a ready-to-use CLI tool.
Clone voices cover: Spain, Mexico, Argentina, Ibero-America (neutral LatAm), Chile.
Design voices kept only where near-native quality achieved (neutral_male, energetic_male).
Install it with `pip install -e ".[mlx]"` and use `spanish-tts say "Hola"` for quick generation.
Local path: `~/Code/spanish-tts` (or `~/Code/qwen3-tts-spanish-voices` if renamed on disk).

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
14. **speed parameter is built into generate()** — no need for sample rate manipulation
15. **VoiceDesign with lang_code="auto" produces English accent** — "auto" skips the codec language token entirely, so the model defaults to English prosody (especially when the instruct prompt is in English). ALWAYS pass explicit `lang_code="spanish"` (or target language) for VoiceDesign. Clone mode is not affected because the reference audio provides the acoustic prior.
16. **VoiceDesign instruct prompts should stay in ENGLISH, not the target language** — the model was trained primarily on English/Chinese voice descriptions. Writing instructs in Spanish causes severe gender confusion (male->female, female->male) and anime-like artifacts. Use English instructs + explicit `lang_code="spanish"` for best results. Even so, VoiceDesign produces "American TTS reading Spanish" prosody for most voices — only ~1 in 4 designs sounds near-native. For reliable native accent, always prefer voice cloning (Base model + reference audio).
17. **VoiceDesign is unreliable for non-English/Chinese native accents** — the model fundamentally cannot produce native Spanish (or likely other non-English) prosody from text descriptions alone. Clone voices using real speaker audio are far superior for accent fidelity. Use VoiceDesign only as a fallback when no reference audio is available, and expect English-accented output.

## Sources

- Official: https://qwen.ai/blog?id=qwen3-tts-1128
- HuggingFace: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- Apple Silicon MLX: https://github.com/kapi2800/qwen3-tts-apple-silicon
- MLX Audio: https://github.com/Blaizzy/mlx-audio
- Benchmark: https://tinycomputers.io/posts/the-real-cost-of-running-qwen-tts-locally-three-machines-compared.html
- MPS fix: https://github.com/QwenLM/Qwen3-TTS/issues/69

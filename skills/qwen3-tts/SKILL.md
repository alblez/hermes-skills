---
name: qwen3-tts
version: 1.0.0
description: >
  Run Qwen3-TTS text-to-speech locally on Apple Silicon (MLX preferred)
  or GPU/CPU (PyTorch). Supports voice cloning, voice design, and preset
  custom voices. 10 languages, 3-second voice cloning, emotional control.
tags: [tts, speech, voice-cloning, voice-design, mlx, apple-silicon, qwen]
triggers:
  - text to speech
  - TTS
  - voice cloning
  - voice synthesis
  - qwen tts
  - generate speech
  - speak this text
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

Use the bundled script: `scripts/tts_mlx.py`

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

## Performance Notes

- **RTF (Real-Time Factor)**: ~3.0 on M3 Max for 1.7B PyTorch (slower than real-time)
- MLX 8-bit is significantly faster and lighter than PyTorch MPS
- 0.6B models are ~3x faster than 1.7B with some quality tradeoff
- First run on MPS/MLX is slower due to kernel compilation (29% improvement by run 3)
- For faster-than-realtime TTS, consider F5-TTS (0.64 RTF) as alternative

## Pitfalls

1. **NEVER use device_map="cpu" on Mac** — will hang for 20+ minutes and may never complete
2. **NEVER use float16 on MPS** — use bfloat16 only
3. **flash-attn does NOT compile on Apple Silicon** — skip it, not needed for MLX
4. **sox must be installed** — `brew install sox` or audio processing will fail
5. **First inference is slow** — kernel compilation warmup, subsequent runs faster
6. **MLX models need exact folder names** — HuggingFace repo name must match local dir name
9. **mlx-audio returns generators, not lists** — use `next(iter(results))` not `results[0]`
10. **huggingface-cli is deprecated** — use `hf download` instead
11. **Warnings about tokenizer regex and model type are harmless** — they don't affect generation quality
7. **For voice cloning**: reference audio should be 5-10s, clean (no background noise)
8. **The `--instruct` flag**: controls emotion/prosody for CustomVoice, is REQUIRED for VoiceDesign

## Sources

- Official: https://qwen.ai/blog?id=qwen3-tts-1128
- HuggingFace: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- Apple Silicon MLX: https://github.com/kapi2800/qwen3-tts-apple-silicon
- MLX Audio: https://github.com/Blaizzy/mlx-audio
- Benchmark: https://tinycomputers.io/posts/the-real-cost-of-running-qwen-tts-locally-three-machines-compared.html
- MPS fix: https://github.com/QwenLM/Qwen3-TTS/issues/69

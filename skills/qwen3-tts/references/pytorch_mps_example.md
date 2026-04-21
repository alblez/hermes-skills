# PyTorch MPS Fallback (Apple Silicon)

Use this approach only when MLX is not available. MLX is significantly faster
and lighter (2-3GB RAM vs 10+GB, 40-50C vs 80-90C).

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

## Key Differences from MLX

- PyTorch returns `(wavs, sr)` tuple (list of numpy arrays + sample rate)
- MLX returns generators — use `next(iter(results))` to get first result
- PyTorch has `generate_voice_clone()` method; MLX does not (use `generate(ref_audio=...)`)
- PyTorch supports `create_voice_clone_prompt()` for reusable voice prompts

## PyTorch-Specific Methods

```python
# Voice clone (PyTorch only — this method does NOT exist in MLX)
model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", ...)
wavs, sr = model.generate_voice_clone(
    text="Text to speak.",
    language="English",
    ref_audio="reference.wav",
    ref_text="Transcript of reference.",
)

# Reusable clone prompt (PyTorch only)
prompt = model.create_voice_clone_prompt(ref_audio="ref.wav", ref_text="transcript")
wavs, sr = model.generate_voice_clone(text="New text.", voice_clone_prompt=prompt)
```

## WARNING

Do NOT install `qwen-tts` (PyTorch) in the same conda env as `mlx-audio`.
They have conflicting `transformers` version requirements. See pitfall 18.

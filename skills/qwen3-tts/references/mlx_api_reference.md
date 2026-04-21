# MLX API Reference (mlx-audio)

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
    language="english",      # case-insensitive (both "english" and "English" work)
)

# All return generators:
first_result = next(iter(results))
audio_np = np.array(first_result.audio)
sf.write("out.wav", audio_np, model.sample_rate)
```

## Method Availability

- `model.generate_voice_clone()` — does NOT exist; use `model.generate(ref_audio=..., ref_text=...)` instead
- `model.generate_voice_design()` — exists and works; `model.generate(instruct=...)` also works as an alternative
- `model.generate_custom_voice()` — exists and works; the standard method for preset speakers

## Parameter Naming

- `model.generate()` uses `lang_code=` for the language parameter
- `model.generate_custom_voice()` and `model.generate_voice_design()` use `language=`
- Both are case-insensitive (the API calls `.lower()` internally)

## Not Yet Documented in This Skill

- **Streaming**: `stream=True` parameter on `generate()`, `generate_custom_voice()`, `generate_voice_design()`
- **Batch generation**: `model.batch_generate(texts=[...])` for parallel synthesis
- **Additional quantizations**: mlx-community hosts 5-bit, 6-bit, and bf16 variants beyond 4/8-bit

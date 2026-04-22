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

- **Batch generation**: `model.batch_generate(texts=[...])` for parallel synthesis
- **Additional quantizations**: mlx-community hosts 5-bit, 6-bit, and bf16 variants beyond 4/8-bit

## Streaming

All generate methods support `stream=True` for incremental decoding:

```python
# Streaming — yields ~2-second audio chunks as they generate
for chunk in model.generate(text="Long text...", lang_code="english", stream=True):
    audio = np.array(chunk.audio)
    print(f"Chunk: {chunk.samples} samples, final={chunk.is_final_chunk}")

# Also works with custom voice and voice design:
for chunk in model.generate_custom_voice(text="...", speaker="Ryan", language="english", stream=True):
    ...
for chunk in model.generate_voice_design(text="...", instruct="...", language="english", stream=True):
    ...
```

Parameters:
- `stream: bool = False` — enable streaming decode
- `streaming_interval: float = 2.0` — seconds of audio per chunk (25 codec tokens at 12.5 Hz)

Each chunk is a `GenerationResult` with:
- `audio` — `mx.array` float32, 24kHz sample rate
- `samples` — number of samples in this chunk (~48,000 for 2.0s interval)
- `is_streaming_chunk` — `True` for streaming chunks
- `is_final_chunk` — `True` for the last chunk of a segment

The streaming decoder uses stateful `streaming_step()` with conv buffers and
transformer KV cache — it processes only new tokens incrementally, not re-decoding
from scratch. Memory stays flat regardless of text length.

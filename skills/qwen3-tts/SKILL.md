---
name: qwen3-tts
version: 1.6.0
description: >
  Run Qwen3-TTS text-to-speech locally on Apple Silicon (MLX).
  Spanish-optimized CLI with curated voice registry; 9 other languages
  supported via bundled MLX script. Voice cloning, voice design, and
  preset custom voices. 3-second voice cloning, emotional control.
author: Alberto Gonzalez Rouille
license: Apache-2.0
platforms: [macos]
metadata:
  hermes:
    tags: [tts, speech, voice-cloning, voice-design, mlx, apple-silicon, qwen]
    config:
      - key: qwen3-tts.spanish-tts-path
        description: "Path to the qwen3-tts-spanish-voices repository clone"
        default: "~/.qwen3-tts-spanish-voices"
        prompt: "Spanish TTS repo path"
      - key: qwen3-tts.run-prefix
        description: "Command prefix to run tools in the TTS environment (conda run, venv path, etc.)"
        default: "conda run -n qwen3-tts"
        prompt: "Environment run prefix (e.g., 'conda run -n qwen3-tts' or '/path/to/venv/bin/')"
required_environment_variables: []
# Optional env vars (both have defaults, do NOT list as required):
#   QWEN_TTS_OUTPUT_DIR — defaults to ~/tts-output/
#   QWEN_TTS_MODEL — defaults to recommended 8-bit MLX model per mode
---

# Qwen3-TTS Local Inference

Local TTS on Apple Silicon via MLX. Three modes: preset speakers (CustomVoice),
voice descriptions (VoiceDesign), and 3-second voice cloning (Base). 10 languages.

## When to Use

- User asks to convert text to speech or generate audio from text
- User wants to clone a voice from a reference audio sample
- User wants to design a custom voice from a natural language description
- User needs multilingual speech synthesis (especially CJK + European languages)

## Hermes Agent Quick Reference

> **`${RUN_PREFIX}`** in commands below refers to the `qwen3-tts.run-prefix` skill
> config value (default: `conda run -n qwen3-tts`). For venv/uv setups, configure
> it to the environment's bin path (e.g., `/path/to/venv/bin/`).

### Primary method: MCP

If the MCP server is configured (see MCP Server Setup below), Hermes calls
`mcp_spanish-tts_say` directly. The model stays loaded across calls, eliminating
the 5-15s cold start of `conda run`.

```
mcp_spanish-tts_say(text="Texto en español", voice="carlos_mx")
```

The tool returns `{ "path": "/path/to/output.wav", "duration_seconds": 3.2 }`.
Convert the WAV for delivery as needed (MP3, OGG for Telegram).

For long texts (>50 words), pass `stream=True` for lower memory usage:
```
mcp_spanish-tts_say(text="Long text here...", voice="carlos_mx", stream=True)
```
Output format is identical. Streaming uses incremental decoding internally.

### Fallback: terminal()

If the MCP server is not running, use `terminal()` directly:

```bash
${RUN_PREFIX} spanish-tts say -v carlos_mx -o /tmp/output.wav "Texto en español"
```

To convert WAV to MP3 (for non-Telegram delivery):
```bash
${RUN_PREFIX} spanish-tts say -v carlos_mx -o /tmp/out.wav "Texto" && \
  ffmpeg -y -i /tmp/out.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -acodec libmp3lame -b:a 192k /tmp/out.mp3
```

For Telegram voice bubbles (Opus-in-OGG):
```bash
${RUN_PREFIX} spanish-tts say -v carlos_mx -o /tmp/out.wav "Texto" && \
  ffmpeg -y -i /tmp/out.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a libopus -b:a 64k /tmp/out.ogg
```

### Voice selection

- **Default (male)**: `carlos_mx` — Mexican Spanish, most tested
- **Female voice**: `lucia_es` — use when the user says "voz femenina" or context implies female
- **List all voices**: `${RUN_PREFIX} spanish-tts list`
- For one-off voice changes, pass `-v <voice_name>` in the terminal() command

### For non-Spanish languages

Use the bundled MLX script directly (the `spanish-tts` CLI is Spanish-only):

```bash
${RUN_PREFIX} python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Hello world!" \
  --speaker Ryan --language English -o /tmp/english.wav
```

To convert WAV to MP3:
```bash
${RUN_PREFIX} python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Hello world!" \
  --speaker Ryan --language English -o /tmp/out.wav && \
  ffmpeg -y -i /tmp/out.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -acodec libmp3lame -b:a 192k /tmp/out.mp3
```

For Telegram voice bubbles (Opus-in-OGG):
```bash
${RUN_PREFIX} python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py "Hello world!" \
  --speaker Ryan --language English -o /tmp/out.wav && \
  ffmpeg -y -i /tmp/out.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a libopus -b:a 64k /tmp/out.ogg
```

Script path: `${HERMES_SKILL_DIR}/scripts/tts_mlx.py` (resolved automatically when the skill loads).

## Troubleshooting

### TTS command produces no output or wrong voice

1. Check conda env exists: `conda env list | grep qwen3-tts`
2. Test CLI directly: `${RUN_PREFIX} spanish-tts say -v carlos_mx -o /tmp/test.wav "Hola mundo"`
3. Check the WAV: `file /tmp/test.wav` — should show `RIFF ... WAVE audio`
4. If `conda run` fails, check conda version: `conda --version` (25.x removed `--no-banner` — see pitfall 4)

### text_to_speech() silently falls back to Edge TTS

If the `qwen3tts` provider is patched but failing, `tts_tool.py`'s broad try/except
may fall through to Edge TTS without logging. Check hermes logs for "Qwen3-TTS" vs
"Edge TTS" to confirm which provider was actually used.

### Telegram sends audio but it doesn't play as voice bubble

Telegram requires Opus-in-OGG. Ensure ffmpeg has libopus: `ffmpeg -codecs | grep opus`.
If using terminal() directly, convert to OGG before sending (see Quick Reference above).

### Output file has .mp3 extension but is actually WAV

ffmpeg WAV-to-MP3 conversion failed and the code fell back to renaming.
Check that ffmpeg has libmp3lame: `ffmpeg -codecs | grep mp3lame`. See pitfall 5.

---

## Setup & Reference Material

Everything below is for environment setup, manual CLI usage, and advanced configuration.
The agent's primary workflow is covered in the Quick Reference above.

## MCP Server Setup

### Installation

```bash
conda activate qwen3-tts
cd ~/.qwen3-tts-spanish-voices   # or the path configured in qwen3-tts.spanish-tts-path
pip install -e ".[mlx,mcp]"
```

### Register with Hermes

```bash
hermes mcp add spanish-tts --command "conda run -n qwen3-tts python -m spanish_tts.mcp_server"
```

Or add directly to `config.yaml`:
```yaml
mcp_servers:
  spanish-tts:
    command: ["conda", "run", "-n", "qwen3-tts", "python", "-m", "spanish_tts.mcp_server"]
```

> For non-conda environments, adjust the `command` array to point to your
> environment's Python, e.g.: `["/path/to/venv/bin/python", "-m", "spanish_tts.mcp_server"]`

### Verify

```bash
# Check the server starts
conda run -n qwen3-tts python -m spanish_tts.mcp_server --help

# Test via Hermes
hermes chat -q "List the available Spanish TTS voices"
```

Once configured, Hermes exposes `mcp_spanish-tts_say`, `mcp_spanish-tts_list_all_voices`,
and `mcp_spanish-tts_demo` as native tools. See `references/future_work.md` for the
full implementation plan and server source code.

## Approach Selection

### Resource Requirements

- **Disk**: ~2.9 GB per model variant (8-bit). Using all three modes (clone + design + custom voice) caches ~8.7 GB in `~/.cache/huggingface/hub/`.
- **RAM**: ~2.5-3 GB resident per loaded model (1.7B-8bit). The 0.6B variants use ~1.2-1.5 GB.
- **First run**: Model downloads automatically on first use (~2-5 min on fast connection). First inference after download includes kernel compilation (~3-5s extra, one-time).
- **MCP server start**: ~5-10s for model preload. Subsequent tool calls complete in 2-5s.
- **Offline**: Fully offline after initial model download. No network calls during inference.

### Apple Silicon (M1/M2/M3/M4) — Use MLX (Recommended)
- 2-3GB RAM vs 10+GB for PyTorch
- Typically 15-25C cooler than PyTorch MPS for single TTS calls
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

**Quick setup** (recommended): Run the bundled install script:
```bash
bash ${HERMES_SKILL_DIR}/scripts/install.sh
```
This creates the conda env, installs all dependencies, sets up the spanish-tts
CLI, and configures the MCP server. Run `bash ${HERMES_SKILL_DIR}/scripts/install.sh --help` for options.

**Manual setup** (if you prefer step-by-step):

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

### Choosing a Voice

- **English**: Use preset `Ryan` (dynamic male) or `Aiden` (sunny male)
- **Spanish**: Use `spanish-tts` CLI with curated voices (`carlos_mx`, `lucia_es`, etc.)
- **Chinese**: Use preset `Vivian` (female), `Serena` (female), or `Uncle_Fu` (male)
- **Japanese**: Use preset `Ono_Anna` (female)
- **Korean**: Use preset `Sohee` (female)
- **Other languages** (German, French, Russian, Portuguese, Italian): Use any preset
  with `--language <target>` for cross-lingual synthesis, or use `--mode voice-clone`
  with native-language reference audio for best accent fidelity.
- **Custom persona**: Use `--mode voice-design --instruct "description"` (best for
  English/Chinese; unreliable accents for other languages -- see pitfall 13)

9 preset speakers (no Spanish/Portuguese/German/French/Russian/Italian presets --
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

### Cross-Lingual Voice Cloning

Qwen3-TTS can clone a voice in one language and synthesize speech in another.
The `--language` flag controls the **output** language, not the reference language.

Example -- clone a Korean speaker's voice, output in Spanish:
```bash
${RUN_PREFIX} python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py \
  "Hola, esto es una prueba de clonacion." \
  --mode voice-clone \
  --ref-audio /path/to/korean_speaker.wav \
  --ref-text "한국어 텍스트 여기에." \
  --language Spanish \
  -o /tmp/cross_lingual.wav
```

Quality is roughly 85-90% of same-language cloning. Expect subtle accent bleed
from the reference language into the target. For languages without preset speakers,
cross-lingual cloning with native reference audio produces better accents than
VoiceDesign.

## Spanish Voices (qwen3-tts-spanish-voices)

The [qwen3-tts-spanish-voices](https://github.com/alblez/qwen3-tts-spanish-voices) project
provides a CLI for Spanish TTS with curated voices (Creative Commons, VoxForge).

### Prerequisites

```bash
conda activate qwen3-tts
cd ~/.qwen3-tts-spanish-voices   # or the path configured in qwen3-tts.spanish-tts-path
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
  Expect 8-16s total per TTS call on M-series Max, 15-25s on M1/M2 base.
  With MCP server (model stays loaded): 2-5s per call.

## Pitfalls

### Critical

1. **NEVER use device_map="cpu" on Mac** — will hang for 20+ minutes and may never complete
2. **NEVER use float16 on MPS** — use bfloat16 only
3. **qwen-tts (PyTorch) conflicts with mlx-audio/mlx-lm** — `qwen-tts` pins `transformers==4.57.3`, but `mlx-audio`/`mlx-lm` require `transformers>=5.0.0`. They cannot coexist. On Apple Silicon using MLX, do NOT install `qwen-tts`. If accidentally installed: `pip uninstall qwen-tts`.
4. **conda run --no-banner incompatible with conda 25.x** — The `--no-banner` flag does not exist in conda 25.5.1+. Always use `conda run -n <env> <command>` without `--no-banner`.
5. **WAV-to-MP3 rename vs convert** — `spanish-tts say` always outputs WAV. Never rename to .mp3. Always convert: `ffmpeg -y -i input.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -acodec libmp3lame -b:a 192k output.mp3`.

### Important

6. **flash-attn does NOT compile on Apple Silicon** — skip it, not needed for MLX
7. **MLX models need exact folder names** — HuggingFace repo name must match local dir name
8. **mlx-audio returns generators, not lists** — use `next(iter(results))` not `results[0]`
9. **lang_code is case-insensitive** — both "english" and "English" work (APIs call `.lower()` internally). Convention: MLX docs use lowercase, PyTorch uses capitalized. Either works.
10. **speed parameter accepted but not yet functional** — `model.generate()` accepts `speed=` but silently ignores it. The bundled script uses librosa time-stretch as a workaround (falls back to sample rate change if librosa is not installed). Do not rely on the API's speed parameter.
11. **VoiceDesign with lang_code="auto" produces English accent** — ALWAYS pass explicit `lang_code="spanish"` (or target language) for VoiceDesign. Clone mode is not affected.
12. **VoiceDesign instruct prompts should stay in ENGLISH** — Spanish instructs cause gender confusion and artifacts. Use English instructs + explicit `lang_code="spanish"`.
13. **VoiceDesign is unreliable for non-English/Chinese accents** — Clone voices using real speaker audio are far superior. Use VoiceDesign only as fallback when no reference audio is available.

### Informational

14. **Harmless Mistral regex warning** — Every generation prints `"incorrect regex pattern... fix_mistral_regex=True"`. This is a tokenizer compatibility notice from HuggingFace, not a real error. Ignore it.
15. **Model type mismatch warning** — Every generation prints `"model of type qwen3_tts to instantiate a model of type ''"`. Harmless HuggingFace warning. Ignore it.
16. **Empty text silently generates audio** — The `spanish-tts` CLI does not validate empty input. Passing `""` produces a ~0.8s WAV of silence/noise. The MCP server validates and rejects empty text.
17. **"Fetching N files" progress bar on cached models** — Appears on every run even when the model is already downloaded. HuggingFace Hub checking for updates. Harmless but noisy.

See `references/pitfalls_informational.md` for additional lower-severity notes (sox install,
first-inference warmup, deprecated CLI, cloning tips, datasets torchcodec).

## Verification

Manual smoke test (requires completed setup):
```bash
${RUN_PREFIX} python ${HERMES_SKILL_DIR}/scripts/tts_mlx.py \
  "Hello, this is a test." --speaker Ryan --language English \
  -o /tmp/qwen3_tts_verify.wav && afplay /tmp/qwen3_tts_verify.wav
```

Via Hermes:
```bash
hermes chat --toolsets skills -q "Say 'Hello world' using the qwen3-tts skill"
```

Expected: a WAV file with audible English speech in Ryan's voice.

## Advanced: Native text_to_speech() Provider

> This approach requires patching hermes-agent internals and is lost on
> `hermes update`. It is superseded by the MCP server plan in
> `references/future_work.md`. For details see
> `references/tts_tool_provider_patch.md`.

## MLX API Reference

See `references/mlx_api_reference.md` for Python code examples covering all three
modes (custom voice, voice design, voice clone) with the mlx-audio API.

## Uninstall

Remove the conda environment and cached models:
```bash
# Remove conda env (~500 MB)
conda env remove -n qwen3-tts

# Remove cached HuggingFace models (~2.9 GB per variant)
rm -rf ~/.cache/huggingface/hub/models--mlx-community--Qwen3-TTS-*

# Remove MCP server config from ~/.hermes/config.yaml
# (delete the spanish-tts entry under mcp_servers)

# Remove spanish-tts voice registry (optional)
rm -rf ~/.spanish-tts
```

## Sources

- Official: https://qwen.ai/blog?id=qwen3-tts-1128
- HuggingFace: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- Apple Silicon MLX: https://github.com/kapi2800/qwen3-tts-apple-silicon
- MLX Audio: https://github.com/Blaizzy/mlx-audio
- Spanish Voices: https://github.com/alblez/qwen3-tts-spanish-voices
- Benchmark: https://tinycomputers.io/posts/the-real-cost-of-running-qwen-tts-locally-three-machines-compared.html
- MPS fix: https://github.com/QwenLM/Qwen3-TTS/issues/69

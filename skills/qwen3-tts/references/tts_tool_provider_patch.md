# Hermes tts_tool.py — qwen3tts Provider Patch

## Context

This documents the local modifications applied to hermes-agent's `tools/tts_tool.py`
to add native `qwen3tts` provider support. These changes are local to the hermes-agent
installation and will be lost on the next `hermes update`. Re-apply this patch after
updating.

Long-term, this should be upstreamed as a PR to hermes-agent.

---

## Bug 1: `--no-banner` flag removed in conda 25.x

### Problem

`conda run --no-banner -n qwen3-tts spanish-tts say ...` exits with code 2:

```
conda: error: unrecognized arguments: --no-banner
```

The `--no-banner` flag was removed in conda 25.x. The command fails before
`spanish-tts` is ever invoked.

### Fix

Remove `--no-banner` from the subprocess command:

```python
# BEFORE (broken on conda 25.x):
cmd = [
    "conda", "run", "--no-banner", "-n", conda_env,
    "spanish-tts", "say",
    "-v", voice,
    "-o", wav_path,
]

# AFTER (works on all conda versions):
cmd = [
    "conda", "run", "-n", conda_env,
    "spanish-tts", "say",
    "-v", voice,
    "-o", wav_path,
]
```

---

## Bug 2: WAV file renamed to .mp3 instead of properly converted

### Problem

`spanish-tts say` always outputs WAV (PCM). When the caller requests `.mp3` output,
the original code used `os.rename()` to change the extension — producing a file with
`.mp3` extension but WAV content. This breaks:

- `file` reports `RIFF (little-endian) data, WAVE audio` despite .mp3 extension
- Telegram `_convert_to_opus()` may fail or produce garbled audio
- Any tool expecting MP3 framing will break

### Fix

Use ffmpeg to transcode WAV to MP3, with rename as fallback:

```python
# BEFORE (broken — just renames):
if wav_path != output_path:
    os.rename(wav_path, output_path)

# AFTER (proper conversion):
if wav_path != output_path:
    convert_result = subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-acodec", "libmp3lame",
         "-b:a", "128k", output_path],
        capture_output=True, timeout=30,
    )
    if convert_result.returncode != 0:
        # Fallback: just rename (WAV with wrong extension, but at least audible)
        os.rename(wav_path, output_path)
    else:
        os.remove(wav_path)
```

---

## Full Provider: `_generate_qwen3tts()` function

Add this function to `tools/tts_tool.py` (around line 686, before `text_to_speech_tool`):

```python
def _generate_qwen3tts(text: str, output_path: str, tts_config: dict) -> str:
    """Generate speech using Qwen3-TTS via spanish-tts CLI (conda subprocess)."""
    import re
    import shutil
    import subprocess
    from pathlib import Path

    qwen3_cfg = tts_config.get("qwen3tts", {})
    voice = qwen3_cfg.get("voice", "carlos_mx")
    speed = float(qwen3_cfg.get("speed", 1.0))
    conda_env = qwen3_cfg.get("conda_env", "qwen3-tts")

    # Input validation
    if not re.match(r'^[a-zA-Z0-9_-]+$', conda_env):
        raise ValueError(f"Invalid conda_env name: {conda_env!r}")
    if not re.match(r'^[a-zA-Z0-9_-]+$', voice):
        raise ValueError(f"Invalid voice name: {voice!r}")
    if not (0.25 <= speed <= 4.0):
        raise ValueError(f"Speed out of range (0.25-4.0): {speed}")

    # spanish-tts always outputs WAV; we convert afterward if needed
    output = Path(output_path)
    if output.suffix == ".wav":
        wav_path = str(output)
    else:
        wav_path = str(output.with_suffix(".wav"))

    cmd = [
        "conda", "run", "-n", conda_env,
        "spanish-tts", "say",
        "-v", voice,
        "-o", wav_path,
    ]

    if not math.isclose(speed, 1.0):
        cmd.extend(["--speed", str(speed)])

    # Text goes last as positional argument
    cmd.append(text)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # MLX on M1 Max takes ~15-30s for typical paragraphs
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Qwen3-TTS: 'conda' not found on PATH. "
            "Install Miniconda/Miniforge or ensure conda is on PATH."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Qwen3-TTS: synthesis timed out after 120 seconds")

    if result.returncode != 0:
        raise RuntimeError(
            f"Qwen3-TTS failed (exit {result.returncode}): {result.stderr[:500]}"
        )

    # Verify output
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
        raise RuntimeError(
            f"Qwen3-TTS: output file missing or empty at {wav_path}"
        )

    # Convert WAV to target format if needed
    if wav_path != output_path:
        try:
            convert_result = subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-acodec", "libmp3lame",
                 "-b:a", "128k", output_path],
                capture_output=True, timeout=30,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Qwen3-TTS: 'ffmpeg' not found. Install with: brew install ffmpeg"
            )
        if convert_result.returncode != 0:
            # Fallback: move WAV to output path (wrong extension but audible)
            logger.warning(
                f"ffmpeg WAV→MP3 failed (exit {convert_result.returncode}), "
                f"returning WAV with {output.suffix} extension"
            )
            shutil.move(wav_path, output_path)
        else:
            os.remove(wav_path)

    return output_path
```

---

## Provider branch in `text_to_speech_tool()`

Add this `elif` branch in the provider dispatch section of `text_to_speech_tool()`:

```python
elif provider == "qwen3tts":
    try:
        output_path = _generate_qwen3tts(text, output_path, tts_config)
        logger.info(f"Qwen3-TTS generated: {output_path}")
    except RuntimeError as e:
        logger.error(f"Qwen3-TTS failed: {e}")
        raise
```

Also add `"qwen3tts"` to the Opus auto-conversion list for Telegram compatibility
(wherever the code checks provider for Opus conversion).

---

## Re-application Steps

After running `hermes update`:

1. Open `tools/tts_tool.py` in the hermes-agent installation
2. Add the `_generate_qwen3tts()` function before `text_to_speech_tool()`
3. Add the `elif provider == "qwen3tts"` branch in the provider dispatch
4. Add `"qwen3tts"` to the Opus auto-conversion list
5. Verify config.yaml has the `tts.qwen3tts` section
6. Test: `text_to_speech(text="Hola mundo", output_path="/tmp/test.mp3")`

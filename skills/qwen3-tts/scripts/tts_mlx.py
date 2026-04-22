#!/usr/bin/env python3
"""
Qwen3-TTS MLX Inference Script for Apple Silicon.

Last verified: mlx-audio 0.4.2, mlx-lm 0.31.1, transformers 5.5.4 (Apr 2026)

Supports three modes:
  - custom-voice: Use preset speakers with emotion/style control
  - voice-design: Create voices from natural language descriptions
  - voice-clone: Clone voices from reference audio

Usage:
  python tts_mlx.py "Hello world!" --speaker Ryan --language English
  python tts_mlx.py "Text" --mode voice-design --instruct "A calm British narrator"
  python tts_mlx.py "Text" --mode voice-clone --ref-audio ref.wav --ref-text "transcript"

Environment Variables:
  QWEN_TTS_OUTPUT_DIR  - Output directory (default: ~/tts-output/)
  QWEN_TTS_MODEL       - Model ID override (default depends on mode)

Requirements:
  pip install "mlx-audio>=0.3.0,<1.0" "mlx-lm>=0.30.0,<1.0" "transformers>=5.0.0" numpy soundfile
"""

import argparse
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf


# Model matrix: {mode: {variant: model_id}}
# VoiceDesign has no 0.6B variant — only 1.7B.
_MODEL_MATRIX = {
    "custom-voice": {
        "0.6B-4bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit",
        "0.6B-8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
        "1.7B-4bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-4bit",
        "1.7B-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    },
    "voice-design": {
        "1.7B-4bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-4bit",
        "1.7B-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
    },
    "voice-clone": {
        "0.6B-4bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
        "0.6B-8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit",
        "1.7B-4bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit",
        "1.7B-8bit": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit",
    },
}

# Default speakers per language
DEFAULT_SPEAKERS = {
    "Chinese": "Vivian",
    "English": "Ryan",
    "Japanese": "Ono_Anna",
    "Korean": "Sohee",
}

# Model cache — inert under `conda run` (new process per call).
# Becomes active when this module is imported by a long-lived process
# (e.g., the MCP server planned in references/future_work.md).
_model_cache = {}

# Tested library versions — warn if different
_TESTED_VERSIONS = {"mlx-audio": "0.4.2", "mlx-lm": "0.31.1"}


def _get_system_ram_gb() -> int:
    """Detect system RAM in GB (macOS only, returns 0 on failure)."""
    import subprocess
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip()) // (1024 ** 3)
    except Exception:
        pass
    return 0


def _resolve_default_model(mode: str) -> str:
    """Select model variant based on system RAM.

    Tiers:
        <= 8 GB  -> 0.6B-4bit (VoiceDesign: 1.7B-4bit with warning)
        9-16 GB  -> 1.7B-4bit
        >= 24 GB -> 1.7B-8bit
    """
    ram_gb = _get_system_ram_gb()
    variants = _MODEL_MATRIX[mode]

    if ram_gb <= 8:
        target = "0.6B-4bit"
        if target not in variants:
            # VoiceDesign has no 0.6B — fall back to 1.7B-4bit
            target = "1.7B-4bit"
            print(f"  NOTE: {mode} has no 0.6B model. Using 1.7B-4bit on {ram_gb}GB RAM "
                  f"(~850MB resident). Monitor memory pressure.", file=sys.stderr)
        else:
            print(f"  Auto-selected {target} for {ram_gb}GB RAM", file=sys.stderr)
    elif ram_gb <= 16:
        target = "1.7B-4bit"
        print(f"  Auto-selected {target} for {ram_gb}GB RAM", file=sys.stderr)
    else:
        target = "1.7B-8bit"
        # No message for the happy path (>=24GB)

    if target not in variants:
        # Shouldn't happen, but fall back to first available
        target = next(iter(variants))
        print(f"  WARNING: Falling back to {target}", file=sys.stderr)

    return variants[target]


def check_versions():
    """Warn if library versions differ from tested."""
    import importlib.metadata
    # Detect conflicting PyTorch package
    try:
        qwen_tts_ver = importlib.metadata.version("qwen-tts")
        print(f"ERROR: qwen-tts {qwen_tts_ver} is installed and conflicts with mlx-audio "
              f"(pins transformers 4.x). Run: pip uninstall qwen-tts", file=sys.stderr)
        sys.exit(1)
    except importlib.metadata.PackageNotFoundError:
        pass  # Good — no conflict
    for pkg, tested_ver in _TESTED_VERSIONS.items():
        try:
            actual = importlib.metadata.version(pkg)
            if actual != tested_ver:
                print(f"WARNING: {pkg} {actual} (tested with {tested_ver})", file=sys.stderr)
        except importlib.metadata.PackageNotFoundError:
            print(f"ERROR: {pkg} not installed. Run: pip install {pkg}", file=sys.stderr)
            sys.exit(1)


def get_output_dir():
    """Get output directory from env or default."""
    output_dir = os.environ.get("QWEN_TTS_OUTPUT_DIR", os.path.expanduser("~/tts-output"))
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_model(model_id: str):
    """Load model with caching."""
    if model_id not in _model_cache:
        from mlx_audio.tts import load_model
        print(f"Loading model: {model_id}")
        _model_cache[model_id] = load_model(model_id)
        if hasattr(_model_cache[model_id], "get_supported_speakers"):
            speakers = _model_cache[model_id].get_supported_speakers()
            print(f"  Supported speakers: {speakers}")
    return _model_cache[model_id]


def resolve_output_path(output: str | None, prefix: str = "tts") -> str:
    """Resolve output file path."""
    if output:
        path = Path(output).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(get_output_dir(), f"{prefix}_{timestamp}.wav")


def generate_custom_voice(text: str, speaker: str, language: str,
                          instruct: str | None, speed: float, model_id: str,
                          output: str | None):
    """Generate speech using a preset speaker."""
    model = get_model(model_id)

    kwargs = {
        "text": text,
        "speaker": speaker,
        "language": language.lower(),
    }
    if instruct:
        kwargs["instruct"] = instruct

    print(f"Generating: speaker={speaker}, language={language}, speed={speed}")
    results = model.generate_custom_voice(**kwargs)

    # Results may be a generator or list — get first item
    output_path = resolve_output_path(output, "custom")
    first_result = next(iter(results))
    audio_np = np.array(first_result.audio)

    # Apply speed adjustment via time-stretching (preserves pitch)
    sample_rate = model.sample_rate
    if not math.isclose(speed, 1.0):
        try:
            import librosa
            audio_np = librosa.effects.time_stretch(audio_np, rate=speed)
            print(f"  Applied {speed}x speed via time-stretch (pitch preserved)")
        except ImportError:
            print(f"  WARNING: librosa not installed — falling back to sample rate hack "
                  f"(pitch will shift). Install: pip install librosa", file=sys.stderr)
            sample_rate = int(sample_rate * speed)
    sf.write(output_path, audio_np, sample_rate)
    print(f"  Saved: {output_path} (sr={sample_rate})")

    duration = len(audio_np) / sample_rate
    print(f"  Duration: {duration:.1f}s")
    return output_path


def generate_voice_design(text: str, instruct: str, language: str,
                          model_id: str, output: str | None):
    """Generate speech from a voice description."""
    model = get_model(model_id)

    if language.lower() not in ("english", "chinese"):
        print(f"  WARNING: VoiceDesign quality is unreliable for {language}. "
              f"Consider --mode voice-clone for better accent fidelity.", file=sys.stderr)

    print(f"Generating voice design: instruct='{instruct[:50]}...'")
    results = model.generate_voice_design(
        text=text,
        language=language.lower(),
        instruct=instruct,
    )

    output_path = resolve_output_path(output, "design")
    first_result = next(iter(results))
    audio_np = np.array(first_result.audio)
    sf.write(output_path, audio_np, model.sample_rate)

    duration = len(audio_np) / model.sample_rate
    print(f"  Saved: {output_path} (duration={duration:.1f}s)")
    return output_path


def generate_voice_clone(text: str, ref_audio: str, ref_text: str,
                         language: str, model_id: str, output: str | None):
    """Clone a voice from reference audio."""
    model = get_model(model_id)

    print(f"Cloning voice from: {ref_audio}")
    results = model.generate(
        text=text,
        lang_code=language.lower(),
        ref_audio=ref_audio,
        ref_text=ref_text,
    )

    output_path = resolve_output_path(output, "clone")
    first_result = next(iter(results))
    audio_np = np.array(first_result.audio)
    sf.write(output_path, audio_np, model.sample_rate)

    duration = len(audio_np) / model.sample_rate
    print(f"  Saved: {output_path} (duration={duration:.1f}s)")
    return output_path


def resolve_speaker(language: str, speaker_arg: str | None) -> str:
    """Resolve speaker from argument or language default."""
    lang_key = next(
        (k for k in DEFAULT_SPEAKERS if k.lower() == language.lower()), None
    )
    if lang_key:
        return speaker_arg or DEFAULT_SPEAKERS.get(lang_key, "Ryan")
    if not speaker_arg:
        print(f"  NOTE: No preset speaker for {language}; defaulting to Ryan (English). "
              f"Consider --mode voice-clone for native accent.", file=sys.stderr)
    return speaker_arg or "Ryan"


def validate_args(args):
    """Validate argument combinations and warn on unsupported options."""
    # Text length limit
    if len(args.text) > 10000:
        print(f"ERROR: text too long ({len(args.text)} chars, max 10000)", file=sys.stderr)
        sys.exit(1)
    # Speed range
    if not (0.5 <= args.speed <= 2.0):
        print(f"ERROR: --speed must be between 0.5 and 2.0 (got {args.speed})", file=sys.stderr)
        sys.exit(1)
    # Ref-audio file existence
    if args.ref_audio and not args.ref_audio.startswith(("http://", "https://")):
        if not os.path.exists(args.ref_audio):
            print(f"ERROR: --ref-audio file not found: {args.ref_audio}", file=sys.stderr)
            sys.exit(1)
    if not math.isclose(args.speed, 1.0) and args.mode != "custom-voice":
        print(f"WARNING: --speed is only supported in custom-voice mode, ignoring speed={args.speed}", file=sys.stderr)
    if args.mode == "voice-design" and not args.instruct:
        print("ERROR: --instruct is required for voice-design mode", file=sys.stderr)
        sys.exit(1)
    if args.mode == "voice-clone" and not args.ref_audio:
        print("ERROR: --ref-audio is required for voice-clone mode", file=sys.stderr)
        sys.exit(1)
    if args.mode == "voice-clone" and not args.ref_text:
        print("WARNING: --ref-text not provided, quality may degrade", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS MLX Inference")
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument("--mode", choices=["custom-voice", "voice-design", "voice-clone"],
                        default="custom-voice", help="Generation mode")
    parser.add_argument("--speaker", default=None, help="Speaker name (custom-voice mode)")
    parser.add_argument("--language", default="English", help="Language (default: English)")
    parser.add_argument("--instruct", default=None,
                        help="Style instruction (emotion/prosody) or voice description")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed factor (0.8-1.3)")
    parser.add_argument("--model", default=None, help="Override model ID")
    parser.add_argument("--output", "-o", default=None, help="Output .wav path")
    parser.add_argument("--ref-audio", default=None, help="Reference audio for cloning")
    parser.add_argument("--ref-text", default=None, help="Transcript of reference audio")

    args = parser.parse_args()
    check_versions()
    validate_args(args)

    model_id = args.model or os.environ.get("QWEN_TTS_MODEL") or _resolve_default_model(args.mode)
    speaker = resolve_speaker(args.language, args.speaker)

    if args.mode == "custom-voice":
        generate_custom_voice(
            text=args.text, speaker=speaker, language=args.language,
            instruct=args.instruct, speed=args.speed, model_id=model_id,
            output=args.output,
        )
    elif args.mode == "voice-design":
        generate_voice_design(
            text=args.text, instruct=args.instruct, language=args.language,
            model_id=model_id, output=args.output,
        )
    elif args.mode == "voice-clone":
        generate_voice_clone(
            text=args.text, ref_audio=args.ref_audio,
            ref_text=args.ref_text or "", language=args.language,
            model_id=model_id, output=args.output,
        )


if __name__ == "__main__":
    main()

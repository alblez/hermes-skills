#!/usr/bin/env python3
"""
Qwen3-TTS MLX Inference Script for Apple Silicon.

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
  pip install "mlx-audio>=0.3.0" "mlx-lm>=0.30.0" numpy soundfile
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf


# Default models per mode
DEFAULT_MODELS = {
    "custom-voice": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "voice-design": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
    "voice-clone": "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit",
}

# Default speakers per language
DEFAULT_SPEAKERS = {
    "Chinese": "Vivian",
    "English": "Ryan",
    "Japanese": "Ono_Anna",
    "Korean": "Sohee",
}

# Cache loaded model
_model_cache = {}


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
        "language": language,
    }
    if instruct:
        kwargs["instruct"] = instruct

    print(f"Generating: speaker={speaker}, language={language}, speed={speed}")
    results = model.generate_custom_voice(**kwargs)

    # Results may be a generator or list — get first item
    output_path = resolve_output_path(output, "custom")
    first_result = next(iter(results))
    audio_np = np.array(first_result.audio)

    # Apply speed adjustment via resampling if needed
    sample_rate = model.sample_rate
    if speed != 1.0:
        # Adjust sample rate to simulate speed change
        effective_sr = int(sample_rate * speed)
        sf.write(output_path, audio_np, effective_sr)
        print(f"  Saved: {output_path} (sr={effective_sr}, speed={speed}x)")
    else:
        sf.write(output_path, audio_np, sample_rate)
        print(f"  Saved: {output_path} (sr={sample_rate})")

    duration = len(audio_np) / sample_rate
    print(f"  Duration: {duration:.1f}s")
    return output_path


def generate_voice_design(text: str, instruct: str, language: str,
                          model_id: str, output: str | None):
    """Generate speech from a voice description."""
    model = get_model(model_id)

    print(f"Generating voice design: instruct='{instruct[:50]}...'")
    results = model.generate_voice_design(
        text=text,
        language=language,
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

    # Resolve model
    model_id = args.model or os.environ.get("QWEN_TTS_MODEL") or DEFAULT_MODELS[args.mode]

    # Resolve speaker
    speaker = args.speaker or DEFAULT_SPEAKERS.get(args.language, "Ryan")

    if args.mode == "custom-voice":
        generate_custom_voice(
            text=args.text, speaker=speaker, language=args.language,
            instruct=args.instruct, speed=args.speed, model_id=model_id,
            output=args.output,
        )
    elif args.mode == "voice-design":
        if not args.instruct:
            print("ERROR: --instruct is required for voice-design mode", file=sys.stderr)
            sys.exit(1)
        generate_voice_design(
            text=args.text, instruct=args.instruct, language=args.language,
            model_id=model_id, output=args.output,
        )
    elif args.mode == "voice-clone":
        if not args.ref_audio:
            print("ERROR: --ref-audio is required for voice-clone mode", file=sys.stderr)
            sys.exit(1)
        if not args.ref_text:
            print("WARNING: --ref-text not provided, quality may degrade", file=sys.stderr)
        generate_voice_clone(
            text=args.text, ref_audio=args.ref_audio,
            ref_text=args.ref_text or "", language=args.language,
            model_id=model_id, output=args.output,
        )


if __name__ == "__main__":
    main()

# Informational Pitfalls

These are lower-severity notes that rarely affect the agent's primary code path
(text_to_speech via terminal or the qwen3tts provider). They are relevant for
manual CLI usage, environment setup, and edge cases.

4. **sox must be installed** — `brew install sox` (macOS) or `apt install sox` (Linux), or audio processing in some modes will fail.

5. **First inference is slow** — kernel compilation warmup on MLX/Metal. Subsequent runs are ~29% faster. Expected first-run overhead: 10-30 seconds extra.

8. **huggingface-cli is deprecated** — use `hf download` instead of `huggingface-cli download` for model downloads.

9. **Warnings about tokenizer regex and model type are harmless** — stderr messages like "The model type is not yet supported" don't affect generation quality. Safe to ignore.

10. **For voice cloning**: reference audio should be 5-10 seconds, clean (no background noise, no music, single speaker). Longer clips don't improve quality.

11. **The `--instruct` flag**: controls emotion/prosody for CustomVoice mode, and is REQUIRED for VoiceDesign mode. Omitting it in VoiceDesign produces an error.

12. **datasets v4.8+ requires torchcodec for audio decoding** — if torch is not installed, use `ds.with_format("arrow")` then decode raw bytes with soundfile: `sf.read(io.BytesIO(row.column("audio")[0].as_py()["bytes"]))`. Only relevant when running the VoxForge curation pipeline.

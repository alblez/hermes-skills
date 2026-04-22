# Future Work

Remaining items after the v1.6.0 implementation cycle (Apr 2026).

---

## Upstream PR to hermes-agent (Low Priority)

Submit `qwen3tts` as an official TTS provider. Deprioritized since the MCP
server provides a clean integration without core changes. Revisit if Hermes
adds a native "local CLI TTS" provider abstraction.

---

## Undocumented Qwen3-TTS Capabilities

Not yet exposed in the skill:

- **Batch generation**: `model.batch_generate(texts=[...])` for parallel synthesis
- **`create_voice_clone_prompt()`**: Reusable voice prompts (PyTorch only)
- **vLLM deployment**: Production serving with vLLM-Omni
- **Fine-tuning**: Custom voice training from reference data
- **DashScope cloud API**: 49 timbres with broader language coverage
- **Additional quantizations**: 5-bit, 6-bit, bf16 variants on mlx-community

---

## Completed (reference only)

| Item | Completed in |
|------|-------------|
| MCP Server | v1.6.0 — `src/spanish_tts/mcp_server.py` |
| Streaming decode | v1.6.0 — `stream=True` on engine + MCP `say` tool |
| Fix `platforms` claim | v1.6.0 — changed to `[macos]` |
| Persistent TTS daemon | v1.6.0 — MCP server keeps model loaded |
| Concurrency control | v1.6.0 — MCP single-process sequential |

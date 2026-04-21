# Future Work

Tracked items from the 5-agent swarm review (Apr 2026). These are deferred
improvements that were identified but not implemented in v1.5.0.

## MCP Server (High Priority)

Build a Model Context Protocol server wrapping `spanish-tts` CLI. This would
provide a clean tool interface (`mcp_spanish_tts_say`) that survives `hermes update`
without any core patching.

**Location**: `scripts/mcp_server.py` in this skill, or in the spanish-tts repo.

**Config** (hermes config.yaml):
```yaml
mcp_servers:
  spanish-tts:
    command: ["conda", "run", "-n", "qwen3-tts", "python", "-m", "spanish_tts.mcp_server"]
    tools:
      include: ["say", "list_voices", "demo"]
```

**Estimated effort**: ~100-150 lines of Python.

## Upstream PR to hermes-agent (Medium Priority)

Submit `qwen3tts` as an official TTS provider following the NeuTTS pattern
(commits `d50e0711`, `11f029c3`). Requirements:
- Register in `DEFAULT_CONFIG["tts"]`
- Add `check_tts_requirements()` for conda
- Add inline documentation comment listing qwen3tts in valid choices
- Consider generic "local CLI TTS" provider instead of spanish-tts-specific

The `upstream-contribution` skill in this repo was built for this workflow.

## Fix `platforms` Claim (Low Priority)

Current: `platforms: [macos, linux]`. MLX is Apple Silicon only.
The PyTorch path exists but has no `spanish-tts` CLI equivalent for Linux.

Options:
- Change to `platforms: [macos]`
- Add Linux section with PyTorch + vLLM instructions and a generic wrapper

## Document Missing Qwen3-TTS Capabilities

Add to references/ when relevant:
- **Streaming generation**: `stream=True` on `generate()`, `generate_custom_voice()`, `generate_voice_design()`
- **Batch generation**: `model.batch_generate(texts=[...])` for parallel synthesis
- **`create_voice_clone_prompt()`**: Reusable voice prompts (PyTorch only)
- **vLLM deployment**: Production serving with vLLM-Omni
- **Fine-tuning**: Custom voice training from reference data
- **DashScope cloud API**: 49 timbres with broader language coverage
- **Additional quantizations**: 5-bit, 6-bit, bf16 variants on mlx-community

## Persistent TTS Daemon

Each `conda run` call spawns a new process, reloading the 2-3 GB model.
A persistent daemon accepting requests via socket/stdin would eliminate
the 5-15s model loading overhead per call. This could be integrated with
the MCP server approach above.

## Concurrency Control

No locking exists. Concurrent TTS calls each spawn their own conda process
with full model load. On 16 GB machines, 2+ concurrent calls can trigger swap.
Add a threading semaphore or file-based lock for multi-user scenarios.

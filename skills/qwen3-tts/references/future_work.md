# Future Work

Tracked items from the 5-agent swarm review (Apr 2026). These are deferred
improvements that were identified but not implemented in v1.5.0.

---

## MCP Server -- IMPLEMENTED

**Status**: Implemented in `src/spanish_tts/mcp_server.py` in the
[qwen3-tts-spanish-voices](https://github.com/alblez/qwen3-tts-spanish-voices) repo.

Install: `pip install -e ".[mlx,mcp]"`

Hermes config:
```yaml
mcp_servers:
  spanish-tts:
    command: ["conda", "run", "-n", "qwen3-tts", "python", "-m", "spanish_tts.mcp_server"]
```

The implementation follows the sketch below. The model preloads eagerly at
server start, eliminating the 5-15s cold start per `conda run` call.

### Target repo

**https://github.com/alblez/qwen3-tts-spanish-voices** (`/Users/alberto/Code/spanish-tts`)

The MCP server wraps the `spanish_tts.engine` module that already exists.
It belongs with the code it wraps, not in hermes-skills.

### File to create

`src/spanish_tts/mcp_server.py` — a Python module invocable as:
```
python -m spanish_tts.mcp_server
```

### Existing code the server reuses

The server should import and call these directly (no subprocess, no CLI):

| Function | Module | Signature | Returns |
|----------|--------|-----------|---------|
| `generate()` | `spanish_tts.engine` | `(text, voice_config, speed=1.0, output=None, output_dir=None)` | `str` (WAV path) |
| `generate_clone()` | `spanish_tts.engine` | `(text, ref_audio, ref_text, speed=1.0, output=None, ...)` | `str` (WAV path) |
| `generate_design()` | `spanish_tts.engine` | `(text, instruct, language="Spanish", speed=1.0, output=None, ...)` | `str` (WAV path) |
| `list_voices()` | `spanish_tts.config` | `(voices_file=None)` | `dict[str, dict]` |
| `get_voice()` | `spanish_tts.config` | `(name, voices_file=None)` | `dict \| None` |
| `get_defaults()` | `spanish_tts.config` | `(voices_file=None)` | `dict` |

The engine uses `_model_cache = {}` (module-level dict in `engine.py`) so the
MLX model stays loaded across MCP tool calls within the same process. This is
the key advantage over `conda run` which spawns a new process each time.

### MCP tools to expose

```
Tool: say
  Description: Generate Spanish speech from text using a registered voice
  Parameters:
    text (str, required): Text to synthesize
    voice (str, default "neutral_male"): Voice name from registry
    speed (float, default 1.0): Speed factor 0.8-1.3
    output (str, optional): Output .wav path (auto-generated if omitted)
  Returns: { "path": "/path/to/output.wav", "duration_seconds": 3.2 }

Tool: list_voices
  Description: List all registered voices with their type and metadata
  Parameters: none
  Returns: { "voices": { "carlos_mx": { "type": "clone", "gender": "male", ... }, ... } }

Tool: demo
  Description: Generate the same text with ALL registered voices for comparison
  Parameters:
    text (str, required): Text to synthesize
    output_dir (str, default "/tmp/spanish-tts-demo"): Output directory
  Returns: { "results": [ { "voice": "carlos_mx", "path": "...", "status": "ok" }, ... ] }
```

### Implementation sketch

```python
"""MCP server for spanish-tts."""

from mcp.server.fastmcp import FastMCP

from spanish_tts.config import get_defaults, get_voice, list_voices
from spanish_tts.engine import generate

mcp = FastMCP("spanish-tts")


@mcp.tool()
def say(text: str, voice: str = "neutral_male", speed: float = 1.0, output: str | None = None) -> dict:
    """Generate Spanish speech from text using a registered voice."""
    voice_config = get_voice(voice)
    if voice_config is None:
        available = list(list_voices().keys())
        return {"error": f"Voice '{voice}' not found. Available: {', '.join(available)}"}

    defaults = get_defaults()
    effective_speed = speed or defaults.get("speed", 1.0)
    output_dir = defaults.get("output_dir", "~/tts-output/spanish")

    path = generate(
        text=text,
        voice_config=voice_config,
        speed=effective_speed,
        output=output,
        output_dir=output_dir,
    )

    import soundfile as sf
    info = sf.info(path)
    return {"path": path, "duration_seconds": round(info.duration, 2)}


@mcp.tool()
def list_all_voices() -> dict:
    """List all registered voices with their type and metadata."""
    return {"voices": list_voices()}


@mcp.tool()
def demo(text: str, output_dir: str = "/tmp/spanish-tts-demo") -> dict:
    """Generate the same text with ALL registered voices for comparison."""
    from pathlib import Path
    voices = list_voices()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for name, config in voices.items():
        try:
            path = generate(text=text, voice_config=config, speed=1.0, output=str(out / f"{name}.wav"))
            results.append({"voice": name, "path": path, "status": "ok"})
        except Exception as e:
            results.append({"voice": name, "error": str(e), "status": "failed"})

    return {"results": results}


if __name__ == "__main__":
    mcp.run()
```

### pyproject.toml changes

Add an `mcp` optional dependency group and a `__main__` entry:

```toml
[project.optional-dependencies]
mlx = [
    "mlx-audio>=0.3.0",
    "mlx-lm>=0.30.0",
]
mcp = [
    "mcp[cli]>=1.0",
]
all = [
    "qwen3-tts-spanish-voices[mlx,mcp]",
]
```

### Hermes config.yaml

```yaml
mcp_servers:
  spanish-tts:
    command: ["conda", "run", "-n", "qwen3-tts", "python", "-m", "spanish_tts.mcp_server"]
```

The agent will see tools named `mcp_spanish-tts_say`, `mcp_spanish-tts_list_all_voices`,
`mcp_spanish-tts_demo` (Hermes prefixes MCP tools with the server name).

### Installation

```bash
conda activate qwen3-tts
cd ~/Code/spanish-tts
pip install -e ".[mlx,mcp]"
```

Then in hermes:
```bash
hermes mcp add spanish-tts --command "conda run -n qwen3-tts python -m spanish_tts.mcp_server"
```

### Testing

```bash
# Verify the server starts
conda run -n qwen3-tts python -m spanish_tts.mcp_server --help

# Test via Hermes
hermes chat -q "List the available Spanish TTS voices"
hermes chat -q "Generate audio saying 'Hola mundo' with the carlos_mx voice"
```

### Why this matters

| | `conda run` (current) | MCP server |
|---|---|---|
| Model reload | Every call (5-15s) | Once at server start |
| Survives hermes update | N/A (terminal approach) | Yes |
| Clean tool interface | No (manual terminal commands) | Yes (`mcp_spanish-tts_say`) |
| Concurrent safety | None (multiple processes) | Single process, sequential |
| Hermes terminal backend | Bypassed (runs locally) | Respects MCP config |

### Estimated effort

~100-150 lines for the server, ~10 lines for pyproject.toml changes,
~5 lines for hermes config.yaml. Plus tests.

---

## Upstream PR to hermes-agent (Medium Priority)

Submit `qwen3tts` as an official TTS provider following the NeuTTS pattern
(commits `d50e0711`, `11f029c3`). Requirements:

- Register in `DEFAULT_CONFIG["tts"]`
- Add `check_tts_requirements()` for conda
- Add inline documentation comment listing qwen3tts in valid choices
- Consider generic "local CLI TTS" provider instead of spanish-tts-specific

The `upstream-contribution` skill in this repo was built for this workflow.

Note: If the MCP server is built first, the upstream PR becomes less urgent
since MCP provides a clean integration without core changes.

---

## Fix `platforms` Claim (Low Priority)

Current: `platforms: [macos, linux]`. MLX is Apple Silicon only.
The PyTorch path exists but has no `spanish-tts` CLI equivalent for Linux.

Options:

- Change to `platforms: [macos]`
- Add Linux section with PyTorch + vLLM instructions and a generic wrapper

---

## Document Missing Qwen3-TTS Capabilities

Add to references/ when relevant:

- **Streaming generation**: `stream=True` on `generate()`, `generate_custom_voice()`, `generate_voice_design()`
- **Batch generation**: `model.batch_generate(texts=[...])` for parallel synthesis
- **`create_voice_clone_prompt()`**: Reusable voice prompts (PyTorch only)
- **vLLM deployment**: Production serving with vLLM-Omni
- **Fine-tuning**: Custom voice training from reference data
- **DashScope cloud API**: 49 timbres with broader language coverage
- **Additional quantizations**: 5-bit, 6-bit, bf16 variants on mlx-community

---

## Persistent TTS Daemon

Each `conda run` call spawns a new process, reloading the 2-3 GB model.
The MCP server approach above solves this naturally — the model stays loaded
in the MCP server process. If MCP is not used, a standalone daemon accepting
requests via socket/stdin would be the alternative.

---

## Concurrency Control

No locking exists. Concurrent TTS calls each spawn their own conda process
with full model load. On 16 GB machines, 2+ concurrent calls can trigger swap.
The MCP server approach handles this naturally (single process, sequential tool calls).
For the `conda run` path, add a threading semaphore or file-based lock.

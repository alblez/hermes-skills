# Hermes Agent Skills

A collection of reusable skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — the open-source AI agent framework by Nous Research.

## Available Skills

| Skill | Description |
|-------|-------------|
| [qwen3-tts](skills/qwen3-tts/) | Run Qwen3-TTS text-to-speech locally on Apple Silicon (MLX) or GPU/CPU (PyTorch). Supports custom voices, voice design, and voice cloning. 10 languages, 3-second voice cloning, emotional control. |
| [upstream-contribution](skills/upstream-contribution/) | Contribute your derivative project back to the upstream OSS project it builds on. Detects upstream relationships, forks the upstream repo, adds your project to their ecosystem/community section, and opens a PR. Also finds relevant awesome lists. |

## Installation

### Via Hermes Skills Tap (Recommended)

```bash
# Add this repo as a skill source
hermes skills tap add alblez/hermes-skills

# Search and install
hermes skills search qwen3-tts
hermes skills install alblez/hermes-skills/skills/qwen3-tts
```

### Manual

```bash
# Clone and copy the skill you want
git clone https://github.com/alblez/hermes-skills.git
cp -r hermes-skills/skills/qwen3-tts ~/.hermes/skills/
```

## Structure

```
hermes-skills/
├── .gitignore
├── README.md
├── LICENSE
└── skills/
    ├── qwen3-tts/
    │   ├── SKILL.md              # Skill definition (loaded by Hermes)
    │   ├── requirements.txt      # Python dependencies
    │   └── scripts/
    │       └── tts_mlx.py        # MLX inference script
    └── upstream-contribution/
        ├── SKILL.md              # Skill definition (loaded by Hermes)
        └── scripts/
            └── scan-upstream-opportunities.py  # Cron job scanner
```

## Contributing

Each skill lives in its own directory under `skills/` and must contain a `SKILL.md` with YAML frontmatter. See the [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills) guide for the skill format.

## License

Apache-2.0

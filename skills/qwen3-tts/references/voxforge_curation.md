# VoxForge Curation Pipeline

Source clone voices from the `ciempiess/voxforge_spanish` HuggingFace dataset
(21,692 samples — Spain, Argentina, Mexico, Chile, Latin America).

Run from the spanish-tts repo directory (`~/Code/spanish-tts` or the path
configured in `qwen3-tts.spanish-tts-path`).

```bash
# Browse dataset stats by country/gender
python scripts/curate.py browse

# Find best speakers for a country/gender
python scripts/curate.py pick --country mexico --gender male

# Preview a speaker's clips
python scripts/curate.py listen SPEAKER_ID

# Export best clip as a voice (registers in voices.yaml automatically)
python scripts/curate.py export SPEAKER_ID --name carlos_mx --accent mexico --gender male
```

Clone voices produced this way have better accent fidelity than design voices.
The curate.py script requires the `datasets` package and downloads samples on first run.

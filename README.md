# OraKit XYZ

OraKit XYZ is a local preview for turning Sugartown Ora wallet metadata into a character-profile layer. Search an ENS name or wallet address, load matching Sugartown Oras through Moralis, inspect token traits, and open a selected character profile modal.

## Quick Start

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 server.py
```

Then open:

```text
http://localhost:4173/
```

Set `MORALIS_API_KEY` in `.env` before searching live wallets. The server also supports `MORALIS_API` and `MORALIS_WEB3_API_KEY`.

## Current Features

- ENS or wallet search for Sugartown Ora ownership
- Moralis NFT metadata lookup with ENSIdeas fallback resolution
- hardcoded `pizzalord.eth` alias for the known Ora wallet
- responsive Ora grid with token images and trait chips
- selected-character modal with lore, persona prompt, and schema export
- custom animated Ora 4147 Alpha Cola 404/error state

## Image Asset Workflow

The live error animation is:

```text
assets/ora-4147-alpha-cola-fail.gif
```

`generate_404_gif.py` creates the rough local version with Pillow. `polish_404_gif.py` can build a reference board, use a GPT Image sprite sheet, and retime the result into the directed loop.

The polished OpenAI step expects an `OPENAI_API_KEY` and an image-generation CLI path via `IMAGE_GEN_CLI`, or the default Codex imagegen CLI location under `~/.codex`.

## Notes

API keys stay server-side and are read from local env files only. Do not commit `.env`.

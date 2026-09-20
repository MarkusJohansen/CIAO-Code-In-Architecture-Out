# CIAO — Agent Guide

## Purpose
CIAO is a command‑line tool that flattens a code repository (via Repomix) and generates Markdown architecture documentation (arc42) using local or cloud LLMs.

## How to run
```bash
cd CIAO-system
uv run main.py <github-repo-url-or-local-path>
```

## Tech stack
- Python 3.11+, async
- `uv` for dependency management
- `repomix` for repo flattening
- `openai` Python client for LLM API calls (OpenAI-compatible)

## Key files
| File | Purpose |
|---|---|
| `main.py` | Entry point — flattens repo, calls LLM sections in parallel, writes docs |
| `prompt.json` | arc42 template sections + system prompts + format specs |
| `repomix.config.json` | Controls what files get included/excluded from flattening |
| `.env` | LLM config (gitignored) |
| `run.sh` | Convenience script — auto-starts llama.cpp server, runs CIAO |

## Environment variables
| Variable | Default | Description |
|---|---|---|
| `LLM_BASE_URL` | — | OpenAI-compatible endpoint (e.g. `http://localhost:8080/v1`) |
| `LLM_MODEL` | `gpt-5-2025-08-07` | Model name or path |
| `LLM_API_KEY` | `"no-key"` | Optional API key for local servers |
| `TOKEN_LIMIT` | `400000` | Max tokens per prompt; skip section if exceeded |
| `OPENAI_API_KEY` | — | Fallback for cloud OpenAI (only if `LLM_BASE_URL` not set) |

## LLM backends supported
1. **OpenAI** — set `OPENAI_API_KEY`
2. **Ollama** — `LLM_BASE_URL=http://localhost:11434/v1`
3. **llama.cpp** — `LLM_BASE_URL=http://localhost:8080/v1`, point `LLM_MODEL` to a `.gguf` path

## Models available on this machine
Stored in `~/models/`:
- `Qwythos-9B-Q4_K_M.gguf` — good balance, default choice
- `Qwen3-Coder-30B.gguf` — best code quality, slower
- `VibeThinker-3B.BF16.gguf` — fastest, lightest
- `Qwen3.6-14B-FableVibes-Q6_K.gguf` — creative/artistic, decent for code
- `gpt-oss-20b-Q8_0.gguf` — large, slow
- `GLM-4.7-Flash.gguf` — general purpose
- `North-Mini-Code-1.0-Q4_K_M.gguf` — tiny code model

Use `run.sh` — it reads `.env` and auto-starts the llama.cpp server if not already running.

## Common commands
```bash
# Install dependencies
uv sync

# Run CIAO (auto-starts server, reads .env)
./run.sh https://github.com/example/repo

# Or manually:
llama-server -m ~/models/Qwythos-9B-Q4_K_M.gguf --port 8080
uv run main.py https://github.com/example/repo

# Check if server is up
curl http://localhost:8080/health
```

## Agent conventions
- **Never commit `.env`** — it has local paths and API keys. If you modify `.env`, check if `.env.example` needs updating too.
- **Keep `prompt.json` valid JSON** — it drives the entire doc generation pipeline.
- **Async all the way** — `generate_section` calls are concurrent; don't add blocking I/O inside them.
- **Token counting** — `tiktoken` is approximate for non-OpenAI models. That's fine; it's only for skipping oversized prompts.
- **Model path expansion** — `run.sh` expands `~` in `LLM_MODEL`. If you write a new script, do the same.

## Testing / validation
- No automated tests yet. Validate by running on a known repo and checking `arc42_documentation.txt`.
- Compare output against existing docs in `Data/Repos/` (generated with GPT-5).
- Check PlantUML diagrams render correctly.

## When modifying LLM calling logic
1. `call_openai_with_retry()` in `main.py` — add retry/backoff logic here
2. `generate_section()` — change prompts, section formats here (reads from `prompt.json`)
3. `async_main()` — change concurrency or orchestration here
4. Keep OpenAI-compatible API shape — don't break compatibility with Ollama/llama.cpp

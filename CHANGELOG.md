# CIAO Changelog — Self-Hosted Fork

## Summary

Forked the original CIAO CLI (which only supported OpenAI GPT-5 via cloud API) to support self-hosted models via llama.cpp and Ollama, while modernizing the Python tooling.

## Changes

### LLM Backend
- **Before**: Hard-coded `AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])` calling `gpt-5-2025-08-07`
- **After**: Configurable endpoint via env vars:
  - `LLM_BASE_URL` — OpenAI-compatible server (e.g. `http://localhost:8080/v1`)
  - `LLM_MODEL` — model name or path (e.g. `~/models/Qwythos-9B-Q4_K_M.gguf`)
  - `LLM_API_KEY` — optional key for local servers (defaults to `"no-key"`)
  - `OPENAI_API_KEY` — still works as fallback
  - `TOKEN_LIMIT` — configurable per model context window
- **Timeout**: Raised from SDK default (60s) to **300s** to accommodate slow local prefill on 9B+ models

### Dependency Management
- **Before**: `pip install argparse asyncio aiofiles tiktoken openai repomix` manually
- **After**: `uv` project with `pyproject.toml` + `.venv`
  - Added `python-dotenv` for `.env` config loading
  - Locked dependency versions

### Config & Secrets
- Added `.env` (gitignored) and `.env.example` — stores LLM URL, model path, token budget
- Added `python-dotenv` + `load_dotenv()` at startup in `main.py`

### Repomix
- Updated `repomix.config.json` from camelCase to snake_case (`tokenCount` → `token_count`, `maxFileSize` → `max_file_size`, etc.) for compatibility with Repomix v0.5.0

### Scripts
- Added `run.sh` — reads `.env`, auto-starts `llama-server` if not running, then runs CIAO

### Documentation
- Updated `README.md` with setup for OpenAI, Ollama, and llama.cpp
- Added `AGENTS.md` — agent conventions, commands, model catalog
- Added `CONTEXT.md` — architecture decisions, limitations, extension points
- Added `.gitignore` — Python, secrets, IDE, CIAO output files

### Known Limitations
- Token counting via `tiktoken` is approximate for non-OpenAI models (only used for skipping oversized prompts)
- Serial execution (`--max-parallel=1`) recommended for models < 30B on Apple Silicon to avoid timeout and maximize KV cache reuse
- No automated tests — validate manually against `Data/Repos/` benchmarks

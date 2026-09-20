# CIAO — Context & Decisions

## What this project does
CIAO (Code-In-Architecture-Out) is a Python CLI tool that generates ISO/IEC/IEEE 42010, SEI Views & Beyond, C4 model, and arc42-compliant architecture documentation from source code repositories. It uses Repomix to flatten repositories and LLMs to generate structured Markdown docs.

## Architecture snapshot
```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌────────────┐
│  Repo   │───▶│ Repomix  │───▶│  LLM    │───▶│ arc42 doc  │
│  (git)  │     │ (flatten)│     │ (async) │     │ (.txt/.md) │
└─────────┘     └──────────┘     └─────────┘     └────────────┘
```

- **Single-file architecture**: `main.py` does everything — flattening, prompting, parallel LLM calls, doc assembly.
- **Async parallel sections**: Each arc42 section (System Overview, Context, Containers, etc.) is a separate LLM call, up to 12 concurrent.
- **OpenAI-compatible client**: Uses the `openai` Python SDK. Works with any OpenAI-compatible server — OpenAI, Ollama, llama.cpp, vLLM, LM Studio, etc.
- **Config-driven prompts**: `prompt.json` defines sections, their goals, and expected formats (text, table, diagram, steps).

## Key decisions

### 1. Why OpenAI SDK for local models?
Both Ollama and llama.cpp expose `/v1/chat/completions` with OpenAI-compatible request/response formats. Using the official SDK means zero custom HTTP handling, streaming support, and tool use (if we ever need it). We're not locked into OpenAI — we're locked into the standard.

### 2. Why not use a pipeline / DAG framework?
The original paper used a single-shot approach. We kept it simple: flat async loop over sections. If we ever need dependency graphs (e.g. section 5 depends on section 4), we'll add topological ordering to `walk()`. Not needed yet.

### 3. Why arc42 + C4 + SEI + ISO 42010?
The paper's contribution is a unified template that satisfies all four standards simultaneously. Each section maps to multiple standards. This is the differentiator — don't simplify to just C4 or just arc42.

### 4. Why repomix instead of building our own flattener?
Repomix is fast, configurable, handles gitignore, supports remote repos, and produces clean tree + file content. Not reinventing the wheel.

### 5. Why GGUF files in ~/models/ instead of Ollama's cache?
HuggingFace's cache path (`~/.cache/huggingface/hub/models--*/snapshots/*/<hash>/`) is unwieldy for direct CLI use. Flat `~/models/` directory lets us run `llama-server -m ~/models/model.gguf` without path archaeology.

## Known limitations & risks

| Issue | Impact | Mitigation |
|---|---|---|
| No automated tests | Regressions go unnoticed | Manual validation against `Data/Repos/` benchmarks |
| Token counting is approximate for non-OpenAI models | May skip sections unnecessarily or overflow context | Use conservative `TOKEN_LIMIT` (default 400K works for 512K ctx models) |
| LLM hallucination in diagrams | Invalid PlantUML | Validation rules in `prompt.json` + manual review |
| Single monolithic `main.py` | Hard to maintain as features grow | Split into `flatten.py`, `llm.py`, `doc.py` when >500 lines |
| No incremental / cached runs | Re-flattens and re-generates everything every time | Add output checksums; skip unchanged sections |
| Parallel sections may drift in tone | Inconsistent voice across doc | System prompt enforcement + shared context works well enough |

## Performance characteristics
- **Flattening**: ~1-5 min for 100K LOC repos (network + disk)
- **Section generation**: ~10-30s per section per call (depends on model speed)
- **Total**: ~2-5 min for 8-12 sections with concurrency of 12
- **Memory**: LLM server uses ~6-18 GB RAM depending on model (Qwythos-9B ~6GB, Qwen3-Coder-30B ~18GB)

## Extension points
| Want to add... | Where to touch |
|---|---|
| New arc42 section | `prompt.json` → add entry under `doc_template` |
| New diagram type | `prompt.json` → add `"diagram": { "uml_type": "..." }` |
| Different LLM client | `main.py` → swap `AsyncOpenAI` for `AsyncAnthropic` etc. |
| Streaming output | `call_openai_with_retry` → use `client.chat.completions.create(..., stream=True)` |
| Section dependency ordering | `walk()` in `main.py` → sort by dependency graph instead of dict order |
| Vision (image analysis) | `repomix.config.json` → add image patterns, `prompt.json` → add vision template |
| Caching | Wrap `generate_section` with `@cache` keyed by `(repo_hash, section_id)` |

## Data folder
`Data/Repos/*.md` — benchmark outputs from the original paper (generated with GPT-5). Use these to validate quality regressions when switching models. The PNG files are rendered diagrams extracted from those docs.

## Environment
- **OS**: macOS (Apple Silicon)
- **Python**: 3.11+ (managed by `uv`)
- **LLM server**: `llama-server` (Homebrew)
- **Models**: Qwythos 9B (default), Qwen3 Coder 30B (quality), VibeThinker 3B (speed)
- **Memory pressure**: 18GB peak with Qwen3-Coder-30B; 6GB with Qwythos-9B

## Research context
This is the artifact from a research project comparing LLM-generated architecture documentation against human-written docs. The `Data/Repos/` folder contains 24 open-source repos that were documented. The paper's contribution is the unified template and the evaluation methodology, not the tool itself.

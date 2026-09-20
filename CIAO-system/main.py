"""CIAO — Code-In-Architecture-Out
Orchestrator: flatten repo, generate sections in parallel, assemble doc.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import cast, List

import aiofiles

from config import (
    REPO_URL,
    DEFAULT_MAX_PARALLEL,
    LLM_BASE_URL,
    RESULTS_DIR,
    MEMORY_PATH,
    FULL_CODE_PATH,
)
from flattening import flatten_repo
from doc_generator import generate_section, walk
from schemas import Memory


def ensure_memory_schema(raw: dict) -> Memory:
    required_top = {"global_guidelines", "md_safety", "user_profile", "doc_template"}
    missing = required_top.difference(raw.keys())
    if missing:
        raise KeyError(f"Missing keys in memory JSON: {missing}")
    return cast(Memory, raw)


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Generate arc42 docs via Repomix CLI + LLM (async & typed)")
    parser.add_argument("repository", nargs='?', default=REPO_URL, help="Local path or Git URL (default: config.yaml repo.url)")
    parser.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL, help="Maximum concurrent LLM calls")
    args = parser.parse_args()

    repo = args.repository
    if not repo:
        raise SystemExit("❌ No repository specified. Set repo.url in config.yaml or pass as argument.")

    # derive clean repo name for output file
    repo_name = repo.rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
    md_path = RESULTS_DIR / f"{repo_name}_doc.md"

    if not (LLM_BASE_URL or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit(
            "❌ No LLM configured. Set either:\n"
            "   LLM_BASE_URL (e.g. http://localhost:11434/v1 for Ollama)\n"
            "   or OPENAI_API_KEY for OpenAI."
        )

    print("🌀 Flattening repository …")
    code = await flatten_repo(repo)
    print(f"📄 {FULL_CODE_PATH.name} ({len(code):,} characters) ready")

    try:
        raw_memory = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"❌ Memory JSON not found: {MEMORY_PATH}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"❌ Invalid JSON in {MEMORY_PATH}: {exc}")

    memory: Memory = ensure_memory_schema(raw_memory)

    guidelines = memory["global_guidelines"]
    profile = memory["user_profile"]
    template = memory["doc_template"]
    md_rules = memory["md_safety"]

    md_parts: List[str] = [" "]

    semaphore = asyncio.Semaphore(args.max_parallel)
    tasks: List[asyncio.Task[str]] = []

    for sid, spec in walk(template):
        tasks.append(asyncio.create_task(
            generate_section(sid, spec, code, profile, guidelines, md_rules, semaphore)
        ))

    t0 = time.perf_counter()
    print(f"[MAIN] Launching {len(tasks)} tasks...")
    sections = await asyncio.gather(*tasks)
    total_duration = time.perf_counter() - t0
    print(f"[MAIN] All tasks done in {total_duration:.2f}s")

    md_parts.extend(filter(None, sections))
    md_parts.append(" ")

    async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
        await f.write("\n\n".join(md_parts))

    print(f"✅ MD written to {md_path}")


def main() -> None:
    """Synchronous entry point for uv / CLI."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")


if __name__ == "__main__":
    main()

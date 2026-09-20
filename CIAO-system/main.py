from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    Tuple,
    Union,
    List,
    Literal,
    cast,
    TypedDict,
)

import aiofiles
import tiktoken
import yaml
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

# Load .env file before any other configuration
load_dotenv()



BASE_DIR: Path = Path(__file__).resolve().parent
REPO_CONFIG_PATH: Path = BASE_DIR / "config.yaml"
REPO_MIX_CONFIG_PATH: Path = BASE_DIR / "repomix.config.json"
MEMORY_PATH: Path = BASE_DIR / "prompt.json"
FULL_CODE_PATH: Path = BASE_DIR / "full_code.txt"
MD_PATH: Path = BASE_DIR / "arc42_documentation.txt"

# Load config.yaml if present
_yaml_conf: dict[str, Any] = {}
if REPO_CONFIG_PATH.exists():
    with open(REPO_CONFIG_PATH, "r") as f:
        _yaml_conf = yaml.safe_load(f) or {}

# Helper to resolve precedence: config.yaml < .env < explicit CLI (later)
def _conf(path: str, env: str, default: Any = None) -> Any:
    # .env overrides yaml
    val = os.environ.get(env)
    if val is not None:
        return val
    # yaml
    keys = path.split(".")
    node = _yaml_conf
    for k in keys:
        node = node.get(k, {}) if isinstance(node, dict) else {}
    if node or isinstance(node, bool):
        return node
    return default

MODEL_NAME: str = _conf("llm.model", "LLM_MODEL", "gpt-5-2025-08-07")
TOKEN_LIMIT: int = int(str(_conf("llm.token_limit", "TOKEN_LIMIT", "400000")))
LLM_BASE_URL: str | None = str(_conf("llm.base_url", "LLM_BASE_URL", "")) or None
LLM_API_KEY: str | None = str(_conf("llm.api_key", "LLM_API_KEY", "")) or None
LLM_TIMEOUT: float = float(str(_conf("llm.timeout", "LLM_TIMEOUT", "300.0")))

REPO_URL: str | None = str(_conf("repo.url", "REPO_URL", "")) or None

try:
    enc = tiktoken.encoding_for_model(MODEL_NAME)
except KeyError:
    enc = tiktoken.get_encoding("cl100k_base")

# If a local base URL is set, use it; otherwise fall back to OpenAI
if LLM_BASE_URL:
    client = AsyncOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY or "no-key",
        timeout=LLM_TIMEOUT,
    )
else:
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=LLM_TIMEOUT)


MessageParam = Union[
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionDeveloperMessageParam,
]

def sys_msg(content: str) -> ChatCompletionSystemMessageParam:
    return {"role": "system", "content": content}

def usr_msg(content: str) -> ChatCompletionUserMessageParam:
    return {"role": "user", "content": content}

def asst_msg(content: str) -> ChatCompletionAssistantMessageParam:
    return {"role": "assistant", "content": content}


class TextFormat(TypedDict):
    description: str

class TableFormat(TypedDict):
    columns: Sequence[str]
    caption: str

class DiagramFormat(TypedDict, total=False):
    type: str
    description: str

class StepsFormat(TypedDict):
    description: str

class ListFormat(TypedDict):
    items: Sequence[str]

class TreeFormat(TypedDict):
    description: str

class SectionFormat(TypedDict, total=False):
    text: TextFormat
    table: TableFormat
    diagram: DiagramFormat
    steps: StepsFormat
    list: ListFormat
    tree: TreeFormat
    examples: Dict[str, Any]

class SectionSpec(TypedDict, total=False):
    title: str
    goal: str
    format: SectionFormat
    style: str
    optional: bool
    example: Dict[str, Any]
    subsections: Dict[str, "SectionSpec"]

class GlobalGuidelines(TypedDict):
    objective: str
    formatting: Sequence[str]
    commitment: Sequence[str]
    code_analysis: str

class UserProfile(TypedDict):
    role: str
    preferred_language: str
    output_format: str
    writing_style: str
    target_audience: str
    include: Sequence[str]
    diagram_format: str

class Memory(TypedDict):
    global_guidelines: GlobalGuidelines
    md_safety: Sequence[str]
    user_profile: UserProfile
    doc_template: Dict[str, SectionSpec]



def ensure_memory_schema(raw: Mapping[str, Any]) -> Memory:
    required_top = {"global_guidelines", "md_safety", "user_profile", "doc_template"}
    missing = required_top.difference(raw.keys())
    if missing:
        raise KeyError(f"Missing keys in memory JSON: {missing}")
    return cast(Memory, raw)


def walk(tree: Mapping[str, SectionSpec]) -> Iterator[Tuple[str, SectionSpec]]:
    for sid, spec in tree.items():
        if "goal" in spec:
            yield sid, spec
        if "subsections" in spec:
            yield from walk(spec["subsections"])  # Recursive call for nested sections


def prompt_token_count(*parts: str) -> int:
    return sum(len(enc.encode(p)) for p in parts)


async def call_openai_with_retry(
    messages: Sequence[MessageParam],
    model: str,
    *,
    max_retries: int = 3,
    initial_backoff: float = 2.0,
) -> str:

    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            resp: ChatCompletion = await client.chat.completions.create(
                model=model,
                messages=messages,
            )
            content_any: Any = resp.choices[0].message.content
            if content_any is None:
                raise ValueError("OpenAI returned empty content")
            content: str = cast(str, content_any)
            return content
        except Exception as exc:
            if attempt == max_retries:
                # If this was the last attempt, re-raise the exception.
                raise
            msg = (
                "⚠️  OpenAI error (attempt {}/{}): {} Retrying in {:.1f}s…"
            ).format(attempt, max_retries, exc, backoff)
            print(msg)
            await asyncio.sleep(backoff)
            backoff *= 2
    raise RuntimeError("Retry loop failed unexpectedly")


async def flatten_repo(repo: str) -> str:

    if not REPO_MIX_CONFIG_PATH.exists():
        raise SystemExit(f"❌ Config file missing: {REPO_MIX_CONFIG_PATH}")

    is_remote = repo.startswith(("http://", "https://", "git@"))
    cmd = ["repomix", "--remote", repo, "-c", str(REPO_MIX_CONFIG_PATH)] if is_remote else ["repomix", repo, "-c", str(REPO_MIX_CONFIG_PATH)]

    print("   ↪", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    if proc.returncode != 0:
        raise SystemExit(
            f"❌ Repomix error (code {proc.returncode}):\n{stderr_b.decode()}\n{stdout_b.decode()}"
        )

    try:
        async with aiofiles.open(FULL_CODE_PATH, "r", encoding="utf-8") as f:
            data = await f.read()
            return cast(str, data)
    except FileNotFoundError as exc:
        raise SystemExit(f"❌ Repomix did not create {FULL_CODE_PATH.name}: {exc}")


async def generate_section(
    sid: str,
    spec: SectionSpec,
    code: str,
    profile: UserProfile,
    guidelines: GlobalGuidelines,
    md_rules: Iterable[str],
    semaphore: asyncio.Semaphore,
) -> str:

    print(f"🔄 {sid:>4} — {spec['title']}")
    start = time.perf_counter()


    system_global = f"""
ROLE  : You are {profile['role']} writing for {profile['target_audience']}.
LANG  : {profile['preferred_language']}
OUT   : {profile['output_format']}   — tone: {profile['writing_style']}
INCL  : {', '.join(profile['include'])}; diagrams → {profile['diagram_format']}

OBJECTIVE
  {guidelines['objective']}

FORMATTING
  {'; '.join(guidelines['formatting'])}

COMMITMENTS
  {'; '.join(guidelines['commitment'])}

POLICY
  {guidelines['code_analysis']}
""".strip()

    system_md = "MD SAFETY\n" + "\n".join("• " + r for r in md_rules)

    # --- 2. Construct the Assistant Prompt ---
    # This pre-fills the assistant's response, guiding it on the specific task.
    assistant_payload = f"""
SECTION {sid} — {spec['title']}
Goal: {spec['goal']}

Required artefacts (JSON):
{json.dumps(spec.get('format', {}), indent=2)}

Style hints:
{spec.get('style', '')}

CHECKLIST
[ ] produce tables / figures / steps listed above
[ ] Write an introduction paragraph describing the purpose of the section.
[ ] Generate content in md format as described in the format field.
[ ] Derive all details from the source code; do not invent fictitious elements.
[ ] Where diagrams are expected, describe or insert PlantUML.
[ ] Ensure the section can be validated by someone familiar with the codebase.
""".strip()


    user_payload = f"### Flattened repository ###\n```plaintext\n{code}\n```"


    total_tok = prompt_token_count(system_global, system_md, assistant_payload, user_payload)
    if total_tok > TOKEN_LIMIT:
        print(f"⚠️  Skipped {sid} (prompt {total_tok} tokens > {TOKEN_LIMIT})")
        return ""

    # llama.cpp chat templates require a single system message at the top.
    system_combined = f"{system_global}\n\n{system_md}\n\n{assistant_payload}"
    messages: List[MessageParam] = [
        sys_msg(system_combined),
        usr_msg(user_payload),
    ]


    async with semaphore:
        try:
            content = await call_openai_with_retry(messages, MODEL_NAME)
        except Exception as exc:
            print(f"❌ OpenAI error in {sid}: {exc}")
            return ""

    dur = time.perf_counter() - start
    print(f"✔️  {sid} finished in {dur:.2f}s")
    return f"% {sid} — {spec['title']}\n{content}"


async def async_main() -> None:

    # Defaults from config.yaml
    default_repo = REPO_URL
    default_parallel = int(str(_yaml_conf.get("execution", {}).get("max_parallel", 12)))

    parser = argparse.ArgumentParser(description="Generate arc42 docs via Repomix CLI + LLM (async & typed)")
    parser.add_argument("repository", nargs='?', default=default_repo, help="Local path or Git URL (default: config.yaml repo.url)")
    parser.add_argument("--max-parallel", type=int, default=default_parallel, help="Maximum concurrent LLM calls")
    args = parser.parse_args()

    repo = args.repository
    if not repo:
        raise SystemExit("❌ No repository specified. Set repo.url in config.yaml or pass as argument.")

    if not (LLM_BASE_URL or os.environ.get("OPENAI_API_KEY")):
        raise SystemExit(
            "❌ No LLM configured. Set either:\n"
            "   LLM_BASE_URL (e.g. http://localhost:11434/v1 for Ollama)\n"
            "   or OPENAI_API_KEY for OpenAI."
        )

    print("🌀 Flattening repository …")
    code = await flatten_repo(args.repository)
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


    md_parts: List[str] = [
        " ",
    ]

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

    async with aiofiles.open(MD_PATH, "w", encoding="utf-8") as f:
        await f.write("\n\n".join(md_parts))

    print(f"✅ MD written to {MD_PATH}")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

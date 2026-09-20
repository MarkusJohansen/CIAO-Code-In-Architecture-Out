"""Architecture doc section generation."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Iterable, Mapping, Sequence, Tuple, Iterator

from llm_client import (
    client,
    sys_msg,
    usr_msg,
    prompt_token_count,
    MessageParam,
)
from schemas import SectionSpec, UserProfile, GlobalGuidelines
from config import MODEL_NAME, TOKEN_LIMIT


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
            resp = await client.chat.completions.create(model=model, messages=messages)
            content_any = resp.choices[0].message.content
            if content_any is None:
                raise ValueError("OpenAI returned empty content")
            content: str = content_any
            return content
        except Exception as exc:
            if attempt == max_retries:
                raise
            msg = "⚠️  OpenAI error (attempt {}/{}): {} Retrying in {:.1f}s…".format(
                attempt, max_retries, exc, backoff
            )
            print(msg)
            await asyncio.sleep(backoff)
            backoff *= 2
    raise RuntimeError("Retry loop failed unexpectedly")


def walk(tree: Mapping[str, SectionSpec]) -> Iterator[Tuple[str, SectionSpec]]:
    for sid, spec in tree.items():
        if "goal" in spec:
            yield sid, spec
        if "subsections" in spec:
            yield from walk(spec["subsections"])


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
    from llm_client import sys_msg, usr_msg, MessageParam
    from typing import List

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
    return f"<!-- Section {sid} — {spec['title']} -->\n\n{content}"

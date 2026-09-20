"""Repository flattening via Repomix."""
from __future__ import annotations

import asyncio
from typing import cast

import aiofiles

from config import REPO_MIX_CONFIG_PATH, FULL_CODE_PATH


async def flatten_repo(repo: str) -> str:
    if not REPO_MIX_CONFIG_PATH.exists():
        raise SystemExit(f"❌ Config file missing: {REPO_MIX_CONFIG_PATH}")

    is_remote = repo.startswith(("http://", "https://", "git@"))
    cmd = (
        ["repomix", "--remote", repo, "-c", str(REPO_MIX_CONFIG_PATH)]
        if is_remote
        else ["repomix", repo, "-c", str(REPO_MIX_CONFIG_PATH)]
    )

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

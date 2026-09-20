"""Configuration layer: config.yaml < .env < CLI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR: Path = Path(__file__).resolve().parent
REPO_CONFIG_PATH: Path = BASE_DIR / "config.yaml"
REPO_MIX_CONFIG_PATH: Path = BASE_DIR / "repomix.config.json"
MEMORY_PATH: Path = BASE_DIR / "prompt.json"
FULL_CODE_PATH: Path = BASE_DIR / "full_code.txt"

_yaml_conf: dict[str, Any] = {}
if REPO_CONFIG_PATH.exists():
    with open(REPO_CONFIG_PATH, "r") as f:
        _yaml_conf = yaml.safe_load(f) or {}


def _conf(path: str, env: str, default: Any = None) -> Any:
    """Resolve precedence: config.yaml < .env < explicit CLI (later)."""
    val = os.environ.get(env)
    if val is not None:
        return val
    keys = path.split(".")
    node = _yaml_conf
    for k in keys:
        node = node.get(k, {}) if isinstance(node, dict) else {}
    if node or isinstance(node, bool):
        return node
    return default


# LLM settings
MODEL_NAME: str = _conf("llm.model", "LLM_MODEL", "gpt-5-2025-08-07")
TOKEN_LIMIT: int = int(str(_conf("llm.token_limit", "TOKEN_LIMIT", "400000")))
LLM_BASE_URL: str | None = str(_conf("llm.base_url", "LLM_BASE_URL", "")) or None
LLM_API_KEY: str | None = str(_conf("llm.api_key", "LLM_API_KEY", "")) or None
LLM_TIMEOUT: float = float(str(_conf("llm.timeout", "LLM_TIMEOUT", "300.0")))

# Repo / execution settings
REPO_URL: str | None = str(_conf("repo.url", "REPO_URL", "")) or None
DEFAULT_MAX_PARALLEL: int = int(str(_yaml_conf.get("execution", {}).get("max_parallel", 12)))

# Output paths — put docs under results/<model-name>/
RESULTS_DIR: Path = BASE_DIR / "results" / Path(os.path.expanduser(MODEL_NAME)).name
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

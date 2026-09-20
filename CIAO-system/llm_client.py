"""LLM client setup and message helpers."""
from __future__ import annotations

from typing import Union

import tiktoken
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionDeveloperMessageParam,
)

from config import LLM_BASE_URL, LLM_API_KEY, LLM_TIMEOUT, MODEL_NAME

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


# Tokenizer
try:
    enc = tiktoken.encoding_for_model(MODEL_NAME)
except Exception:
    enc = tiktoken.get_encoding("cl100k_base")


def prompt_token_count(*parts: str) -> int:
    return sum(len(enc.encode(p)) for p in parts)


# OpenAI-compatible client
if LLM_BASE_URL:
    client = AsyncOpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY or "no-key",
        timeout=LLM_TIMEOUT,
    )
else:
    import os
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=LLM_TIMEOUT)

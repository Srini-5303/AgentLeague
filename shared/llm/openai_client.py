"""OpenAI-compatible LLM client covering three local providers:
  - openai        : api.openai.com           (OPENAI_API_KEY)
  - ollama        : local OpenAI-compatible   (OLLAMA_BASE_URL, no key)
  - azure_openai  : Azure OpenAI              (AzureOpenAI client)

Uses the async OpenAI SDK. Structured output is requested via response_format
json_schema (strict) where supported, with a tolerant fallback for Ollama.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from shared.config import Settings
from shared.interfaces.llm import LLMClient, LLMMessage


class OpenAICompatClient(LLMClient):
    def __init__(self, settings: Settings):
        self._s = settings
        self._client = self._build_client(settings)
        # Ollama doesn't support strict json_schema response_format reliably.
        self._supports_strict_schema = settings.llm_provider != "ollama"

    @staticmethod
    def _build_client(s: Settings):
        from openai import AsyncAzureOpenAI, AsyncOpenAI

        if s.llm_provider == "azure_openai":
            return AsyncAzureOpenAI(
                azure_endpoint=s.azure_openai_endpoint,
                api_key=s.azure_openai_api_key,
                api_version=s.azure_openai_api_version,
            )
        if s.llm_provider == "ollama":
            return AsyncOpenAI(base_url=s.ollama_base_url, api_key="ollama")
        return AsyncOpenAI(api_key=s.openai_api_key)

    def _resolve_model(self, model: str) -> str:
        # For Ollama, map any requested model to the configured local model.
        return self._s.ollama_model if self._s.llm_provider == "ollama" else model

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        json_schema: Optional[dict] = None,
        temperature: float = 0.8,
        max_tokens: int = 600,
    ) -> str:
        kwargs: dict = {
            "model": self._resolve_model(model),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_schema and self._supports_strict_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "agent_response", "strict": True, "schema": json_schema},
            }
        elif json_schema:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._resolve_model(model),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

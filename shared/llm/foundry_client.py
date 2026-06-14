"""Foundry LLM client (RUNTIME=azure).

Design choice (deliberate, for robustness): we call the Foundry project's model
deployments through its OpenAI-compatible client — `AIProjectClient.get_openai_client()`
returns an OpenAI client bound to the project, so chat completions and streaming
work exactly like the local OpenAI path, and calls are captured by Foundry's
server-side tracing. The character "agents" remain their system_prompt.md
instructions passed in messages — identical contract to local mode, so the swap is
truly config-only.

We intentionally do NOT depend on the preview hosted-agent / A2A `agent_reference`
surface for the request path (it churns). infra/deploy_agents.py can OPTIONALLY
register named agents in the project for the portal's agent view + richer traces,
but the runtime does not require them.

azure-ai-projects / azure-identity imported lazily; install via requirements-azure.txt.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from shared.config import Settings
from shared.interfaces.llm import LLMClient, LLMMessage


class FoundryLLMClient(LLMClient):
    def __init__(self, settings: Settings):
        from azure.ai.projects.aio import AIProjectClient
        from azure.identity.aio import DefaultAzureCredential

        self._s = settings
        self._credential = DefaultAzureCredential()
        self._project = AIProjectClient(
            endpoint=settings.foundry_project_endpoint, credential=self._credential
        )
        self._openai = None  # lazily created OpenAI-compatible client

    async def _client(self):
        if self._openai is None:
            # Returns an async OpenAI-compatible client bound to this Foundry project.
            self._openai = self._project.get_openai_client()
        return self._openai

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        json_schema: Optional[dict] = None,
        temperature: float = 0.8,
        max_tokens: int = 600,
    ) -> str:
        client = await self._client()
        kwargs: dict = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if json_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "agent_response", "strict": True, "schema": json_schema},
            }
        resp = await client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        client = await self._client()
        stream = await client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=True
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

"""OPTIONAL: register named character + narrator agents in the Foundry project.

The runtime does NOT require this — FoundryLLMClient calls the project's model
deployments via the OpenAI-compatible client, passing each agent's system_prompt.md
as instructions (identical to local). Registering named agents here is purely to
populate the Foundry portal's Agents view and enrich server-side traces.

⚠ The azure-ai-projects agent-creation API is preview and its surface may differ
from this script. Verify class/method names against the installed SDK version
(`pip show azure-ai-projects`) and the current Microsoft Learn docs before relying
on it. If it errors, the game still runs — this step is cosmetic.

Usage:
  python infra/deploy_agents.py --endpoint <foundry-project-endpoint> --model gpt-4o-mini
"""
from __future__ import annotations

import argparse
from pathlib import Path

AGENTS = ["warrior", "mage", "rogue", "healer", "rival", "game_master"]
AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--narrator-model", default="gpt-4o")
    args = ap.parse_args()

    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    # NOTE: verify these names against your installed SDK (preview).
    from azure.ai.projects.models import PromptAgentDefinition  # type: ignore

    project = AIProjectClient(endpoint=args.endpoint, credential=DefaultAzureCredential())

    created = {}
    for agent in AGENTS:
        instructions = (AGENTS_DIR / agent / "system_prompt.md").read_text(encoding="utf-8")
        model = args.narrator_model if agent == "game_master" else args.model
        try:
            result = project.agents.create_version(
                agent_name=f"eldervale-{agent.replace('_', '-')}",
                definition=PromptAgentDefinition(model=model, instructions=instructions),
            )
            created[agent] = getattr(result, "name", f"eldervale-{agent}")
            print(f"  registered: {created[agent]}  (model={model})")
        except Exception as e:  # cosmetic step — never fatal
            print(f"  skipped {agent}: {e}")

    print("\nDone. Set CHARACTER_AGENT_IDS / NARRATOR_AGENT_ID only if you later switch "
          "FoundryLLMClient to the agent_reference request path.")


if __name__ == "__main__":
    main()

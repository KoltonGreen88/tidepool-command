"""INTEGRATION: TIDEPOOL — Anthropic Reasoner adapter.

Implements engine.ports.Reasoner. The engine owns the prompts; this owns the
transport. Model matches the Command Agent (claude-sonnet-4-6). API key from the
environment (Doppler / Streamlit Secrets).
"""

from __future__ import annotations

import os

from engine.ports import Reasoner  # noqa: F401 (documents the fulfilled contract)
from integrations.tidepool import config


class AnthropicReasoner:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or config.ANTHROPIC_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                raise RuntimeError("Missing ANTHROPIC_API_KEY")
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def complete(self, system: str, prompt: str, max_tokens: int = 1200) -> str:
        msg = self._get_client().messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

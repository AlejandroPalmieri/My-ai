from __future__ import annotations

from agentos.models.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    default_api_key_env = "OPENAI_API_KEY"
    default_base_url = "https://api.openai.com/v1"

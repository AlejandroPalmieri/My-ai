from __future__ import annotations

from pathlib import Path

from agentos.models.config import load_model_config
from agentos.models.schemas import ModelConfig, ModelProfile, ModelProvider


class ModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root

    def load(self) -> ModelConfig:
        return load_model_config(self.root)

    def enabled_providers(self) -> list[ModelProvider]:
        return [provider for provider in self.load().providers if provider.enabled]

    def enabled_profiles(self) -> list[ModelProfile]:
        return [profile for profile in self.load().model_profiles if profile.enabled]

    def profile(self, profile_name: str) -> ModelProfile:
        for profile in self.load().model_profiles:
            if profile.name == profile_name:
                return profile
        raise KeyError(f"Unknown model profile: {profile_name}")

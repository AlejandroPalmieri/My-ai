from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from agentos.services.interfaces import (
    DoctorService,
    PolicyService,
    ProfileService,
    RefinerService,
    SDDService,
    SkillRegistryService,
    StrategicBrainService,
    TechnicalMemoryService,
    TraceService,
)
from agentos.services.local import (
    LocalDoctorService,
    LocalPolicyService,
    LocalProfileService,
    LocalRefinerService,
    LocalSDDService,
    LocalSkillRegistryService,
    LocalStrategicBrainService,
    LocalTechnicalMemoryService,
    LocalTraceService,
)


@dataclass(frozen=True)
class ServiceContainer:
    root: Path

    @cached_property
    def memory(self) -> TechnicalMemoryService:
        return LocalTechnicalMemoryService(self.root)

    @cached_property
    def sdd(self) -> SDDService:
        return LocalSDDService(self.root)

    @cached_property
    def skills(self) -> SkillRegistryService:
        return LocalSkillRegistryService(self.root)

    @cached_property
    def policies(self) -> PolicyService:
        return LocalPolicyService(self.root)

    @cached_property
    def traces(self) -> TraceService:
        return LocalTraceService(self.root)

    @cached_property
    def profiles(self) -> ProfileService:
        return LocalProfileService(self.root)

    @cached_property
    def strategic_brain(self) -> StrategicBrainService:
        return LocalStrategicBrainService(self.root)

    @cached_property
    def refiner(self) -> RefinerService:
        return LocalRefinerService()

    @cached_property
    def doctor(self) -> DoctorService:
        return LocalDoctorService(self.root)


def create_service_container(root: Path) -> ServiceContainer:
    return ServiceContainer(root=root)

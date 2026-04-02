"""Orchestrates profile lifecycle — creation, switching, deletion."""

import uuid
from datetime import datetime, timezone

from betting.models.profile import Profile
from betting.services.profile_repository import ProfileRepository
from betting.services.agent_repository import AgentRepository


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        agent_repo: AgentRepository,
    ) -> None:
        self._profiles = profile_repo
        self._agents = agent_repo

    def create_profile(
        self,
        name: str,
        profile_type: str = "paper",
        bankroll_start: float = 1000.0,
    ) -> Profile:
        profile = Profile(
            id=str(uuid.uuid4()),
            name=name,
            type=profile_type,
            bankroll_start=bankroll_start,
            is_active=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        self._profiles.create(profile)
        self._agents.bootstrap_agents(
            profile_id=profile.id,
            bankroll_start=bankroll_start,
        )
        return profile

    def get_active_profile(self) -> Profile:
        profile = self._profiles.get_active()
        if profile is None:
            raise RuntimeError("No active profile found")
        return profile

    def switch_profile(self, profile_id: str) -> Profile:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ValueError(f"Profile {profile_id!r} not found")
        self._profiles.set_active(profile_id)
        profile.is_active = True
        return profile

    def list_profiles(self) -> list[Profile]:
        return self._profiles.list_all()

    def delete_profile(self, profile_id: str) -> None:
        self._profiles.delete(profile_id)

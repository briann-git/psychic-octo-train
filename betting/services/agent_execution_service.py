"""Dispatches synthesiser verdicts to all contextual bandit agents."""

import logging

from betting.models.agent import Agent, BanditPolicy
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.verdict import Verdict
from betting.services.agent_repository import AgentRepository

logger = logging.getLogger(__name__)


class AgentExecutionService:
    def __init__(
        self,
        agent_repo: AgentRepository,
        flat_stake: float = 10.0,
    ) -> None:
        self._repo = agent_repo
        self._flat_stake = flat_stake

    def execute(
        self,
        verdict: Verdict,
        fixture: Fixture,
        odds: OddsSnapshot,
        signals: list[dict],
    ) -> None:
        """
        Runs the verdict through all four agents.
        Each agent independently decides to back or skip and records its decision.
        """
        agents = self._repo.get_all_agents()
        for agent in agents:
            self._execute_for_agent(agent, verdict, fixture, odds, signals)

    def _execute_for_agent(
        self,
        agent: Agent,
        verdict: Verdict,
        fixture: Fixture,
        odds: OddsSnapshot,
        signals: list[dict],
    ) -> None:
        # 1. Compute agent's weighted confidence from raw signals
        weighted_confidence = self._weighted_confidence(agent.policy, signals)

        # 2. Apply agent's threshold
        if weighted_confidence < agent.policy.confidence_threshold:
            return

        # 3. Compute edge from agent's weighted signals
        weighted_edge = self._weighted_edge(agent.policy, signals)
        if weighted_edge <= 0:
            return

        # 4. Compute stake
        stake = self._compute_stake(agent, weighted_confidence, weighted_edge, odds)
        if stake <= 0 or stake > agent.bankroll:
            return

        # 5. Deduct stake from bankroll
        agent.bankroll -= stake
        agent.total_picks += 1
        self._repo.save_agent(agent)

        # 6. Record pick
        selection_odds = odds.selections.get(verdict.selection, 0.0)
        self._repo.record_agent_pick(agent.id, {
            "fixture_id": fixture.id,
            "home_team": fixture.home_team,
            "away_team": fixture.away_team,
            "league": fixture.league,
            "kickoff": fixture.kickoff.isoformat(),
            "season": fixture.season,
            "market": verdict.market,
            "selection": verdict.selection,
            "odds": selection_odds,
            "stake": stake,
            "confidence": weighted_confidence,
            "expected_value": weighted_edge,
            "statistical_weight": agent.policy.statistical_weight,
            "market_weight": agent.policy.market_weight,
        })

        logger.info(
            "[Agent %s] Backing %s vs %s — %s @ %.3f, stake=%.2f, "
            "confidence=%.3f, bankroll=%.2f",
            agent.id, fixture.home_team, fixture.away_team,
            verdict.selection, selection_odds, stake,
            weighted_confidence, agent.bankroll,
        )

    def _weighted_confidence(
        self, policy: BanditPolicy, signals: list[dict]
    ) -> float:
        """
        Computes weighted confidence using the agent's own weights,
        independent of the synthesiser's weights.
        """
        total_weight = 0.0
        weighted_sum = 0.0
        weight_map = {
            "statistical": policy.statistical_weight,
            "market": policy.market_weight,
        }
        for signal in signals:
            agent_id = signal.get("agent_id", "")
            weight = weight_map.get(agent_id, 0.0)
            weighted_sum += signal.get("confidence", 0.0) * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _weighted_edge(
        self, policy: BanditPolicy, signals: list[dict]
    ) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        weight_map = {
            "statistical": policy.statistical_weight,
            "market": policy.market_weight,
        }
        for signal in signals:
            agent_id = signal.get("agent_id", "")
            weight = weight_map.get(agent_id, 0.0)
            weighted_sum += signal.get("edge", 0.0) * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _compute_stake(
        self,
        agent: Agent,
        confidence: float,
        edge: float,
        odds: OddsSnapshot,
    ) -> float:
        if agent.policy.staking_strategy == "kelly":
            return self._kelly_stake(agent, edge, odds)
        return self._flat_stake

    def _kelly_stake(
        self,
        agent: Agent,
        edge: float,
        odds: OddsSnapshot,
    ) -> float:
        """
        Fractional Kelly criterion.
        Capped at 10% of bankroll per bet — prevents ruin on early overconfidence.
        """
        if edge <= 0:
            return 0.0

        kelly_fraction = edge * agent.policy.kelly_fraction
        stake = kelly_fraction * agent.bankroll
        max_stake = agent.bankroll * 0.10
        return round(min(stake, max_stake), 2)

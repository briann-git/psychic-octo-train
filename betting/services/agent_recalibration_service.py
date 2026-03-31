"""Weekly recalibration of contextual bandit agent policies."""

import logging
from datetime import datetime, timezone

from betting.services.agent_repository import AgentRepository

logger = logging.getLogger(__name__)

MIN_PICKS_FOR_UPDATE = 5
CONFIDENT_SAMPLE_SIZE = 30


class AgentRecalibrationService:
    def __init__(self, agent_repo: AgentRepository) -> None:
        self._repo = agent_repo

    def recalibrate_all(self, since: datetime) -> None:
        """
        Recalibrates all agents from picks settled since the given datetime.
        Called weekly after Sunday settlement run.
        """
        agents = self._repo.get_all_agents()
        for agent in agents:
            self._recalibrate_agent(agent, since)

    def _recalibrate_agent(self, agent, since: datetime) -> None:
        settled = self._repo.get_settled_since(agent.id, since)

        if len(settled) < MIN_PICKS_FOR_UPDATE:
            logger.info(
                "Agent %s — only %d settled picks since %s, skipping update "
                "(minimum %d required)",
                agent.id, len(settled), since.date(), MIN_PICKS_FOR_UPDATE,
            )
            return

        # Adaptive learning rate — scales with sample size
        cumulative_settled = agent.total_settled + len(settled)
        rate_scale = min(1.0, cumulative_settled / CONFIDENT_SAMPLE_SIZE)
        effective_lr = agent.policy.learning_rate * (0.20 + 0.80 * rate_scale)

        logger.info(
            "Agent %s — recalibrating from %d picks, "
            "effective_lr=%.4f (scale=%.2f)",
            agent.id, len(settled), effective_lr, rate_scale,
        )

        # Compute reward signal per pick (CLV preferred, fallback to binary P&L)
        rewards = self._compute_rewards(settled)

        # Compute gradient — which signal produced better CLV?
        stat_gradient, market_gradient, threshold_gradient = (
            self._compute_gradients(settled, rewards)
        )

        # Update policy
        agent.policy.statistical_weight += effective_lr * stat_gradient
        agent.policy.market_weight += effective_lr * market_gradient
        agent.policy.confidence_threshold += effective_lr * threshold_gradient * 0.01
        agent.policy.normalise_weights()
        agent.policy.clip()
        agent.policy.update_count += 1
        agent.total_settled += len(settled)
        agent.last_updated_at = datetime.now(tz=timezone.utc)

        self._repo.save_agent(agent)

        logger.info(
            "Agent %s updated — stat=%.3f market=%.3f threshold=%.3f "
            "update_count=%d",
            agent.id,
            agent.policy.statistical_weight,
            agent.policy.market_weight,
            agent.policy.confidence_threshold,
            agent.policy.update_count,
        )

    def _compute_rewards(self, picks: list[dict]) -> list[float]:
        """
        Reward signal per pick.
        Primary: CLV (outcome-independent measure of decision quality).
        Fallback: +1 for won, -1 for lost, 0 for void (when CLV unavailable).
        """
        rewards = []
        for pick in picks:
            clv = pick.get("clv")
            if clv is not None:
                rewards.append(clv)
            else:
                outcome = pick.get("outcome", "")
                rewards.append(
                    1.0 if outcome == "won" else (-1.0 if outcome == "lost" else 0.0)
                )
        return rewards

    def _compute_gradients(
        self,
        picks: list[dict],
        rewards: list[float],
    ) -> tuple[float, float, float]:
        """
        Computes policy gradients from pick history and rewards.

        stat_gradient:      positive = statistical signal was more predictive
        market_gradient:    positive = market signal was more predictive
        threshold_gradient: positive = threshold should increase (too many losers)
                            negative = threshold should decrease (missing winners)
        """
        if not picks or not rewards:
            return 0.0, 0.0, 0.0

        stat_gradient = 0.0
        market_gradient = 0.0
        threshold_gradient = 0.0

        for pick, reward in zip(picks, rewards):
            stat_weight_used = pick.get("statistical_weight", 0.5)
            market_weight_used = pick.get("market_weight", 0.5)

            stat_gradient += reward * stat_weight_used
            market_gradient += reward * market_weight_used

            # Threshold gradient: if reward negative, threshold was too low
            threshold_gradient += -reward * (1.0 if reward < 0 else 0.0)

        n = len(picks)
        return stat_gradient / n, market_gradient / n, threshold_gradient / n

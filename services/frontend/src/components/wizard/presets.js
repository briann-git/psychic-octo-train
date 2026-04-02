const PRESETS = {
  conservative: {
    label: 'Conservative',
    description: 'High confidence, flat staking',
    agents: [
      { bankroll: 500, confidence_threshold: 0.72, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.80, market_weight: 0.20 },
      { bankroll: 500, confidence_threshold: 0.68, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.60, market_weight: 0.40 },
    ],
  },
  balanced: {
    label: 'Balanced',
    description: 'Mixed strategies, 3 agents',
    agents: [
      { bankroll: 334, confidence_threshold: 0.65, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.70, market_weight: 0.30 },
      { bankroll: 333, confidence_threshold: 0.62, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.50, market_weight: 0.50 },
      { bankroll: 333, confidence_threshold: 0.60, staking_strategy: 'kelly', kelly_fraction: 0.15, statistical_weight: 0.30, market_weight: 0.70 },
    ],
  },
  aggressive: {
    label: 'Aggressive',
    description: 'Lower thresholds, Kelly staking',
    agents: [
      { bankroll: 250, confidence_threshold: 0.58, staking_strategy: 'kelly', kelly_fraction: 0.20, statistical_weight: 0.80, market_weight: 0.20 },
      { bankroll: 250, confidence_threshold: 0.55, staking_strategy: 'kelly', kelly_fraction: 0.25, statistical_weight: 0.60, market_weight: 0.40 },
      { bankroll: 250, confidence_threshold: 0.60, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.40, market_weight: 0.60 },
      { bankroll: 250, confidence_threshold: 0.55, staking_strategy: 'kelly', kelly_fraction: 0.15, statistical_weight: 0.20, market_weight: 0.80 },
    ],
  },
  custom: {
    label: 'Custom',
    description: 'Start from scratch',
    agents: [
      { bankroll: 1000, confidence_threshold: 0.60, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.70, market_weight: 0.30 },
    ],
  },
};

export function defaultAgent() {
  return { bankroll: 500, confidence_threshold: 0.60, staking_strategy: 'flat', kelly_fraction: 0.25, statistical_weight: 0.70, market_weight: 0.30 };
}

export default PRESETS;

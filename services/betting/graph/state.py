from typing import Optional, TypedDict


class BettingState(TypedDict):
    # Set by IngestNode
    fixture: dict                        # serialised Fixture
    markets: list[str]                   # e.g. ["double_chance"]
    odds_snapshot: dict                  # serialised OddsSnapshot
    eligible: bool                       # False = skip entire pipeline

    # Set by the backtest runner (None during live/paper operation)
    cutoff_date: Optional[str]           # ISO-format datetime for look-ahead prevention

    # Set by StatisticalNode
    statistical_signal: Optional[dict]   # serialised Signal

    # Set by MarketNode
    market_signal: Optional[dict]        # serialised Signal

    # Set by SynthesiserNode
    verdict: Optional[dict]              # serialised Verdict

    # Set by LedgerNode
    recorded: bool

    # Accumulated by any node
    errors: list[str]

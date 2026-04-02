from langgraph.graph import StateGraph, END
from langgraph.types import Send

from betting.graph.state import BettingState
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.market import MarketNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.nodes.ledger import LedgerNode


def build_pipeline(
    ingest_node: IngestNode,
    statistical_node: StatisticalNode,
    market_node: MarketNode,
    synthesiser_node: SynthesiserNode,
    ledger_node: LedgerNode,
):
    """
    Assembles the LangGraph pipeline and returns a compiled graph.

    Flow:
        ingest -> (eligible?) -> fan_out -> statistical  \\
                                         -> market       --> synthesiser -> ledger -> END
               -> (not eligible) -> ledger -> END
    """
    graph: StateGraph = StateGraph(BettingState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("statistical", statistical_node)
    graph.add_node("market", market_node)
    graph.add_node("synthesiser", synthesiser_node)
    graph.add_node("ledger", ledger_node)

    graph.set_entry_point("ingest")

    def route_after_ingest(state: BettingState):
        if state.get("eligible"):
            return [Send("statistical", state), Send("market", state)]
        return "ledger"

    graph.add_conditional_edges(
        "ingest",
        route_after_ingest,
        ["statistical", "market", "ledger"],
    )

    graph.add_edge("statistical", "synthesiser")
    graph.add_edge("market", "synthesiser")
    graph.add_edge("synthesiser", "ledger")
    graph.add_edge("ledger", END)

    return graph.compile()

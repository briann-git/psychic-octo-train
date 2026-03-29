from langgraph.graph import StateGraph, END

from betting.graph.state import BettingState
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.nodes.ledger import LedgerNode


def build_pipeline(
    ingest_node: IngestNode,
    statistical_node: StatisticalNode,
    synthesiser_node: SynthesiserNode,
    ledger_node: LedgerNode,
):
    """
    Assembles the LangGraph pipeline and returns a compiled graph.

    Flow:
        ingest -> (eligible?) -> statistical -> synthesiser -> ledger -> END
                              -> (not eligible) -> ledger -> END
    """
    graph: StateGraph = StateGraph(BettingState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("statistical", statistical_node)
    graph.add_node("synthesiser", synthesiser_node)
    graph.add_node("ledger", ledger_node)

    graph.set_entry_point("ingest")

    graph.add_conditional_edges(
        "ingest",
        lambda state: "statistical" if state.get("eligible") else "ledger",
    )

    graph.add_edge("statistical", "synthesiser")
    graph.add_edge("synthesiser", "ledger")
    graph.add_edge("ledger", END)

    return graph.compile()

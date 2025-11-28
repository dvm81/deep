"""LangGraph workflow definition - V2.0 with Supervisor architecture."""

from typing import TypedDict
from langgraph.graph import StateGraph, END
from ..schema import ResearchState
from .planner import planning_node
from .supervisor import supervisor_node  # V2.0: Supervisor replaces researcher
from .writer import writer_node


class GraphState(TypedDict):
    """State container for the graph workflow."""
    state: ResearchState


def planning_wrapper(state: ResearchState) -> ResearchState:
    """Wrapper for planning node that updates state in place.

    Args:
        state: Current research state

    Returns:
        Updated research state
    """
    updates = planning_node(state)
    for k, v in updates.items():
        setattr(state, k, v)
    return state


def research_wrapper(state: ResearchState) -> ResearchState:
    """Wrapper for supervisor node that updates state in place.

    V2.0: Uses supervisor that coordinates parallel sub-agents with reflection.

    Args:
        state: Current research state

    Returns:
        Updated research state
    """
    updates = supervisor_node(state)
    for k, v in updates.items():
        setattr(state, k, v)
    return state


def writer_wrapper(state: ResearchState) -> ResearchState:
    """Wrapper for writer node that updates state in place.

    Args:
        state: Current research state

    Returns:
        Updated research state
    """
    updates = writer_node(state)
    for k, v in updates.items():
        setattr(state, k, v)
    return state


def build_graph():
    """Build the LangGraph workflow - V2.0 with Supervisor architecture.

    The workflow is linear with parallel sub-agents:
    plan -> supervisor (spawns parallel sub-agents with reflection) -> write -> END

    V2.0 Features:
    - Research Supervisor coordinates multiple sub-agents
    - Sub-agents work in parallel (ThreadPool)
    - Each sub-agent has reflection/self-critique
    - Supervisor reviews all findings

    Returns:
        Compiled LangGraph application
    """
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("plan", lambda s: {"state": planning_wrapper(s["state"])})
    workflow.add_node("research", lambda s: {"state": research_wrapper(s["state"])})
    workflow.add_node("write", lambda s: {"state": writer_wrapper(s["state"])})

    # Define edges (linear flow)
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "research")
    workflow.add_edge("research", "write")
    workflow.add_edge("write", END)

    # Compile and return
    app = workflow.compile()
    return app

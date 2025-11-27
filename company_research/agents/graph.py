"""LangGraph workflow definition."""

from typing import TypedDict
from langgraph.graph import StateGraph, END
from ..schema import ResearchState
from .planner import planning_node
from .researcher import research_node
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
    """Wrapper for research node that updates state in place.

    Args:
        state: Current research state

    Returns:
        Updated research state
    """
    updates = research_node(state)
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
    """Build the LangGraph workflow.

    The workflow is linear:
    plan -> research -> write -> END

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

"""LangGraph workflow definition - V2.7 with Iterative Refinement."""

from typing import TypedDict
from langgraph.graph import StateGraph, END
from ..schema import ResearchState
from .planner import planning_node
from .supervisor import supervisor_node  # V2.0: Supervisor replaces researcher
from .refinement import refinement_node  # V2.7: Targeted refinement
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


def refinement_wrapper(state: ResearchState) -> ResearchState:
    """Wrapper for refinement node that updates state in place.

    V2.7: Executes targeted follow-up research to fill gaps.

    Args:
        state: Current research state

    Returns:
        Updated research state
    """
    updates = refinement_node(state)
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


def should_refine(graph_state: GraphState) -> str:
    """Conditional edge function to decide refinement.

    Args:
        graph_state: Current graph state

    Returns:
        "refinement" if refinement is needed, "write" otherwise
    """
    state = graph_state["state"]

    # Check if refinement is needed
    if (state.supervisor_review and
        state.supervisor_review.refinement_needed and
        state.refinement_iteration < 1):
        return "refinement"

    return "write"


def build_graph():
    """Build the LangGraph workflow - V2.7 with Iterative Refinement.

    The workflow now includes conditional branching:
    plan → research → [conditional: refinement OR write] → write → END

    V2.7 Features:
    - Conditional refinement based on supervisor review
    - Targeted follow-up research for low-confidence findings
    - Maximum 1 refinement iteration (prevents infinite loops)
    - Merges refined findings with original findings

    V2.0 Features (retained):
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
    workflow.add_node("refinement", lambda s: {"state": refinement_wrapper(s["state"])})
    workflow.add_node("write", lambda s: {"state": writer_wrapper(s["state"])})

    # Define edges
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "research")

    # Conditional edge: research → refinement OR write
    workflow.add_conditional_edges(
        "research",
        should_refine,
        {
            "refinement": "refinement",
            "write": "write"
        }
    )

    # After refinement, always go to write
    workflow.add_edge("refinement", "write")
    workflow.add_edge("write", END)

    # Compile and return
    app = workflow.compile()
    return app

from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class MeetingState(TypedDict):
    plan: List[dict]
    approved: bool

def strategist_node(state: MeetingState):
    # This represents the AI brainstorming the 5-day innovation walkthrough
    return {"plan": [{"day": "Mon", "topic": "Local AI Security"}]}

def human_review_node(state: MeetingState):
    # This is a placeholder node. The graph will be configured to 
    # INTERRUPT before this node runs.
    pass

# Setup Persistence
memory = MemorySaver()

# Build Graph
builder = StateGraph(MeetingState)
builder.add_node("strategist", strategist_node)
builder.add_node("human_review", human_review_node)

builder.add_edge(START, "strategist")
builder.add_edge("strategist", "human_review")
builder.add_edge("human_review", END)

# COMPILE with interrupt
marketing_team = builder.compile(
    checkpointer=memory, 
    interrupt_before=["human_review"]
)